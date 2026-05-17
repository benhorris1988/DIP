import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate, formatDuration } from "@/lib/utils";

const statuses = ["all", "running", "succeeded", "failed"] as const;

export function Jobs() {
  const [status, setStatus] = useState<(typeof statuses)[number]>("all");
  const q = useQuery({
    queryKey: ["jobs", status],
    queryFn: () =>
      api.get<Job[]>(status === "all" ? "/jobs" : `/jobs?status=${status}`),
    refetchInterval: 5_000,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Job runs</h2>
          <p className="text-sm text-slate-500">Recent executions of your pipelines.</p>
        </div>
        <button className="btn-secondary" onClick={() => q.refetch()}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="flex gap-1 rounded-lg bg-slate-200/60 p-1 w-fit">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={
              "px-3 py-1.5 text-sm font-medium rounded-md capitalize " +
              (status === s
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900")
            }
          >
            {s}
          </button>
        ))}
      </div>

      {q.data?.length ? (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Pipeline</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Rows read</th>
                <th className="px-5 py-3 text-right">Rows written</th>
                <th className="px-5 py-3 text-right">Duration</th>
                <th className="px-5 py-3">Triggered</th>
                <th className="px-5 py-3">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {q.data.map((j) => (
                <tr key={j.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <Link
                      to={`/jobs/${j.id}`}
                      className="font-medium text-slate-900 hover:text-brand-600"
                    >
                      {j.pipeline_name}
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={j.status} />
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums">
                    {j.rows_read.toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums">
                    {j.rows_written.toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums">
                    {formatDuration(j.duration_ms)}
                  </td>
                  <td className="px-5 py-3 capitalize text-slate-600">{j.triggered_by}</td>
                  <td className="px-5 py-3 text-slate-500">{formatDate(j.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          icon={Activity}
          title="No job runs"
          description="Trigger a pipeline to see runs appear here."
        />
      )}
    </div>
  );
}
