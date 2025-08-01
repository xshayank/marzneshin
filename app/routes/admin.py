from typing import Optional, Annotated
from datetime import timedelta

import sqlalchemy
from fastapi import APIRouter, Response
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db import Session, crud
from app.db.models import Admin as DBAdmin, Service, User
from app.dependencies import AdminDep, SudoAdminDep, DBDep, get_current_admin
from app.marznode.operations import update_user
from app.models.admin import (
    Admin,
    AdminCreate,
    AdminInDB,
    Token,
    AdminPartialModify,
    AdminResponse,
    OTPTokenData,
)
from app.models.service import ServiceResponse
from app.models.user import UserResponse
from app.utils.auth import create_admin_token
from app.services import otp as otp_service

router = APIRouter(tags=["Admin"], prefix="/admins")


def authenticate_admin(
    db: Session, username: str, password: str
) -> Optional[DBAdmin]: # Changed type hint back to DBAdmin for clarity
    dbadmin = crud.get_admin(db, username)
    if not dbadmin:
        return None

    # This part remains the same
    if not AdminInDB.model_validate(dbadmin).verify_password(password):
        return None

    # Return the verified database object
    return dbadmin


@router.post("/token", response_model=Token)
def admin_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBDep
):
    dbadmin = authenticate_admin(db, form_data.username, form_data.password)
    if not dbadmin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if dbadmin.is_otp_enabled:
        otp_token = form_data.client_secret
        if not otp_token:
            raise HTTPException(
                status_code=401,
                detail={"otp_required": True},
            )

        if not otp_service.verify_otp(dbadmin.otp_secret, otp_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return Token(
        is_sudo=dbadmin.is_sudo,
        access_token=create_admin_token(
            form_data.username, is_sudo=dbadmin.is_sudo
        ),
    )


@router.post("/current/otp/enable", status_code=200)
async def enable_admin_otp_setup(
    db: DBDep,
    current_admin: DBAdmin = Depends(get_current_admin),
):

    if current_admin.is_otp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled.")

    secret = otp_service.generate_otp_secret()

    db_admin = db.query(DBAdmin).filter(DBAdmin.id == current_admin.id).first()
    db_admin.otp_secret = secret

    db.commit()

    uri = otp_service.get_otp_provisioning_uri(current_admin.username, secret)
    qr_code_bytes = otp_service.generate_qr_code(uri)

    return Response(content=qr_code_bytes.read(), media_type="image/png")


@router.post("/current/otp/verify", status_code=200)
async def verify_admin_otp_setup(
    data: OTPTokenData,
    db: DBDep,
    current_admin: DBAdmin = Depends(get_current_admin),
):

    db_admin = db.query(DBAdmin).filter(DBAdmin.id == current_admin.id).first()

    if not db_admin.otp_secret:
        raise HTTPException(
            status_code=400, detail="2FA setup has not been initiated."
        )

    if not otp_service.verify_otp(db_admin.otp_secret, data.token):
        raise HTTPException(status_code=400, detail="Invalid OTP token.")

    db_admin.is_otp_enabled = True
    db.commit()

    return {"message": "2FA for admin has been enabled successfully."}


@router.post("/current/otp/disable", status_code=200)
async def disable_admin_otp(
    data: OTPTokenData,
    db: DBDep,
    current_admin: DBAdmin = Depends(get_current_admin),
):

    db_admin = db.query(DBAdmin).filter(DBAdmin.id == current_admin.id).first()

    if not db_admin.is_otp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled.")

    if not otp_service.verify_otp(db_admin.otp_secret, data.token):
        raise HTTPException(status_code=400, detail="Invalid OTP token.")

    db_admin.is_otp_enabled = False
    db_admin.otp_secret = None
    db.commit()

    return {"message": "2FA for admin has been disabled successfully."}


@router.get("", response_model=Page[AdminResponse])
def get_admins(db: DBDep, admin: SudoAdminDep, username: str | None = None):
    query = db.query(DBAdmin)
    if username:
        query = query.filter(DBAdmin.username.ilike(f"%{username}%"))
    return paginate(db, query)


@router.post("", response_model=Admin)
def create_admin(new_admin: AdminCreate, db: DBDep, admin: SudoAdminDep):
    try:
        dbadmin = crud.create_admin(db, new_admin)
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admin already exists")

    return dbadmin


@router.get("/current", response_model=Admin)
def get_current_admin(admin: AdminDep):
    return admin


@router.post("/token", response_model=Token)
def admin_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBDep
):
    if dbadmin := authenticate_admin(
        db, form_data.username, form_data.password
    ):
        return Token(
            is_sudo=dbadmin.is_sudo,
            access_token=create_admin_token(
                form_data.username, is_sudo=dbadmin.is_sudo
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/{username}", response_model=AdminResponse)
def get_admin(
    username: str,
    db: DBDep,
    admin: SudoAdminDep,
):
    dbadmin = crud.get_admin(db, username)
    if not dbadmin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return dbadmin


@router.put("/{username}", response_model=AdminResponse)
def modify_admin(
    username: str,
    modified_admin: AdminPartialModify,
    db: DBDep,
    admin: SudoAdminDep,
):
    dbadmin = crud.get_admin(db, username)
    if not dbadmin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # If a sudoer admin wants to edit another sudoer
    if username != admin.username and dbadmin.is_sudo:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to edit another sudoers account. Use marzneshin-cli instead.",
        )

    dbadmin = crud.update_admin(db, dbadmin, modified_admin)
    return dbadmin


@router.get("/{username}/services", response_model=Page[ServiceResponse])
def get_admin_services(username: str, db: DBDep, admin: SudoAdminDep):
    """
    Get user services
    """
    db_admin = crud.get_admin(db, username)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if db_admin.is_sudo or db_admin.all_services_access:
        query = db.query(Service)
    else:
        query = (
            db.query(Service)
            .join(Service.admins)
            .where(DBAdmin.id == db_admin.id)
        )

    return paginate(query)


@router.get("/{username}/users", response_model=Page[UserResponse])
def get_admin_users(username: str, db: DBDep, admin: SudoAdminDep):
    """
    Get user services
    """
    db_admin = crud.get_admin(db, username)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    query = db.query(User).where(User.admin_id == db_admin.id)

    return paginate(query)


@router.post("/{username}/disable_users", response_model=AdminResponse)
async def disable_users(username: str, db: DBDep, admin: SudoAdminDep):
    db_admin = crud.get_admin(db, username)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if db_admin.is_sudo and db_admin.username != admin.username:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed.",
        )

    for user in crud.get_users(db, admin=db_admin, enabled=True):
        if user.activated:
            update_user(user, remove=True)
        user.enabled = False
        user.activated = False
    db.commit()

    return db_admin


@router.post("/{username}/enable_users", response_model=AdminResponse)
async def enable_users(username: str, db: DBDep, admin: SudoAdminDep):
    db_admin = crud.get_admin(db, username)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if db_admin.is_sudo and db_admin.username != admin.username:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed.",
        )

    for user in crud.get_users(db, admin=db_admin, enabled=False):
        user.enabled = True
        if user.is_active:
            update_user(user)
            user.activated = True
    db.commit()

    return db_admin


@router.delete("/{username}")
def remove_admin(username: str, db: DBDep, admin: SudoAdminDep):
    dbadmin = crud.get_admin(db, username)
    if not dbadmin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if dbadmin.is_sudo:
        raise HTTPException(
            status_code=403,
            detail="You're not allowed to delete sudoers accounts. Use marzneshin-cli instead.",
        )

    crud.remove_admin(db, dbadmin)
    return {}
