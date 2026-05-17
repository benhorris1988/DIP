import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/types";
import { StatusPill } from "@/components/ui/StatusPill";
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
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Batches
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Recent executions across all pipelines.
          </p>
        </div>
        <button className="btn-secondary" onClick={() => q.refetch()}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      <div className="flex gap-1 rounded-lg bg-zinc-200/60 p-1 w-fit dark:bg-zinc-800/60">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={
              "px-3 py-1 text-xs font-medium rounded-md capitalize " +
              (status === s
                ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-100"
                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100")
            }
          >
            {s}
          </button>
        ))}
      </div>

      {q.data?.length ? (
        <div className="card overflow-hidden">
          <table className="w-full text-[12px]">
            <thead className="bg-zinc-50 text-left text-[10px] uppercase tracking-wider text-zinc-500 dark:bg-zinc-900/40 dark:text-zinc-400">
              <tr>
                <th className="px-4 py-2">Batch</th>
                <th className="px-4 py-2">Pipeline</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Rows read</th>
                <th className="px-4 py-2 text-right">Rows written</th>
                <th className="px-4 py-2 text-right">Duration</th>
                <th className="px-4 py-2">Triggered</th>
                <th className="px-4 py-2">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {q.data.map((j) => (
                <tr
                  key={j.id}
                  className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50"
                >
                  <td className="px-4 py-2">
                    <Link
                      to={`/jobs/${j.id}`}
                      className="font-mono text-zinc-700 hover:text-bifrost-purple dark:text-zinc-300"
                    >
                      {j.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <Link
                      to={`/pipelines/${j.pipeline_id}`}
                      className="font-mono text-zinc-900 hover:text-bifrost-purple dark:text-zinc-100"
                    >
                      {j.pipeline_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <StatusPill status={j.status} />
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {j.rows_read.toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {j.rows_written.toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {formatDuration(j.duration_ms)}
                  </td>
                  <td className="px-4 py-2 capitalize text-zinc-600 dark:text-zinc-300">
                    {j.triggered_by}
                  </td>
                  <td className="px-4 py-2 text-zinc-500">
                    {formatDate(j.started_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          icon={Activity}
          title="No batches yet"
          description="Trigger a pipeline to see batch runs appear here."
        />
      )}
    </div>
  );
}
