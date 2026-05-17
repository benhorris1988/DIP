import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  succeeded: "badge-green",
  healthy: "badge-green",
  running: "badge-blue",
  pending: "badge-amber",
  untested: "badge-slate",
  unknown: "badge-slate",
  error: "badge-red",
  failed: "badge-red",
  cancelled: "badge-slate",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = variants[status] ?? "badge-slate";
  return <span className={cn(cls)}>{status}</span>;
}
