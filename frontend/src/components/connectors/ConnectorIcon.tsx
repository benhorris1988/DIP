import { cn } from "@/lib/utils";

const palette: Record<string, { bg: string; fg: string; label: string }> = {
  sap: {
    bg: "bg-sky-100 dark:bg-sky-500/15",
    fg: "text-sky-700 dark:text-sky-300",
    label: "SAP",
  },
  oracle: {
    bg: "bg-rose-100 dark:bg-rose-500/15",
    fg: "text-rose-700 dark:text-rose-300",
    label: "ORA",
  },
  surreal: {
    bg: "bg-violet-100 dark:bg-violet-500/15",
    fg: "text-violet-700 dark:text-violet-300",
    label: "SDB",
  },
  mssql: {
    bg: "bg-indigo-100 dark:bg-indigo-500/15",
    fg: "text-indigo-700 dark:text-indigo-300",
    label: "SQL",
  },
  fabric: {
    bg: "bg-amber-100 dark:bg-amber-500/15",
    fg: "text-amber-700 dark:text-amber-300",
    label: "FAB",
  },
  databricks: {
    bg: "bg-orange-100 dark:bg-orange-500/15",
    fg: "text-orange-700 dark:text-orange-300",
    label: "DBX",
  },
};

export function ConnectorIcon({
  icon,
  size = 32,
  className,
}: {
  icon: string;
  size?: number;
  className?: string;
}) {
  const conf =
    palette[icon] ?? {
      bg: "bg-zinc-100 dark:bg-zinc-800",
      fg: "text-zinc-700 dark:text-zinc-300",
      label: "EXT",
    };
  return (
    <div
      style={{ width: size, height: size }}
      className={cn(
        "flex shrink-0 items-center justify-center rounded-lg text-[10px] font-bold tracking-wider",
        conf.bg,
        conf.fg,
        className,
      )}
    >
      {conf.label}
    </div>
  );
}
