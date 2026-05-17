import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, CheckCircle2, Clock } from "lucide-react";
import { api } from "@/lib/api";
import type { Job } from "@/types";
import { StatusPill } from "@/components/ui/StatusPill";
import { formatDate, formatDuration } from "@/lib/utils";

export function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const q = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.get<Job>(`/jobs/${id}`),
    refetchInterval: (query) =>
      query.state.data?.status === "running" ||
      query.state.data?.status === "pending"
        ? 2_000
        : false,
  });

  if (q.isLoading) return <div className="text-xs text-zinc-500">Loading…</div>;
  if (!q.data) return <div className="text-xs text-zinc-500">Job not found</div>;
  const j = q.data;

  const steps = buildSteps(j);

  return (
    <div className="flex flex-col gap-5">
      <button onClick={() => navigate(-1)} className="btn-ghost -ml-2 w-fit">
        <ArrowLeft size={13} /> Back
      </button>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              {j.id.slice(0, 8)}
            </h1>
            <StatusPill status={j.status} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-zinc-500 dark:text-zinc-400">
            <Link
              to={`/pipelines/${j.pipeline_id}`}
              className="font-mono text-zinc-700 hover:text-bifrost-purple dark:text-zinc-300"
            >
              {j.pipeline_name}
            </Link>
            <span className="flex items-center gap-1">
              <Clock size={11} /> {formatDate(j.started_at)}
            </span>
            <span>→</span>
            <span>{formatDate(j.finished_at)}</span>
            <span className="font-mono">{formatDuration(j.duration_ms)}</span>
            <span className="capitalize">triggered: {j.triggered_by}</span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Rows read" value={j.rows_read.toLocaleString()} />
        <Metric label="Rows written" value={j.rows_written.toLocaleString()} />
        <Metric
          label="Rows failed"
          value={j.rows_failed.toLocaleString()}
          accent={j.rows_failed > 0 ? "rose" : undefined}
        />
        <Metric label="Duration" value={formatDuration(j.duration_ms)} />
      </div>

      <section className="card overflow-hidden">
        <div className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <h3 className="text-sm font-semibold">Step timeline</h3>
        </div>
        <div className="flex flex-col gap-2 p-4">
          {steps.length === 0 && (
            <div className="text-xs text-zinc-500">No steps recorded.</div>
          )}
          {steps.map((s, i) => (
            <div
              key={i}
              className="grid grid-cols-[140px_1fr_64px_16px] items-center gap-3"
            >
              <div className="truncate font-mono text-[11px] text-zinc-700 dark:text-zinc-300">
                {s.label}
              </div>
              <div className="relative h-3 rounded-full bg-zinc-100 dark:bg-zinc-800">
                <div
                  className={
                    "absolute top-0 h-3 rounded-full " +
                    (s.error ? "bg-rose-500" : "bg-bifrost-gradient")
                  }
                  style={{
                    left: `${s.left}%`,
                    width: `${Math.max(2, s.width)}%`,
                  }}
                />
              </div>
              <div className="text-right font-mono text-[11px] tabular-nums text-zinc-500">
                {formatDuration(s.durationMs)}
              </div>
              {s.error ? (
                <AlertCircle size={13} className="text-rose-500" />
              ) : (
                <CheckCircle2 size={13} className="text-emerald-500" />
              )}
            </div>
          ))}
        </div>
      </section>

      {j.error && (
        <div className="card border-rose-200 bg-rose-50 p-4 dark:border-rose-500/30 dark:bg-rose-500/10">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-300">
            Error
          </div>
          <pre className="mt-1 whitespace-pre-wrap text-xs text-rose-900 dark:text-rose-200">
            {j.error}
          </pre>
        </div>
      )}

      <section className="card overflow-hidden">
        <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold dark:border-zinc-800">
          Log stream
        </div>
        <div className="max-h-96 overflow-y-auto bg-zinc-950 px-4 py-3 font-mono text-[11px] text-zinc-200">
          {j.log.length === 0 && (
            <div className="text-zinc-500">No log entries</div>
          )}
          {j.log.map((l, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-zinc-500">{l.ts.slice(11, 19)}</span>
              <span
                className={
                  l.level === "error"
                    ? "text-rose-400"
                    : l.level === "warn"
                    ? "text-amber-300"
                    : "text-zinc-200"
                }
              >
                {l.message}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

interface Step {
  label: string;
  left: number;
  width: number;
  durationMs: number;
  error: boolean;
}

function buildSteps(j: Job): Step[] {
  const log = j.log ?? [];
  if (log.length === 0 || !j.started_at) return [];
  const start = new Date(j.started_at).getTime();
  const end = j.finished_at ? new Date(j.finished_at).getTime() : Date.now();
  const total = Math.max(1, end - start);

  // Compute per-batch durations from successive log entries
  const segments: Step[] = [];
  for (let i = 0; i < log.length; i++) {
    const cur = new Date(log[i].ts).getTime();
    const next =
      i < log.length - 1 ? new Date(log[i + 1].ts).getTime() : end;
    const left = ((cur - start) / total) * 100;
    const width = ((next - cur) / total) * 100;
    segments.push({
      label: log[i].message.split(":")[0].slice(0, 22),
      left,
      width,
      durationMs: next - cur,
      error: log[i].level === "error",
    });
  }
  return segments;
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "rose";
}) {
  const color =
    accent === "rose"
      ? "text-rose-600 dark:text-rose-400"
      : "text-zinc-900 dark:text-zinc-100";
  return (
    <div className="card p-4">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className={"mt-1 text-xl font-semibold tabular-nums " + color}>
        {value}
      </div>
    </div>
  );
}
