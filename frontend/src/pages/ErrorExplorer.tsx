import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, Filter, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { Job, Pipeline } from "@/types";
import { StatusPill } from "@/components/ui/StatusPill";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate, formatDuration } from "@/lib/utils";

export function ErrorExplorer() {
  const [search, setSearch] = useState("");
  const [pipelineId, setPipelineId] = useState<string>("");

  const failed = useQuery({
    queryKey: ["jobs", "failed"],
    queryFn: () => api.get<Job[]>("/jobs?status=failed&limit=500"),
    refetchInterval: 10_000,
  });
  const pipelines = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => api.get<Pipeline[]>("/pipelines"),
  });

  const rows = useMemo(() => {
    const all = failed.data ?? [];
    return all.filter((j) => {
      if (pipelineId && j.pipeline_id !== pipelineId) return false;
      if (search) {
        const s = search.toLowerCase();
        const msg = (j.error ?? "").toLowerCase();
        if (
          !msg.includes(s) &&
          !j.pipeline_name.toLowerCase().includes(s) &&
          !j.id.toLowerCase().includes(s)
        )
          return false;
      }
      return true;
    });
  }, [failed.data, pipelineId, search]);

  // Group by error message (rough rule_id)
  const groups = useMemo(() => {
    const m = new Map<string, Job[]>();
    for (const j of rows) {
      const key = (j.error ?? "Unknown error").split(":")[0].slice(0, 64);
      const arr = m.get(key) ?? [];
      arr.push(j);
      m.set(key, arr);
    }
    return Array.from(m.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [rows]);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Error explorer
        </h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Failed batches grouped by error class, with full-text search.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search
            size={13}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400"
          />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search error message, pipeline, batch id…"
            className="input pl-7 w-80"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={13} className="text-zinc-400" />
          <select
            value={pipelineId}
            onChange={(e) => setPipelineId(e.target.value)}
            className="input w-56"
          >
            <option value="">All pipelines</option>
            {(pipelines.data ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="ml-auto text-[11px] text-zinc-500">
          {rows.length} failed batches • {groups.length} error classes
        </div>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          icon={AlertOctagon}
          title="No errors found"
          description="No failed batches match the current filters."
        />
      ) : (
        <div className="flex flex-col gap-4">
          {groups.map(([key, jobs]) => (
            <div key={key} className="card overflow-hidden">
              <div className="flex items-center gap-3 border-b border-zinc-200 px-4 py-2.5 dark:border-zinc-800">
                <AlertOctagon size={14} className="text-rose-500" />
                <div className="font-mono text-[12px] text-zinc-900 dark:text-zinc-100">
                  {key}
                </div>
                <span className="pill-rose ml-auto">{jobs.length}</span>
              </div>
              <table className="w-full text-[12px]">
                <thead className="bg-zinc-50 text-left text-[10px] uppercase tracking-wider text-zinc-500 dark:bg-zinc-900/40 dark:text-zinc-400">
                  <tr>
                    <th className="px-4 py-2">Batch</th>
                    <th className="px-4 py-2">Pipeline</th>
                    <th className="px-4 py-2">Status</th>
                    <th className="px-4 py-2 text-right">Duration</th>
                    <th className="px-4 py-2">Started</th>
                    <th className="px-4 py-2">Message</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                  {jobs.map((j) => (
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
                        {formatDuration(j.duration_ms)}
                      </td>
                      <td className="px-4 py-2 text-zinc-500">
                        {formatDate(j.started_at)}
                      </td>
                      <td className="px-4 py-2 text-rose-600 dark:text-rose-400">
                        <span className="line-clamp-1">{j.error}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
