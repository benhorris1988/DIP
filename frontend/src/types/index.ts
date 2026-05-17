export type Role = "source" | "destination";

export interface ConnectorField {
  name: string;
  label: string;
  type: "string" | "password" | "number" | "boolean" | "select";
  required?: boolean;
  default?: unknown;
  options?: string[];
  placeholder?: string;
}

export interface ConnectorMetadata {
  type: string;
  label: string;
  role: Role;
  description: string;
  icon: string;
  config_schema: ConnectorField[];
  secret_schema: ConnectorField[];
}

export interface Connection {
  id: string;
  name: string;
  description: string | null;
  connector_type: string;
  role: Role;
  config: Record<string, unknown>;
  status: string;
  last_tested_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FieldMapping {
  source: string;
  destination: string;
  transform?: string | null;
}

export interface Pipeline {
  id: string;
  name: string;
  description: string | null;
  source_connection_id: string;
  destination_connection_id: string;
  source_object: string;
  destination_object: string;
  mode: string;
  field_mappings: FieldMapping[];
  transform: Record<string, unknown>;
  schedule: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  pipeline_id: string;
  pipeline_name: string;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  rows_read: number;
  rows_written: number;
  rows_failed: number;
  duration_ms: number;
  triggered_by: string;
  error: string | null;
  log: { ts: string; level: string; message: string }[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface Stats {
  pipelines: number;
  connections: number;
  jobs: number;
  succeeded: number;
  failed: number;
  rows_written: number;
}

export interface ObjectSpec {
  name: string;
  label: string;
  fields: { name: string; type: string; nullable: boolean; primary_key: boolean }[];
}
