import { ColumnDef } from "@tanstack/react-table"
import { NodesStatusBadge, NodeType, NodesStatus } from "@marzneshin/modules/nodes"
import {
    DataTableActionsCell,
    DataTableColumnHeader
} from "@marzneshin/libs/entity-table"
import i18n from "@marzneshin/features/i18n"
import {
    type ColumnActions
} from "@marzneshin/libs/entity-table";
import {
    NoPropogationButton,
    DropdownMenuSeparator,
    DropdownMenuItem,
} from "@marzneshin/common/components"
import { Power } from "lucide-react";


export const columns = (actions: ColumnActions<NodeType>): ColumnDef<NodeType>[] => ([
    {
        accessorKey: "name",
        header: ({ column }) => <DataTableColumnHeader title={i18n.t('name')} column={column} />,
    },
    {
        accessorKey: "status",
        header: ({ column }) => <DataTableColumnHeader title={i18n.t('status')} column={column} />,
        cell: ({ row }) => <NodesStatusBadge status={NodesStatus[row.original.status]} />,
    },
    {
        accessorKey: "address",
        header: ({ column }) => <DataTableColumnHeader title={i18n.t('address')} column={column} />,
        cell: ({ row }) => `${row.original.address}:${row.original.port}`
    },
    {
        accessorKey: "usage_coefficient",
        header: ({ column }) => <DataTableColumnHeader title={i18n.t('page.nodes.usage_coefficient')} column={column} />,
    },
    {
        id: "actions",
        cell: ({ row }) => {
            return (
                <NoPropogationButton row={row} actions={actions}>
                    <DataTableActionsCell {...actions} row={row}>
                        {actions.onRestart && (
                            <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onSelect={() => actions.onRestart?.(row.original)}>
                                    <Power className="mr-2 h-4 w-4" />
                                    <span>{i18n.t('Restart')}</span>
                                </DropdownMenuItem>
                            </>
                        )}
                    </DataTableActionsCell>
                </NoPropogationButton>
            );
        },
    }
]);