import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ConnectorMetadata } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";

export function Settings() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<{ status: string; app: string; env: string }>("/health"),
  });
  const connectors = useQuery({
    queryKey: ["connector-metadata"],
    queryFn: () => api.get<ConnectorMetadata[]>("/connectors"),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Settings</h2>
        <p className="text-sm text-slate-500">
          Platform information and installed connectors.
        </p>
      </div>

      <section className="card p-5">
        <h3 className="font-semibold text-slate-900">System</h3>
        <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Info label="Status" value={health.data?.status ?? "—"} />
          <Info label="Environment" value={health.data?.env ?? "—"} />
          <Info label="App" value={health.data?.app ?? "—"} />
        </dl>
      </section>

      <section className="card p-5">
        <h3 className="font-semibold text-slate-900">Installed connectors</h3>
        <p className="mt-1 text-xs text-slate-500">
          Connectors are loaded from the backend connector registry. Drop a new
          connector module into <code>app/connectors/sources</code> or{" "}
          <code>app/connectors/destinations</code> and it will appear here.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {connectors.data?.map((c) => (
            <div key={c.type} className="flex items-start gap-3 rounded-lg border border-slate-200 p-3">
              <ConnectorIcon icon={c.icon} />
              <div>
                <div className="font-medium text-slate-900">{c.label}</div>
                <div className="text-xs text-slate-500">{c.description}</div>
                <div className="mt-1">
                  <span className="badge-slate capitalize">{c.role}</span>
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
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-sm font-medium text-slate-900 capitalize">{value}</dd>
    </div>
  );
}
