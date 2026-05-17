import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Activity,
  CheckCircle2,
  Plug,
  Workflow,
  XCircle,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Job, Stats } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate, formatDuration } from "@/lib/utils";

export function Dashboard() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api.get<Stats>("/jobs/stats") });
  const jobs = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: () => api.get<Job[]>("/jobs?limit=10"),
  });

  const cards = [
    {
      label: "Connections",
      value: stats.data?.connections ?? 0,
      icon: Plug,
      to: "/connections",
      accent: "bg-brand-50 text-brand-600",
    },
    {
      label: "Pipelines",
      value: stats.data?.pipelines ?? 0,
      icon: Workflow,
      to: "/pipelines",
      accent: "bg-purple-50 text-purple-600",
    },
    {
      label: "Successful runs",
      value: stats.data?.succeeded ?? 0,
      icon: CheckCircle2,
      to: "/jobs?status=succeeded",
      accent: "bg-green-50 text-green-600",
    },
    {
      label: "Failed runs",
      value: stats.data?.failed ?? 0,
      icon: XCircle,
      to: "/jobs?status=failed",
      accent: "bg-red-50 text-red-600",
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Welcome back</h2>
        <p className="text-sm text-slate-500">
          Monitor connections, manage pipelines, and inspect job runs across the platform.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Link key={c.label} to={c.to} className="card p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className={`flex h-10 w-10 items-center justify-center rounded-md ${c.accent}`}>
                <c.icon size={20} />
              </div>
              <ArrowUpRight size={16} className="text-slate-400" />
            </div>
            <div className="mt-4 text-2xl font-semibold text-slate-900">{c.value}</div>
            <div className="text-sm text-slate-500">{c.label}</div>
          </Link>
        ))}
      </div>

      <div className="card">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex items-center gap-2">
            <Activity size={18} className="text-slate-500" />
            <h3 className="font-semibold text-slate-900">Recent job runs</h3>
          </div>
          <Link to="/jobs" className="text-sm font-medium text-brand-600 hover:text-brand-700">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Pipeline</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Rows</th>
                <th className="px-5 py-3 text-right">Duration</th>
                <th className="px-5 py-3">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.data?.length ? (
                jobs.data.map((j) => (
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
                      {j.rows_written.toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums">
                      {formatDuration(j.duration_ms)}
                    </td>
                    <td className="px-5 py-3 text-slate-500">{formatDate(j.started_at)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-slate-500">
                    No job runs yet. Create a pipeline and trigger a run.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
