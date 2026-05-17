import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ConnectorMetadata } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";
import { useTheme } from "@/lib/theme";

export function Settings() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () =>
      api.get<{ status: string; app: string; env: string }>("/health"),
  });
  const connectors = useQuery({
    queryKey: ["connector-metadata"],
    queryFn: () => api.get<ConnectorMetadata[]>("/connectors"),
  });
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Settings
        </h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Platform information and installed connectors.
        </p>
      </div>

      <section className="card p-4">
        <h3 className="text-sm font-semibold">System</h3>
        <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Info label="Status" value={health.data?.status ?? "—"} />
          <Info label="Environment" value={health.data?.env ?? "—"} />
          <Info label="App" value={health.data?.app ?? "—"} />
        </dl>
      </section>

      <section className="card p-4">
        <h3 className="text-sm font-semibold">Appearance</h3>
        <div className="mt-3 flex gap-1 rounded-lg bg-zinc-200/60 p-1 w-fit dark:bg-zinc-800/60">
          {(["light", "dark"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={
                "px-3 py-1 text-xs font-medium rounded-md capitalize " +
                (theme === t
                  ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-100"
                  : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100")
              }
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      <section className="card p-4">
        <h3 className="text-sm font-semibold">Installed connectors</h3>
        <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400">
          Connectors are loaded from the backend connector registry. Drop a new
          connector module into <code>app/connectors/sources</code> or{" "}
          <code>app/connectors/destinations</code> and it will appear here.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
          {connectors.data?.map((c) => (
            <div
              key={c.type}
              className="flex items-start gap-3 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
            >
              <ConnectorIcon icon={c.icon} />
              <div>
                <div className="font-mono text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {c.label}
                </div>
                <div className="text-[11px] text-zinc-500">{c.description}</div>
                <div className="mt-1">
                  <span className="pill-zinc capitalize">{c.role}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </dt>
      <dd className="text-xs font-medium text-zinc-900 capitalize dark:text-zinc-100">
        {value}
      </dd>
    </div>
  );
}
