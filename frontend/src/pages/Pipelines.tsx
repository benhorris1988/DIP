import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Play, Plus, Trash2, Workflow } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection, Job, Pipeline } from "@/types";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusPill } from "@/components/ui/StatusPill";
import { Sparkline } from "@/components/ui/Sparkline";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";
import { formatDate } from "@/lib/utils";

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
  const jobs = useQuery({
    queryKey: ["jobs", "for-pipelines"],
    queryFn: () => api.get<Job[]>("/jobs?limit=200"),
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
  const jobsByPipeline = new Map<string, Job[]>();
  for (const j of jobs.data ?? []) {
    const arr = jobsByPipeline.get(j.pipeline_id) ?? [];
    arr.push(j);
    jobsByPipeline.set(j.pipeline_id, arr);
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Pipelines
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Move data from a source to a destination on demand or on a schedule.
          </p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/pipelines/new")}>
          <Plus size={14} /> New pipeline
        </button>
      </div>

      {data.length === 0 ? (
        <EmptyState
          icon={Workflow}
          title="No pipelines yet"
          description="Connect a source to a destination to build your first pipeline."
          action={
            <Link to="/pipelines/new" className="btn-primary">
              <Plus size={14} /> New pipeline
            </Link>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-[12px]">
            <thead className="bg-zinc-50 text-left text-[10px] uppercase tracking-wider text-zinc-500 dark:bg-zinc-900/40 dark:text-zinc-400">
              <tr>
                <th className="px-4 py-2">Pipeline</th>
                <th className="px-4 py-2">Flow</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Mode</th>
                <th className="px-4 py-2">Schedule</th>
                <th className="px-4 py-2 text-right">Rows trend</th>
                <th className="px-4 py-2 text-right">Last batch</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.map((p) => {
                const src = connMap.get(p.source_connection_id);
                const dst = connMap.get(p.destination_connection_id);
                const pipelineJobs = (jobsByPipeline.get(p.id) ?? []).slice(0, 12);
                const trend = pipelineJobs
                  .slice()
                  .reverse()
                  .map((j) => j.rows_written);
                const lastJob = pipelineJobs[0];
                return (
                  <tr
                    key={p.id}
                    className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/pipelines/${p.id}`}
                        className="font-mono font-medium text-zinc-900 hover:text-bifrost-purple dark:text-zinc-100"
                      >
                        {p.name}
                      </Link>
                      {p.description && (
                        <div className="text-[11px] text-zinc-500">
                          {p.description}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {src && (
                          <ConnectorIcon
                            icon={src.connector_type.split("_")[0]}
                            size={22}
                          />
                        )}
                        <span className="font-mono text-[11px] text-zinc-600 dark:text-zinc-400">
                          {p.source_object}
                        </span>
                        <ArrowRight size={12} className="text-zinc-400" />
                        {dst && (
                          <ConnectorIcon
                            icon={dst.connector_type.split("_")[0]}
                            size={22}
                          />
                        )}
                        <span className="font-mono text-[11px] text-zinc-600 dark:text-zinc-400">
                          {p.destination_object}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill
                        status={
                          lastJob
                            ? lastJob.status
                            : p.enabled
                            ? "healthy"
                            : "paused"
                        }
                      />
                    </td>
                    <td className="px-4 py-3 capitalize text-zinc-600 dark:text-zinc-300">
                      {p.mode}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-zinc-500">
                      {p.schedule || "manual"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {trend.length > 0 ? (
                        <Sparkline data={trend} color="#7c3aed" />
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-[11px] text-zinc-500">
                      {lastJob ? formatDate(lastJob.started_at) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => trigger.mutate(p.id)}
                          className="btn-secondary"
                          disabled={!p.enabled || trigger.isPending}
                          title="Trigger run"
                        >
                          <Play size={12} /> Run
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete pipeline "${p.name}"?`))
                              remove.mutate(p.id);
                          }}
                          className="btn-ghost h-7 w-7 p-0 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10"
                          aria-label="Delete"
                        >
                          <Trash2 size={13} />
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
