import {
    OpenInNewWindowIcon,
} from "@radix-ui/react-icons"
import { Row } from "@tanstack/react-table"

import {
    Button,
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@marzneshin/common/components"
import { MoreHorizontal, PencilIcon, TrashIcon, Power } from "lucide-react"
import { useTranslation } from "react-i18next"

interface DataTableActionsCellProps<TData>
    extends React.HTMLAttributes<HTMLDivElement> {
    row: Row<TData>,
    onDelete: (object: TData) => void,
    onEdit: (object: TData) => void,
    onOpen: (object: TData) => void,
    onRestart?: (object: TData) => void,
}

export function DataTableActionsCell<TData>({
    row, onDelete, onEdit, onOpen, onRestart
}: DataTableActionsCellProps<TData>) {
    const { t } = useTranslation();

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" data-testid="action-menu-open" className="p-0 w-8 h-8">
                    <span className="sr-only">Open menu</span>
                    <MoreHorizontal className="w-4 h-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuLabel>{t('actions')}</DropdownMenuLabel>
                <DropdownMenuItem data-testid="action-row-open" onClick={() => { onOpen(row.original) }}>
                    <OpenInNewWindowIcon className="mr-1 w-4 h-4" /> {t('open')}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem data-testid="action-row-edit" onClick={(e) => { e.stopPropagation(); onEdit(row.original) }}>
                    <PencilIcon className="mr-1 w-4 h-4" />    {t('edit')}
                </DropdownMenuItem>
                {onRestart && (
                    <DropdownMenuItem data-testid="action-row-restart" onClick={(e) => { e.stopPropagation(); onRestart(row.original) }}>
                        <Power className="mr-1 w-4 h-4" /> {t('Restart')}
                    </DropdownMenuItem>
                )}

                <DropdownMenuItem data-testid="action-row-delete" onClick={(e) => { e.stopPropagation(); onDelete(row.original) }} className="text-destructive">
                    <TrashIcon className="mr-1 w-4 h-4" />{t('delete')}
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}