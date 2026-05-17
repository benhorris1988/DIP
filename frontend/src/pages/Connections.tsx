import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plug, Plus, Trash2, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";
import { StatusPill } from "@/components/ui/StatusPill";
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
    mutationFn: (id: string) =>
      api.post<{ ok: boolean; message: string }>(`/connections/${id}/test`),
    onSettled: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.del(`/connections/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connections"] }),
  });

  const data = query.data ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Connections
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Configure source and destination systems used by your pipelines.
          </p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/connections/new")}>
          <Plus size={14} /> New connection
        </button>
      </div>

      <div className="flex gap-1 rounded-lg bg-zinc-200/60 p-1 w-fit dark:bg-zinc-800/60">
        {(["all", "source", "destination"] as RoleFilter[]).map((r) => (
          <button
            key={r}
            onClick={() => setFilter(r)}
            className={
              "px-3 py-1 text-xs font-medium rounded-md " +
              (filter === r
                ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-100"
                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100")
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
              <Plus size={14} /> New connection
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.map((c) => (
            <div key={c.id} className="card p-4">
              <div className="flex items-start gap-3">
                <ConnectorIcon icon={c.connector_type.split("_")[0]} />
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/connections/${c.id}`}
                    className="font-mono text-sm font-medium text-zinc-900 hover:text-bifrost-purple dark:text-zinc-100"
                  >
                    {c.name}
                  </Link>
                  <div className="text-[11px] text-zinc-500">
                    {c.connector_type}
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="pill-zinc capitalize">{c.role}</span>
                    <StatusPill status={c.status} />
                  </div>
                </div>
              </div>
              {c.description && (
                <p className="mt-3 text-xs text-zinc-600 dark:text-zinc-300 line-clamp-2">
                  {c.description}
                </p>
              )}
              <div className="mt-3 text-[10px] uppercase tracking-wider text-zinc-500">
                Last tested
                <span className="ml-2 normal-case font-mono text-[11px] text-zinc-600 dark:text-zinc-400">
                  {formatDate(c.last_tested_at)}
                </span>
              </div>
              <div className="mt-3 flex items-center gap-1">
                <button
                  onClick={() => test.mutate(c.id)}
                  disabled={test.isPending}
                  className="btn-secondary"
                >
                  <Zap size={12} /> Test
                </button>
                <Link to={`/connections/${c.id}`} className="btn-ghost">
                  Edit
                </Link>
                <button
                  onClick={() => {
                    if (confirm(`Delete connection "${c.name}"?`))
                      remove.mutate(c.id);
                  }}
                  className="btn-ghost ml-auto h-7 w-7 p-0 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10"
                  aria-label="Delete"
                >
                  <Trash2 size={13} />
                </button>
              </div>
              {test.data && test.variables === c.id && (
                <div
                  className={
                    "mt-3 rounded-md px-2.5 py-2 text-[11px] " +
                    (test.data.ok
                      ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300"
                      : "bg-rose-50 text-rose-800 dark:bg-rose-500/10 dark:text-rose-300")
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
