import { FC } from "react";
import {
    columns as columnsFn,
    fetchNodes,
    NodeType
} from '@marzneshin/modules/nodes';
import { EntityTable } from "@marzneshin/libs/entity-table";
import { useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { fetch } from "@marzneshin/common/utils";
import { toast } from "sonner";

export const NodesTable: FC = () => {
    const navigate = useNavigate({ from: "/nodes" });
    const queryClient = useQueryClient();

    const onOpen = (entity: NodeType) => {
        navigate({
            to: "/nodes/$nodeId",
            params: { nodeId: String(entity.id) },
        })
    }

    const onEdit = (entity: NodeType) => {
        navigate({
            to: "/nodes/$nodeId/edit",
            params: { nodeId: String(entity.id) },
        })
    }

    const onDelete = (entity: NodeType) => {
        navigate({
            to: "/nodes/$nodeId/delete",
            params: { nodeId: String(entity.id) },
        })
    }

    const restartMutation = useMutation({
        mutationFn: (nodeId: number) => fetch(`/nodes/${nodeId}/restart`, { method: 'post' }),
        onSuccess: (data, nodeId) => {
            toast.success(`Restart signal sent to node "${data.name}".`);
            queryClient.invalidateQueries({ queryKey: ['nodes'] });
            queryClient.invalidateQueries({ queryKey: ['node', nodeId] });
        },
        onError: (error: any) => {
            const errorMessage = error.response?._data?.detail || 'Failed to restart node.';
            toast.error(errorMessage);
        },
    });

    const onRestart = (entity: NodeType) => {
        restartMutation.mutate(entity.id);
    }

    const columns = columnsFn({ onEdit, onDelete, onOpen, onRestart });

    return (
        <EntityTable
            fetchEntity={fetchNodes}
            columns={columns}
            primaryFilter="name"
            entityKey="nodes"
            onCreate={() => navigate({ to: "/nodes/create" })}
            onOpen={onOpen}
        />
    )
}