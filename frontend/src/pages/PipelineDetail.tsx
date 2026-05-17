import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Pencil,
  Play,
  Power,
  Trash2,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { Connection, Job, Pipeline } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";
import { StatusPill } from "@/components/ui/StatusPill";
import { formatDate, formatDuration } from "@/lib/utils";

type Tab = "overview" | "batches" | "config" | "history";

export function PipelineDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");

  const pipeline = useQuery({
    enabled: Boolean(id),
    queryKey: ["pipeline", id],
    queryFn: () => api.get<Pipeline>(`/pipelines/${id}`),
  });
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.get<Connection[]>("/connections"),
  });
  const jobs = useQuery({
    enabled: Boolean(id),
    queryKey: ["jobs", "pipeline", id],
    queryFn: () => api.get<Job[]>(`/jobs?pipeline_id=${id}&limit=100`),
    refetchInterval: 5_000,
  });

  const trigger = useMutation({
    mutationFn: () => api.post(`/pipelines/${id}/run`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
  const setEnabled = useMutation({
    mutationFn: (enabled: boolean) =>
      api.patch<Pipeline>(`/pipelines/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pipeline", id] }),
  });
  const remove = useMutation({
    mutationFn: () => api.del(`/pipelines/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      navigate("/pipelines");
    },
  });

  if (pipeline.isLoading || !pipeline.data)
    return <div className="text-xs text-zinc-500">Loading…</div>;

  const p = pipeline.data;
  const connMap = new Map((connections.data ?? []).map((c) => [c.id, c]));
  const src = connMap.get(p.source_connection_id);
  const dst = connMap.get(p.destination_connection_id);
  const jobList = jobs.data ?? [];
  const lastJob = jobList[0];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <button
          onClick={() => navigate("/pipelines")}
          className="btn-ghost -ml-2"
        >
          <ArrowLeft size={13} /> Back
        </button>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              {p.name}
            </h1>
            <StatusPill
              status={
                lastJob
                  ? lastJob.status
                  : p.enabled
                  ? "healthy"
                  : "paused"
              }
            />
            <span className="pill-zinc">{p.mode}</span>
          </div>
          {p.description && (
            <p className="mt-1 max-w-2xl text-xs text-zinc-500 dark:text-zinc-400">
              {p.description}
            </p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-zinc-500 dark:text-zinc-400">
            <span className="flex items-center gap-1.5">
              {src && (
                <ConnectorIcon
                  icon={src.connector_type.split("_")[0]}
                  size={18}
                />
              )}
              <span className="font-mono">
                {src?.name}:{p.source_object}
              </span>
            </span>
            <ArrowRight size={11} />
            <span className="flex items-center gap-1.5">
              {dst && (
                <ConnectorIcon
                  icon={dst.connector_type.split("_")[0]}
                  size={18}
                />
              )}
              <span className="font-mono">
                {dst?.name}:{p.destination_object}
              </span>
            </span>
            <span>•</span>
            <span className="font-mono">{p.schedule || "manual"}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <button
            className="btn-secondary"
            onClick={() => setEnabled.mutate(!p.enabled)}
          >
            <Power size={13} /> {p.enabled ? "Pause" : "Resume"}
          </button>
          <button
            className="btn-primary"
            onClick={() => trigger.mutate()}
            disabled={!p.enabled || trigger.isPending}
          >
            <Play size={13} /> Trigger run
          </button>
          <button
            className="btn-secondary"
            onClick={() => navigate(`/pipelines/${p.id}/edit`)}
          >
            <Pencil size={13} /> Edit
          </button>
          <button
            className="btn-ghost text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10"
            onClick={() => {
              if (confirm(`Delete pipeline "${p.name}"?`)) remove.mutate();
            }}
            aria-label="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </header>

      <nav className="flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
        {(
          [
            ["overview", "Overview"],
            ["batches", "Recent batches"],
            ["config", "Mappings & config"],
            ["history", "Run history"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={
              "border-b-2 px-3 py-2 text-xs font-medium transition-colors " +
              (tab === key
                ? "border-bifrost-purple text-zinc-900 dark:text-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-200")
            }
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <OverviewTab jobs={jobList} />}
      {tab === "batches" && <BatchesTab jobs={jobList} />}
      {tab === "config" && <ConfigTab pipeline={p} />}
      {tab === "history" && <HistoryTab jobs={jobList} />}
    </div>
  );
}

function OverviewTab({ jobs }: { jobs: Job[] }) {
  const recent = jobs.slice(0, 14).slice().reverse();
  const rowData = recent.map((j, i) => ({
    name: j.id.slice(0, 6),
    rows: j.rows_written,
    duration: j.duration_ms,
    i,
  }));

  const succ = jobs.filter((j) => j.status === "succeeded").length;
  const fail = jobs.filter((j) => j.status === "failed").length;
  const total = succ + fail;
  const errorRate = total ? Math.round((fail / total) * 100) : 0;
  const totalRows = jobs.reduce((s, j) => s + j.rows_written, 0);
  const avgDuration = total
    ? Math.round(jobs.reduce((s, j) => s + j.duration_ms, 0) / jobs.length)
    : 0;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Metric label="Total batches" value={jobs.length.toLocaleString()} />
      <Metric label="Rows written" value={totalRows.toLocaleString()} />
      <Metric
        label="Error rate"
        value={`${errorRate}%`}
        accent={errorRate > 10 ? "rose" : errorRate > 0 ? "amber" : "emerald"}
      />
      <Metric label="Avg duration" value={formatDuration(avgDuration)} />
      <Metric label="Succeeded" value={succ.toLocaleString()} accent="emerald" />
      <Metric label="Failed" value={fail.toLocaleString()} accent="rose" />

      <div className="card p-4 lg:col-span-3">
        <div className="mb-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300">
          Rows written (recent batches)
        </div>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rowData}>
              <CartesianGrid stroke="#e4e4e7" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  border: "1px solid #e4e4e7",
                }}
              />
              <Bar dataKey="rows" fill="#7c3aed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card p-4 lg:col-span-3">
        <div className="mb-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300">
          Duration trend
        </div>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rowData}>
              <CartesianGrid stroke="#e4e4e7" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  border: "1px solid #e4e4e7",
                }}
                formatter={(v: number) => formatDuration(v)}
              />
              <Line
                type="monotone"
                dataKey="duration"
                stroke="#ec4899"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function BatchesTab({ jobs }: { jobs: Job[] }) {
  if (jobs.length === 0)
    return (
      <div className="card p-6 text-center text-xs text-zinc-500">
        No batches yet. Trigger a run to populate this list.
      </div>
    );
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-[12px]">
        <thead className="bg-zinc-50 text-left text-[10px] uppercase tracking-wider text-zinc-500 dark:bg-zinc-900/40 dark:text-zinc-400">
          <tr>
            <th className="px-4 py-2">Batch</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2 text-right">Rows read</th>
            <th className="px-4 py-2 text-right">Rows written</th>
            <th className="px-4 py-2 text-right">Duration</th>
            <th className="px-4 py-2">Started</th>
            <th className="px-4 py-2">Triggered</th>
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
              <td className="px-4 py-2 text-zinc-500">
                {formatDate(j.started_at)}
              </td>
              <td className="px-4 py-2 capitalize text-zinc-500">
                {j.triggered_by}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfigTab({ pipeline }: { pipeline: Pipeline }) {
  const yaml = configToYaml(pipeline);
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-zinc-200 px-4 py-2 text-xs font-medium dark:border-zinc-800">
        pipeline.yaml
      </div>
      <pre className="bg-zinc-950 px-4 py-4 font-mono text-[11px] leading-relaxed text-zinc-200 overflow-x-auto">
        {highlightYaml(yaml)}
      </pre>
    </div>
  );
}

function HistoryTab({ jobs }: { jobs: Job[] }) {
  if (jobs.length === 0)
    return (
      <div className="card p-6 text-center text-xs text-zinc-500">
        No history yet.
      </div>
    );
  // simple timeline of recent jobs
  return (
    <div className="card p-4">
      <div className="mb-3 text-xs font-semibold text-zinc-700 dark:text-zinc-300">
        Recent run history
      </div>
      <div className="flex flex-col gap-2">
        {jobs.slice(0, 30).map((j) => (
          <Link
            key={j.id}
            to={`/jobs/${j.id}`}
            className="flex items-center gap-3 rounded-md border border-zinc-200 px-3 py-2 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900/50"
          >
            <StatusPill status={j.status} />
            <span className="font-mono text-[11px] text-zinc-500">
              {j.id.slice(0, 8)}
            </span>
            <span className="text-[11px] text-zinc-500">
              {formatDate(j.started_at)}
            </span>
            <span className="ml-auto font-mono text-[11px] tabular-nums text-zinc-600 dark:text-zinc-300">
              {j.rows_written.toLocaleString()} rows
            </span>
            <span className="font-mono text-[11px] text-zinc-500">
              {formatDuration(j.duration_ms)}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "emerald" | "rose" | "amber";
}) {
  const color =
    accent === "emerald"
      ? "text-emerald-600 dark:text-emerald-400"
      : accent === "rose"
      ? "text-rose-600 dark:text-rose-400"
      : accent === "amber"
      ? "text-amber-600 dark:text-amber-400"
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

function configToYaml(p: Pipeline): string {
  const lines = [
    `# Pipeline definition`,
    `name: ${p.name}`,
    `mode: ${p.mode}`,
    `enabled: ${p.enabled}`,
    `schedule: ${p.schedule || "manual"}`,
    `source:`,
    `  connection: ${p.source_connection_id}`,
    `  object: ${p.source_object}`,
    `destination:`,
    `  connection: ${p.destination_connection_id}`,
    `  object: ${p.destination_object}`,
    `field_mappings:`,
  ];
  if (p.field_mappings.length === 0) {
    lines.push(`  []  # pass-through`);
  } else {
    for (const m of p.field_mappings) {
      lines.push(`  - source: ${m.source}`);
      lines.push(`    destination: ${m.destination}`);
      if (m.transform) lines.push(`    transform: "${m.transform}"`);
    }
  }
  return lines.join("\n");
}

function highlightYaml(yaml: string) {
  return yaml.split("\n").map((line, i) => {
    if (line.startsWith("#"))
      return (
        <div key={i}>
          <span className="text-zinc-500">{line}</span>
        </div>
      );
    const m = line.match(/^(\s*)([^:\s][^:]*):(.*)$/);
    if (m) {
      return (
        <div key={i}>
          <span>{m[1]}</span>
          <span className="text-violet-400">{m[2]}</span>
          <span className="text-zinc-400">:</span>
          <span className="text-emerald-300">{m[3]}</span>
        </div>
      );
    }
    return <div key={i}>{line}</div>;
  });
}
