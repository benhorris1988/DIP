import { NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Plug,
  Workflow,
  Activity,
  Settings as SettingsIcon,
  AlertOctagon,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { BifrostMark } from "@/components/branding/BifrostMark";
import { StatusDot } from "@/components/ui/StatusPill";
import type { Pipeline } from "@/types";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/pipelines", label: "Pipelines", icon: Workflow },
  { to: "/connections", label: "Connections", icon: Plug },
  { to: "/jobs", label: "Job Runs", icon: Activity },
  { to: "/errors", label: "Error Explorer", icon: AlertOctagon },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  const [pipelinesOpen, setPipelinesOpen] = useState(true);
  const { pathname } = useLocation();

  const pipelines = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => api.get<Pipeline[]>("/pipelines"),
  });

  return (
    <aside className="flex w-60 flex-col border-r border-zinc-200 bg-white text-zinc-900 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100">
      <div className="flex h-14 items-center gap-2.5 border-b border-zinc-200 px-4 dark:border-zinc-800">
        <BifrostMark size={28} />
        <div className="leading-tight">
          <div className="text-[13px] font-semibold tracking-tight">
            Data Integration
          </div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            Operator Console
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[12px] font-medium transition-colors",
                isActive
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-white"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-white",
              )
            }
          >
            <item.icon size={15} />
            {item.label}
          </NavLink>
        ))}

        <div className="mt-3">
          <button
            type="button"
            onClick={() => setPipelinesOpen((v) => !v)}
            className="flex w-full items-center justify-between px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300"
          >
            <span>Pipelines</span>
            <ChevronDown
              size={12}
              className={cn(
                "transition-transform",
                !pipelinesOpen && "-rotate-90",
              )}
            />
          </button>
          {pipelinesOpen && (
            <div className="flex flex-col gap-0.5">
              {(pipelines.data ?? []).slice(0, 50).map((p) => {
                const active = pathname === `/pipelines/${p.id}`;
                return (
                  <NavLink
                    key={p.id}
                    to={`/pipelines/${p.id}`}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2.5 py-1 text-[12px] font-mono transition-colors",
                      active
                        ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-white"
                        : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-white",
                    )}
                  >
                    <StatusDot status={p.enabled ? "healthy" : "paused"} />
                    <span className="truncate">{p.name}</span>
                  </NavLink>
                );
              })}
              {pipelines.data?.length === 0 && (
                <div className="px-2.5 py-1 text-[11px] text-zinc-500">
                  No pipelines yet
                </div>
              )}
            </div>
          )}
        </div>
      </nav>

      <BackendStatus />
    </aside>
  );
}

function BackendStatus() {
  const q = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<{ status: string }>("/health"),
    refetchInterval: 15_000,
  });
  const ok = q.data?.status === "ok";
  return (
    <div className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
      <div className="flex items-center gap-2 text-[11px]">
        <StatusDot status={ok ? "healthy" : "error"} />
        <span className="text-zinc-600 dark:text-zinc-400">Backend</span>
        <span className="ml-auto font-mono text-zinc-500">
          {ok ? "online" : "offline"}
        </span>
      </div>
    </div>
  );
}
