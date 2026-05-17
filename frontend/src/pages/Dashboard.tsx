import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Activity,
  Bell,
  CheckCircle2,
  Plug,
  Workflow,
  XCircle,
  Clock,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Connection, Job, Pipeline, Stats } from "@/types";
import { StatusPill } from "@/components/ui/StatusPill";
import { Sparkline } from "@/components/ui/Sparkline";
import { formatDate, formatDuration } from "@/lib/utils";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";

export function Dashboard() {
  const stats = useQuery({
    queryKey: ["stats"],
    queryFn: () => api.get<Stats>("/jobs/stats"),
    refetchInterval: 10_000,
  });
  const jobs = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: () => api.get<Job[]>("/jobs?limit=50"),
    refetchInterval: 10_000,
  });
  const pipelines = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => api.get<Pipeline[]>("/pipelines"),
  });
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.get<Connection[]>("/connections"),
  });

  const successRate24h = (() => {
    const j = jobs.data ?? [];
    if (!j.length) return null;
    const succ = j.filter((x) => x.status === "succeeded").length;
    return Math.round((succ / j.length) * 100);
  })();

  const rowsTrend = (jobs.data ?? [])
    .slice(0, 12)
    .reverse()
    .map((j) => j.rows_written);

  const cards = [
    {
      label: "Active pipelines",
      value: stats.data?.pipelines ?? 0,
      sub: `${(pipelines.data ?? []).filter((p) => p.enabled).length} enabled`,
      icon: Workflow,
      to: "/pipelines",
    },
    {
      label: "Batches · last 24h",
      value: stats.data?.jobs ?? 0,
      sub: successRate24h === null ? "—" : `${successRate24h}% success`,
      icon: Activity,
      to: "/jobs",
      sparkline: rowsTrend,
      sparklineColor: "#10b981",
    },
    {
      label: "Failed runs",
      value: stats.data?.failed ?? 0,
      sub: `${stats.data?.succeeded ?? 0} succeeded`,
      icon: XCircle,
      to: "/errors",
      accent: "rose",
    },
    {
      label: "Connections",
      value: stats.data?.connections ?? 0,
      sub: `${(connections.data ?? []).filter((c) => c.status === "healthy").length} healthy`,
      icon: Plug,
      to: "/connections",
    },
  ] as const;

  const recentJobs = (jobs.data ?? []).slice(0, 12);
  const alerts = (jobs.data ?? [])
    .filter((j) => j.status === "failed")
    .slice(0, 8);

  const connMap = new Map((connections.data ?? []).map((c) => [c.id, c]));

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_320px]">
      <div className="flex flex-col gap-5">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Operator console
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Live status across connections, pipelines and recent batches.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {cards.map((c) => (
            <Link
              key={c.label}
              to={c.to}
              className="card group p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                  <c.icon size={13} />
                  {c.label}
                </div>
                <ArrowUpRight
                  size={13}
                  className="text-zinc-400 group-hover:text-zinc-700 dark:group-hover:text-zinc-200"
                />
              </div>
              <div className="mt-3 flex items-end justify-between">
                <div>
                  <div className="text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
                    {c.value.toLocaleString()}
                  </div>
                  <div className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    {c.sub}
                  </div>
                </div>
                {"sparkline" in c && c.sparkline && c.sparkline.length > 0 && (
                  <Sparkline data={c.sparkline} color={c.sparklineColor} />
                )}
              </div>
            </Link>
          ))}
        </div>

        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
            <h3 className="text-sm font-semibold">Pipelines</h3>
            <Link
              to="/pipelines"
              className="text-xs font-medium text-bifrost-purple hover:underline"
            >
              View all
            </Link>
          </div>
          <table className="w-full text-[12px]">
            <thead className="bg-zinc-50 text-left text-[10px] uppercase tracking-wider text-zinc-500 dark:bg-zinc-900/40 dark:text-zinc-400">
              <tr>
                <th className="px-4 py-2">Pipeline</th>
                <th className="px-4 py-2">Source</th>
                <th className="px-4 py-2">Destination</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Last batch</th>
                <th className="px-4 py-2 text-right">Schedule</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {(pipelines.data ?? []).slice(0, 8).map((p) => {
                const lastJob = (jobs.data ?? []).find(
                  (j) => j.pipeline_id === p.id,
                );
                const src = connMap.get(p.source_connection_id);
                const dst = connMap.get(p.destination_connection_id);
                return (
                  <tr
                    key={p.id}
                    className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50"
                  >
                    <td className="px-4 py-2">
                      <Link
                        to={`/pipelines/${p.id}`}
                        className="font-mono text-zinc-900 hover:text-bifrost-purple dark:text-zinc-100"
                      >
                        {p.name}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      {src && (
                        <div className="flex items-center gap-2">
                          <ConnectorIcon
                            icon={src.connector_type.split("_")[0]}
                            size={20}
                          />
                          <span className="text-zinc-600 dark:text-zinc-300">
                            {src.name}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {dst && (
                        <div className="flex items-center gap-2">
                          <ConnectorIcon
                            icon={dst.connector_type.split("_")[0]}
                            size={20}
                          />
                          <span className="text-zinc-600 dark:text-zinc-300">
                            {dst.name}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2">
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
                    <td className="px-4 py-2 text-right text-zinc-500">
                      {lastJob ? formatDate(lastJob.started_at) : "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-zinc-500">
                      {p.schedule || "manual"}
                    </td>
                  </tr>
                );
              })}
              {(pipelines.data ?? []).length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-zinc-500"
                  >
                    No pipelines yet — create one to start moving data.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
            <h3 className="text-sm font-semibold">Recent batches</h3>
            <Link
              to="/jobs"
              className="text-xs font-medium text-bifrost-purple hover:underline"
            >
              View all
            </Link>
          </div>
          <table className="w-full text-[12px]">
            <thead className="bg-zinc-50 text-left text-[10px] uppercase tracking-wider text-zinc-500 dark:bg-zinc-900/40 dark:text-zinc-400">
              <tr>
                <th className="px-4 py-2">Batch</th>
                <th className="px-4 py-2">Pipeline</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Rows</th>
                <th className="px-4 py-2 text-right">Duration</th>
                <th className="px-4 py-2">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {recentJobs.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-zinc-500"
                  >
                    No batch runs yet.
                  </td>
                </tr>
              )}
              {recentJobs.map((j) => (
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
                  <td className="px-4 py-2 font-mono text-zinc-900 dark:text-zinc-100">
                    {j.pipeline_name}
                  </td>
                  <td className="px-4 py-2">
                    <StatusPill status={j.status} />
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
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <aside className="flex flex-col gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 dark:text-zinc-100">
            <Bell size={13} />
            Recent alerts
            {alerts.length > 0 && (
              <span className="pill-rose ml-auto">{alerts.length}</span>
            )}
          </div>
          <div className="mt-3 flex flex-col gap-3">
            {alerts.length === 0 && (
              <div className="flex items-center gap-2 text-[12px] text-zinc-500">
                <CheckCircle2 size={14} className="text-emerald-500" />
                Nothing failed recently.
              </div>
            )}
            {alerts.map((a) => (
              <Link
                key={a.id}
                to={`/jobs/${a.id}`}
                className="block rounded-md border border-zinc-200 p-3 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/50"
              >
                <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                  <Clock size={11} />
                  {formatDate(a.started_at)}
                </div>
                <div className="mt-1 font-mono text-[12px] text-zinc-900 dark:text-zinc-100">
                  {a.pipeline_name}
                </div>
                <div className="mt-1 line-clamp-2 text-[11px] text-rose-600 dark:text-rose-400">
                  {a.error || "Failed"}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
