import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save, Zap } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection, ConnectorField, ConnectorMetadata, Role } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";

interface FormState {
  name: string;
  description: string;
  connector_type: string;
  role: Role;
  config: Record<string, unknown>;
  secrets: Record<string, unknown>;
}

const initial: FormState = {
  name: "",
  description: "",
  connector_type: "",
  role: "source",
  config: {},
  secrets: {},
};

export function ConnectionForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [form, setForm] = useState<FormState>(initial);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  const connectors = useQuery({
    queryKey: ["connector-metadata"],
    queryFn: () => api.get<ConnectorMetadata[]>("/connectors"),
  });
  const existing = useQuery({
    enabled: isEdit,
    queryKey: ["connection", id],
    queryFn: () => api.get<Connection>(`/connections/${id}`),
  });

  useEffect(() => {
    if (existing.data) {
      setForm({
        name: existing.data.name,
        description: existing.data.description ?? "",
        connector_type: existing.data.connector_type,
        role: existing.data.role,
        config: existing.data.config ?? {},
        secrets: {},
      });
    }
  }, [existing.data]);

  const currentMeta = useMemo(
    () => connectors.data?.find((c) => c.type === form.connector_type),
    [connectors.data, form.connector_type],
  );

  const create = useMutation({
    mutationFn: (payload: FormState) => api.post<Connection>("/connections", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      navigate("/connections");
    },
  });

  const update = useMutation({
    mutationFn: (payload: Partial<FormState>) =>
      api.patch<Connection>(`/connections/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      navigate("/connections");
    },
  });

  const test = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string }>(`/connections/${id}/test`),
    onSuccess: (r) => setTestResult(r),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isEdit) {
      const payload: Partial<FormState> = {
        name: form.name,
        description: form.description,
        config: form.config,
      };
      if (Object.keys(form.secrets).length) payload.secrets = form.secrets;
      update.mutate(payload);
    } else {
      create.mutate(form);
    }
  };

  const setConfig = (k: string, v: unknown) =>
    setForm((f) => ({ ...f, config: { ...f.config, [k]: v } }));
  const setSecret = (k: string, v: unknown) =>
    setForm((f) => ({ ...f, secrets: { ...f.secrets, [k]: v } }));

  const filtered = (connectors.data ?? []).filter((c) => c.role === form.role);

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => navigate(-1)} className="btn-ghost mb-4 -ml-2">
        <ArrowLeft size={16} /> Back
      </button>
      <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
        {isEdit ? "Edit connection" : "New connection"}
      </h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
        Configure how the platform connects to your source or destination system.
      </p>

      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        {!isEdit && (
          <section className="card p-5">
            <div className="mb-4 flex gap-1 rounded-lg bg-zinc-200/60 dark:bg-zinc-800/60 p-1 w-fit">
              {(["source", "destination"] as Role[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setForm({ ...form, role: r, connector_type: "" })}
                  className={
                    "px-3 py-1.5 text-sm font-medium rounded-md " +
                    (form.role === r
                      ? "bg-white text-zinc-900 dark:text-zinc-100 shadow-sm"
                      : "text-zinc-600 dark:text-zinc-400")
                  }
                >
                  {r === "source" ? "Source" : "Destination"}
                </button>
              ))}
            </div>
            <label className="label">Connector type</label>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {filtered.map((c) => (
                <button
                  type="button"
                  key={c.type}
                  onClick={() => setForm({ ...form, connector_type: c.type })}
                  className={
                    "flex items-start gap-3 rounded-lg border p-3 text-left transition-colors " +
                    (form.connector_type === c.type
                      ? "border-bifrost-purple bg-violet-50/50 dark:bg-violet-500/10"
                      : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700")
                  }
                >
                  <ConnectorIcon icon={c.icon} size={36} />
                  <div>
                    <div className="font-medium text-zinc-900 dark:text-zinc-100">{c.label}</div>
                    <div className="text-xs text-zinc-500 dark:text-zinc-400">{c.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {form.connector_type && (
          <>
            <section className="card p-5">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Details</h3>
              <div className="mt-4 grid grid-cols-1 gap-4">
                <div>
                  <label className="label">Name</label>
                  <input
                    required
                    className="input"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Description</label>
                  <textarea
                    className="input"
                    rows={2}
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                  />
                </div>
              </div>
            </section>

            <section className="card p-5">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Configuration</h3>
              <div className="mt-4 grid grid-cols-1 gap-4">
                {currentMeta?.config_schema.map((f) => (
                  <FieldInput
                    key={f.name}
                    field={f}
                    value={form.config[f.name]}
                    onChange={(v) => setConfig(f.name, v)}
                  />
                ))}
              </div>
            </section>

            <section className="card p-5">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Credentials</h3>
              {isEdit && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                  Leave blank to keep the existing credentials.
                </p>
              )}
              <div className="mt-4 grid grid-cols-1 gap-4">
                {currentMeta?.secret_schema.map((f) => (
                  <FieldInput
                    key={f.name}
                    field={f}
                    value={form.secrets[f.name]}
                    onChange={(v) => setSecret(f.name, v)}
                  />
                ))}
              </div>
            </section>
          </>
        )}

        <div className="flex items-center gap-2">
          <button type="submit" className="btn-primary" disabled={create.isPending || update.isPending}>
            <Save size={16} /> {isEdit ? "Save changes" : "Create connection"}
          </button>
          {isEdit && (
            <button
              type="button"
              className="btn-secondary"
              onClick={() => test.mutate()}
              disabled={test.isPending}
            >
              <Zap size={16} /> Test connection
            </button>
          )}
          <button type="button" className="btn-ghost ml-auto" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>

        {testResult && (
          <div
            className={
              "rounded-md px-3 py-2 text-sm " +
              (testResult.ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800")
            }
          >
            {testResult.message}
          </div>
        )}
        {(create.error || update.error) && (
          <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
            {(create.error || update.error)?.message}
          </div>
        )}
      </form>
    </div>
  );
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: ConnectorField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (field.type === "boolean") {
    return (
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          className="h-4 w-4 rounded border-zinc-300 text-bifrost-purple focus:ring-bifrost-purple dark:border-zinc-700"
          checked={Boolean(value ?? field.default)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="text-sm text-zinc-700 dark:text-zinc-300">{field.label}</span>
      </label>
    );
  }
  if (field.type === "select") {
    return (
      <div>
        <label className="label">{field.label}</label>
        <select
          className="input"
          value={String(value ?? field.default ?? "")}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
        >
          <option value="">Select…</option>
          {field.options?.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </div>
    );
  }
  return (
    <div>
      <label className="label">
        {field.label}
        {field.required && <span className="text-red-500"> *</span>}
      </label>
      <input
        className="input"
        type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
        required={field.required}
        placeholder={field.placeholder}
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) =>
          onChange(
            field.type === "number"
              ? e.target.value === ""
                ? undefined
                : Number(e.target.value)
              : e.target.value,
          )
        }
      />
    </div>
  );
}
