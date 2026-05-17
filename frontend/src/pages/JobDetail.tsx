import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate, formatDuration } from "@/lib/utils";

export function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const q = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.get<Job>(`/jobs/${id}`),
    refetchInterval: (query) =>
      query.state.data?.status === "running" || query.state.data?.status === "pending"
        ? 2_000
        : false,
  });

  if (q.isLoading) return <div className="text-sm text-slate-500">Loading…</div>;
  if (!q.data) return <div className="text-sm text-slate-500">Job not found</div>;

  const j = q.data;

  return (
    <div className="mx-auto max-w-4xl">
      <button onClick={() => navigate(-1)} className="btn-ghost mb-4 -ml-2">
        <ArrowLeft size={16} /> Back
      </button>
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">{j.pipeline_name}</h2>
          <p className="text-xs text-slate-500 font-mono">{j.id}</p>
        </div>
        <StatusBadge status={j.status} />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Metric label="Rows read" value={j.rows_read.toLocaleString()} />
        <Metric label="Rows written" value={j.rows_written.toLocaleString()} />
        <Metric label="Rows failed" value={j.rows_failed.toLocaleString()} />
        <Metric label="Duration" value={formatDuration(j.duration_ms)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <InfoRow label="Triggered by" value={j.triggered_by} />
        <InfoRow label="Started" value={formatDate(j.started_at)} />
        <InfoRow label="Finished" value={formatDate(j.finished_at)} />
        <InfoRow label="Created" value={formatDate(j.created_at)} />
      </div>

      {j.error && (
        <div className="mt-6 card border-red-200 bg-red-50 p-4">
          <div className="text-xs font-semibold text-red-800 mb-1">Error</div>
          <pre className="whitespace-pre-wrap text-sm text-red-900">{j.error}</pre>
        </div>
      )}

      <div className="mt-6 card overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-3 font-semibold">Log</div>
        <div className="max-h-96 overflow-y-auto bg-slate-950 px-4 py-3 font-mono text-xs text-slate-200">
          {j.log.length === 0 && <div className="text-slate-500">No log entries</div>}
          {j.log.map((l, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-slate-500">{l.ts.slice(11, 19)}</span>
              <span
                className={
                  l.level === "error"
                    ? "text-red-400"
                    : l.level === "warn"
                    ? "text-amber-300"
                    : "text-slate-200"
                }
              >
                {l.message}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">{value}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-800">{value}</div>
    </div>
  );
}
