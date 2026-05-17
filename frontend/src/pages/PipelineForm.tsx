import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Plus, Save, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Connection, FieldMapping, ObjectSpec, Pipeline } from "@/types";
import { ConnectorIcon } from "@/components/connectors/ConnectorIcon";

interface FormState {
  name: string;
  description: string;
  source_connection_id: string;
  destination_connection_id: string;
  source_object: string;
  destination_object: string;
  mode: "full" | "incremental";
  field_mappings: FieldMapping[];
  schedule: string;
  enabled: boolean;
}

const initial: FormState = {
  name: "",
  description: "",
  source_connection_id: "",
  destination_connection_id: "",
  source_object: "",
  destination_object: "",
  mode: "full",
  field_mappings: [],
  schedule: "",
  enabled: true,
};

export function PipelineForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>(initial);

  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: () => api.get<Connection[]>("/connections"),
  });
  const existing = useQuery({
    enabled: isEdit,
    queryKey: ["pipeline", id],
    queryFn: () => api.get<Pipeline>(`/pipelines/${id}`),
  });

  useEffect(() => {
    if (existing.data) {
      const p = existing.data;
      setForm({
        name: p.name,
        description: p.description ?? "",
        source_connection_id: p.source_connection_id,
        destination_connection_id: p.destination_connection_id,
        source_object: p.source_object,
        destination_object: p.destination_object,
        mode: (p.mode as "full" | "incremental") ?? "full",
        field_mappings: p.field_mappings ?? [],
        schedule: p.schedule ?? "",
        enabled: p.enabled,
      });
    }
  }, [existing.data]);

  const sources = (connections.data ?? []).filter((c) => c.role === "source");
  const destinations = (connections.data ?? []).filter((c) => c.role === "destination");

  const srcObjects = useQuery({
    enabled: Boolean(form.source_connection_id),
    queryKey: ["objects", form.source_connection_id],
    queryFn: () =>
      api.get<ObjectSpec[]>(`/connections/${form.source_connection_id}/objects`),
  });
  const dstObjects = useQuery({
    enabled: Boolean(form.destination_connection_id),
    queryKey: ["objects", form.destination_connection_id],
    queryFn: () =>
      api.get<ObjectSpec[]>(`/connections/${form.destination_connection_id}/objects`),
  });

  const create = useMutation({
    mutationFn: (payload: FormState) =>
      api.post<Pipeline>("/pipelines", {
        ...payload,
        schedule: payload.schedule || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      navigate("/pipelines");
    },
  });
  const update = useMutation({
    mutationFn: (payload: Partial<FormState>) =>
      api.patch<Pipeline>(`/pipelines/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelines"] });
      navigate("/pipelines");
    },
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    isEdit ? update.mutate(form) : create.mutate(form);
  };

  const addMapping = () =>
    setForm({
      ...form,
      field_mappings: [...form.field_mappings, { source: "", destination: "" }],
    });
  const updateMapping = (i: number, patch: Partial<FieldMapping>) => {
    const next = form.field_mappings.slice();
    next[i] = { ...next[i], ...patch };
    setForm({ ...form, field_mappings: next });
  };
  const removeMapping = (i: number) =>
    setForm({ ...form, field_mappings: form.field_mappings.filter((_, idx) => idx !== i) });

  const srcConn = sources.find((c) => c.id === form.source_connection_id);
  const dstConn = destinations.find((c) => c.id === form.destination_connection_id);

  return (
    <div className="mx-auto max-w-4xl">
      <button onClick={() => navigate(-1)} className="btn-ghost mb-4 -ml-2">
        <ArrowLeft size={16} /> Back
      </button>
      <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
        {isEdit ? "Edit pipeline" : "New pipeline"}
      </h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-6">
        Pipelines move data from a source object to a destination object.
      </p>

      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <section className="card p-5">
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Overview</h3>
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
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Source &amp; destination</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
            <div className="space-y-3">
              <label className="label">Source connection</label>
              <select
                required
                className="input"
                value={form.source_connection_id}
                onChange={(e) =>
                  setForm({ ...form, source_connection_id: e.target.value, source_object: "" })
                }
              >
                <option value="">Select source…</option>
                {sources.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.connector_type})
                  </option>
                ))}
              </select>
              <label className="label">Source object</label>
              <ObjectPicker
                value={form.source_object}
                options={srcObjects.data ?? []}
                loading={srcObjects.isFetching}
                onChange={(v) => setForm({ ...form, source_object: v })}
                placeholder={srcConn ? "Select entity / table" : "Select source first"}
              />
              {srcConn && (
                <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                  <ConnectorIcon icon={srcConn.connector_type.split("_")[0]} size={20} />
                  {srcConn.name}
                </div>
              )}
            </div>
            <div className="hidden md:flex h-full items-center justify-center pt-8 text-zinc-400">
              <ArrowRight />
            </div>
            <div className="space-y-3">
              <label className="label">Destination connection</label>
              <select
                required
                className="input"
                value={form.destination_connection_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    destination_connection_id: e.target.value,
                    destination_object: "",
                  })
                }
              >
                <option value="">Select destination…</option>
                {destinations.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.connector_type})
                  </option>
                ))}
              </select>
              <label className="label">Destination object</label>
              <ObjectPicker
                value={form.destination_object}
                options={dstObjects.data ?? []}
                loading={dstObjects.isFetching}
                onChange={(v) => setForm({ ...form, destination_object: v })}
                allowFree
                placeholder={dstConn ? "Select or type table name" : "Select destination first"}
              />
              {dstConn && (
                <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                  <ConnectorIcon icon={dstConn.connector_type.split("_")[0]} size={20} />
                  {dstConn.name}
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="card p-5">
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Settings</h3>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="label">Mode</label>
              <select
                className="input"
                value={form.mode}
                onChange={(e) => setForm({ ...form, mode: e.target.value as "full" | "incremental" })}
              >
                <option value="full">Full load</option>
                <option value="incremental">Incremental</option>
              </select>
            </div>
            <div>
              <label className="label">Schedule (cron)</label>
              <input
                className="input font-mono"
                placeholder="e.g. 0 */4 * * *"
                value={form.schedule}
                onChange={(e) => setForm({ ...form, schedule: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 pt-7">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-zinc-300 text-bifrost-purple focus:ring-bifrost-purple dark:border-zinc-700"
                checked={form.enabled}
                onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
              />
              <span className="text-sm text-zinc-700 dark:text-zinc-300">Enabled</span>
            </label>
          </div>
        </section>

        <section className="card p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">Field mappings</h3>
            <button type="button" className="btn-secondary" onClick={addMapping}>
              <Plus size={14} /> Add mapping
            </button>
          </div>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Leave empty to pass all source fields through unchanged.
          </p>
          {form.field_mappings.length > 0 && (
            <div className="mt-4 space-y-2">
              {form.field_mappings.map((m, i) => (
                <div key={i} className="grid grid-cols-[1fr_auto_1fr_auto] items-center gap-2">
                  <input
                    className="input"
                    placeholder="Source field"
                    value={m.source}
                    onChange={(e) => updateMapping(i, { source: e.target.value })}
                  />
                  <ArrowRight size={14} className="text-zinc-400" />
                  <input
                    className="input"
                    placeholder="Destination field"
                    value={m.destination}
                    onChange={(e) => updateMapping(i, { destination: e.target.value })}
                  />
                  <button
                    type="button"
                    onClick={() => removeMapping(i)}
                    className="btn-ghost text-red-600"
                    aria-label="Remove mapping"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="btn-primary"
            disabled={create.isPending || update.isPending}
          >
            <Save size={16} /> {isEdit ? "Save changes" : "Create pipeline"}
          </button>
          <button type="button" className="btn-ghost ml-auto" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>

        {(create.error || update.error) && (
          <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
            {(create.error || update.error)?.message}
          </div>
        )}
      </form>
    </div>
  );
}

function ObjectPicker({
  value,
  options,
  loading,
  onChange,
  placeholder,
  allowFree,
}: {
  value: string;
  options: ObjectSpec[];
  loading: boolean;
  onChange: (v: string) => void;
  placeholder?: string;
  allowFree?: boolean;
}) {
  if (!options.length && !loading) {
    return (
      <input
        className="input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (allowFree) {
    return (
      <>
        <input
          className="input"
          list="object-list"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <datalist id="object-list">
          {options.map((o) => (
            <option key={o.name} value={o.name} />
          ))}
        </datalist>
      </>
    );
  }
  return (
    <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{loading ? "Loading…" : placeholder}</option>
      {options.map((o) => (
        <option key={o.name} value={o.name}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
