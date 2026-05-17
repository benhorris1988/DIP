import { cn } from "@/lib/utils";

export type StatusKind =
  | "healthy"
  | "running"
  | "pending"
  | "succeeded"
  | "warning"
  | "paused"
  | "untested"
  | "unknown"
  | "error"
  | "failed"
  | "cancelled";

const config: Record<
  StatusKind,
  { cls: string; dot: string; label?: string }
> = {
  healthy: { cls: "pill-emerald", dot: "bg-emerald-500" },
  running: { cls: "pill-violet", dot: "bg-violet-500 animate-pulse" },
  pending: { cls: "pill-amber", dot: "bg-amber-500" },
  succeeded: { cls: "pill-emerald", dot: "bg-emerald-500", label: "ok" },
  warning: { cls: "pill-amber", dot: "bg-amber-500" },
  paused: { cls: "pill-zinc", dot: "bg-zinc-400" },
  untested: { cls: "pill-zinc", dot: "bg-zinc-400" },
  unknown: { cls: "pill-zinc", dot: "bg-zinc-400" },
  error: { cls: "pill-rose", dot: "bg-rose-500" },
  failed: { cls: "pill-rose", dot: "bg-rose-500", label: "error" },
  cancelled: { cls: "pill-zinc", dot: "bg-zinc-400" },
};

export function StatusPill({ status }: { status: string }) {
  const key = (status?.toLowerCase() as StatusKind) ?? "unknown";
  const c = config[key] ?? config.unknown;
  return (
    <span className={cn(c.cls)}>
      <span className={cn("status-dot", c.dot)} />
      {c.label ?? key}
    </span>
  );
}

export function StatusDot({ status, className }: { status: string; className?: string }) {
  const key = (status?.toLowerCase() as StatusKind) ?? "unknown";
  const c = config[key] ?? config.unknown;
  return <span className={cn("status-dot", c.dot, className)} />;
}
