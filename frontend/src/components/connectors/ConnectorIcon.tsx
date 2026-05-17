import { cn } from "@/lib/utils";

const palette: Record<string, { bg: string; fg: string; label: string }> = {
  sap: { bg: "bg-sky-100", fg: "text-sky-700", label: "SAP" },
  oracle: { bg: "bg-red-100", fg: "text-red-700", label: "ORA" },
  surreal: { bg: "bg-purple-100", fg: "text-purple-700", label: "SDB" },
  mssql: { bg: "bg-indigo-100", fg: "text-indigo-700", label: "SQL" },
  fabric: { bg: "bg-amber-100", fg: "text-amber-700", label: "FAB" },
  databricks: { bg: "bg-orange-100", fg: "text-orange-700", label: "DBX" },
};

export function ConnectorIcon({
  icon,
  size = 40,
  className,
}: {
  icon: string;
  size?: number;
  className?: string;
}) {
  const conf = palette[icon] ?? { bg: "bg-slate-100", fg: "text-slate-700", label: "EXT" };
  return (
    <div
      style={{ width: size, height: size }}
      className={cn(
        "flex shrink-0 items-center justify-center rounded-lg text-xs font-bold",
        conf.bg,
        conf.fg,
        className,
      )}
    >
      {conf.label}
    </div>
  );
}
