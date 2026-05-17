import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plug, Plus, Trash2, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

type RoleFilter = "all" | "source" | "destination";

export function Connections() {
  const [filter, setFilter] = useState<RoleFilter>("all");
  const qc = useQueryClient();
  const navigate = useNavigate();

  const query = useQuery({
    queryKey: ["connections", filter],
    queryFn: () =>
      api.get<Connection[]>(
        filter === "all" ? "/connections" : `/connections?role=${filter}`,
      ),
  });

  const test = useMutation({
    mutationFn: (id: string) => api.post<{ ok: boolean; message: string }>(`/connections/${id}/test`),
    onSettled: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/connections/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });

  const data = query.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Connections</h2>
          <p className="text-sm text-slate-500">
            Configure source and destination systems used by your pipelines.
          </p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/connections/new")}>
          <Plus size={16} /> New connection
        </button>
      </div>

      <div className="flex gap-1 rounded-lg bg-slate-200/60 p-1 w-fit">
        {(["all", "source", "destination"] as RoleFilter[]).map((r) => (
          <button
            key={r}
            onClick={() => setFilter(r)}
            className={
              "px-3 py-1.5 text-sm font-medium rounded-md transition-colors " +
              (filter === r
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900")
            }
          >
            {r === "all" ? "All" : r === "source" ? "Sources" : "Destinations"}
          </button>
        ))}
      </div>

      {data.length === 0 ? (
        <EmptyState
          icon={Plug}
          title="No connections yet"
          description="Add your first source or destination to get started."
          action={
            <Link to="/connections/new" className="btn-primary">
              <Plus size={16} /> New connection
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.map((c) => (
            <div key={c.id} className="card p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <ConnectorIcon icon={c.connector_type.split("_")[0]} />
                  <div>
                    <Link
                      to={`/connections/${c.id}`}
                      className="font-semibold text-slate-900 hover:text-brand-600"
                    >
                      {c.name}
                    </Link>
                    <div className="text-xs text-slate-500">{c.connector_type}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="badge-slate capitalize">{c.role}</span>
                      <StatusBadge status={c.status} />
                    </div>
                  </div>
                </div>
              </div>
              {c.description && (
                <p className="mt-3 text-sm text-slate-600">{c.description}</p>
              )}
              <div className="mt-4 text-xs text-slate-500">
                Last tested: {formatDate(c.last_tested_at)}
              </div>
              <div className="mt-4 flex items-center gap-2">
                <button
                  onClick={() => test.mutate(c.id)}
                  disabled={test.isPending}
                  className="btn-secondary"
                >
                  <Zap size={14} /> Test
                </button>
                <Link to={`/connections/${c.id}`} className="btn-ghost">
                  Edit
                </Link>
                <button
                  onClick={() => {
                    if (confirm(`Delete connection "${c.name}"?`)) remove.mutate(c.id);
                  }}
                  className="btn-ghost text-red-600 hover:bg-red-50 ml-auto"
                  aria-label="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              {test.data && test.variables === c.id && (
                <div
                  className={
                    "mt-3 rounded-md px-3 py-2 text-xs " +
                    (test.data.ok
                      ? "bg-green-50 text-green-800"
                      : "bg-red-50 text-red-800")
                  }
                >
                  {test.data.message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
