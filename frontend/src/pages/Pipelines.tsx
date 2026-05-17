import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Play, Plus, Trash2, Workflow } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection, Pipeline } from "@/types";
import { EmptyState } from "@/components/ui/EmptyState";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";

export function Pipelines() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const pipelines = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => api.get<Pipeline[]>("/pipelines"),
  });
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.get<Connection[]>("/connections"),
  });

  const trigger = useMutation({
    mutationFn: (id: string) => api.post(`/pipelines/${id}/run`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/pipelines/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pipelines"] }),
  });

  const data = pipelines.data ?? [];
  const connMap = new Map((connections.data ?? []).map((c) => [c.id, c]));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Pipelines</h2>
          <p className="text-sm text-slate-500">
            Move data from a source to a destination on demand or on a schedule.
          </p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/pipelines/new")}>
          <Plus size={16} /> New pipeline
        </button>
      </div>

      {data.length === 0 ? (
        <EmptyState
          icon={Workflow}
          title="No pipelines yet"
          description="Connect a source to a destination to build your first pipeline."
          action={
            <Link to="/pipelines/new" className="btn-primary">
              <Plus size={16} /> New pipeline
            </Link>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Pipeline</th>
                <th className="px-5 py-3">Source</th>
                <th className="px-5 py-3"></th>
                <th className="px-5 py-3">Destination</th>
                <th className="px-5 py-3">Mode</th>
                <th className="px-5 py-3">Schedule</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((p) => {
                const src = connMap.get(p.source_connection_id);
                const dst = connMap.get(p.destination_connection_id);
                return (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <Link
                        to={`/pipelines/${p.id}`}
                        className="font-medium text-slate-900 hover:text-brand-600"
                      >
                        {p.name}
                      </Link>
                      {p.description && (
                        <div className="text-xs text-slate-500">{p.description}</div>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {src && <ConnectorIcon icon={src.connector_type.split("_")[0]} size={28} />}
                        <div>
                          <div className="font-medium">{src?.name ?? "—"}</div>
                          <div className="text-xs text-slate-500">{p.source_object}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-1 py-3 text-slate-400">
                      <ArrowRight size={16} />
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {dst && <ConnectorIcon icon={dst.connector_type.split("_")[0]} size={28} />}
                        <div>
                          <div className="font-medium">{dst?.name ?? "—"}</div>
                          <div className="text-xs text-slate-500">{p.destination_object}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 capitalize text-slate-600">{p.mode}</td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">
                      {p.schedule || "manual"}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => trigger.mutate(p.id)}
                          className="btn-secondary"
                          disabled={!p.enabled || trigger.isPending}
                        >
                          <Play size={14} /> Run
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete pipeline "${p.name}"?`)) remove.mutate(p.id);
                          }}
                          className="btn-ghost text-red-600 hover:bg-red-50"
                          aria-label="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
