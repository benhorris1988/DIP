// ignore_for_file: invalid_annotation_target

/// Plain data classes mirroring the FastAPI schemas. Hand-rolled (no codegen)
/// to keep the bootstrap lightweight.

String _humanDuration(int seconds) {
  if (seconds < 60) return '${seconds}s';
  final m = seconds ~/ 60;
  if (m < 60) return '${m}m';
  final h = m ~/ 60;
  if (h < 24) return '${h}h';
  final d = h ~/ 24;
  return '${d}d';
}

class ConnectorMetadata {
  final String type;
  final String label;
  final String role;
  final String description;
  final String icon;
  final List<ConfigField> configFields;
  final List<ConfigField> credentialFields;

  ConnectorMetadata({
    required this.type,
    required this.label,
    required this.role,
    required this.description,
    required this.icon,
    required this.configFields,
    required this.credentialFields,
  });

  factory ConnectorMetadata.fromJson(Map<String, dynamic> j) => ConnectorMetadata(
        type: j['type'] as String,
        label: j['label'] as String,
        role: j['role'] as String,
        description: (j['description'] ?? '') as String,
        icon: (j['icon'] ?? 'plug') as String,
        // Backend serialises the connector metadata dataclass, so the keys are
        // `config_schema` / `secret_schema`. Secret-schema fields are always
        // rendered as obscured credential inputs.
        configFields: (j['config_schema'] as List? ?? [])
            .map((e) => ConfigField.fromJson(e as Map<String, dynamic>))
            .toList(),
        credentialFields: (j['secret_schema'] as List? ?? [])
            .map((e) =>
                ConfigField.fromJson(e as Map<String, dynamic>, secret: true))
            .toList(),
      );
}

class ConfigField {
  final String name;
  final String label;
  final String type;
  final bool required;
  final String? helpText;
  final String? placeholder;
  final dynamic defaultValue;
  final List<String>? options;
  final bool secret;

  ConfigField({
    required this.name,
    required this.label,
    required this.type,
    required this.required,
    this.helpText,
    this.placeholder,
    this.defaultValue,
    this.options,
    this.secret = false,
  });

  factory ConfigField.fromJson(Map<String, dynamic> j, {bool secret = false}) {
    final type = (j['type'] ?? 'string') as String;
    return ConfigField(
      name: j['name'] as String,
      label: j['label'] as String,
      type: type,
      required: (j['required'] ?? false) as bool,
      helpText: (j['help_text'] ?? j['help']) as String?,
      placeholder: j['placeholder'] as String?,
      defaultValue: j['default'],
      options: (j['options'] as List?)?.map((e) => e.toString()).toList(),
      secret: secret || type == 'password',
    );
  }
}

class Connection {
  final String id;
  final String name;
  final String? description;
  final String connectorType;
  final String role;
  final Map<String, dynamic> config;
  final String status;
  final String? lastTestedAt;
  final String? lastError;
  final String createdAt;
  final String updatedAt;

  Connection({
    required this.id,
    required this.name,
    required this.description,
    required this.connectorType,
    required this.role,
    required this.config,
    required this.status,
    required this.lastTestedAt,
    required this.lastError,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Connection.fromJson(Map<String, dynamic> j) => Connection(
        id: j['id'] as String,
        name: j['name'] as String,
        description: j['description'] as String?,
        connectorType: j['connector_type'] as String,
        role: j['role'] as String,
        config: Map<String, dynamic>.from(j['config'] ?? {}),
        status: (j['status'] ?? 'untested') as String,
        lastTestedAt: j['last_tested_at'] as String?,
        lastError: j['last_error'] as String?,
        createdAt: (j['created_at'] ?? '') as String,
        updatedAt: (j['updated_at'] ?? '') as String,
      );
}

class FieldMapping {
  final String source;
  final String destination;
  final String? transform;

  FieldMapping({required this.source, required this.destination, this.transform});

  factory FieldMapping.fromJson(Map<String, dynamic> j) => FieldMapping(
        source: j['source'] as String,
        destination: j['destination'] as String,
        transform: j['transform'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'source': source,
        'destination': destination,
        if (transform != null && transform!.isNotEmpty) 'transform': transform,
      };
}

/// A single transformation step in a pipeline's transform plan.
class TransformStep {
  final String type;
  final Map<String, dynamic> config;
  final bool enabled;

  TransformStep({
    required this.type,
    Map<String, dynamic>? config,
    this.enabled = true,
  }) : config = config ?? <String, dynamic>{};

  TransformStep copyWith({
    String? type,
    Map<String, dynamic>? config,
    bool? enabled,
  }) =>
      TransformStep(
        type: type ?? this.type,
        config: config ?? Map<String, dynamic>.from(this.config),
        enabled: enabled ?? this.enabled,
      );

  factory TransformStep.fromJson(Map<String, dynamic> j) => TransformStep(
        type: j['type'] as String,
        config: Map<String, dynamic>.from(j['config'] as Map? ?? const {}),
        enabled: (j['enabled'] ?? true) as bool,
      );

  Map<String, dynamic> toJson() => {
        'type': type,
        'config': config,
        'enabled': enabled,
      };
}

class Pipeline {
  final String id;
  final String name;
  final String? description;
  final String sourceConnectionId;
  final String sourceObject;
  final String destinationConnectionId;
  final String destinationObject;
  final String mode;
  final String? schedule;
  final bool enabled;
  final String? incrementalField;
  final List<FieldMapping> fieldMappings;
  final List<TransformStep> transformSteps;
  final String onError; // "skip" | "fail"
  final String definitionSource;
  final String? definitionPath;
  final String createdAt;
  final String updatedAt;

  Pipeline({
    required this.id,
    required this.name,
    required this.description,
    required this.sourceConnectionId,
    required this.sourceObject,
    required this.destinationConnectionId,
    required this.destinationObject,
    required this.mode,
    required this.schedule,
    required this.enabled,
    required this.incrementalField,
    required this.fieldMappings,
    required this.transformSteps,
    required this.onError,
    required this.definitionSource,
    required this.definitionPath,
    required this.createdAt,
    required this.updatedAt,
  });

  bool get isYamlManaged => definitionSource == 'yaml';

  factory Pipeline.fromJson(Map<String, dynamic> j) {
    final transform = Map<String, dynamic>.from(j['transform'] as Map? ?? const {});
    return Pipeline(
      id: j['id'] as String,
      name: j['name'] as String,
      description: j['description'] as String?,
      sourceConnectionId: j['source_connection_id'] as String,
      sourceObject: j['source_object'] as String,
      destinationConnectionId: j['destination_connection_id'] as String,
      destinationObject: j['destination_object'] as String,
      mode: j['mode'] as String,
      schedule: j['schedule'] as String?,
      enabled: (j['enabled'] ?? true) as bool,
      incrementalField: j['incremental_field'] as String?,
      fieldMappings: (j['field_mappings'] as List? ?? [])
          .map((e) => FieldMapping.fromJson(e as Map<String, dynamic>))
          .toList(),
      transformSteps: (transform['steps'] as List? ?? const [])
          .map((e) => TransformStep.fromJson(e as Map<String, dynamic>))
          .toList(),
      onError: (transform['on_error'] ?? 'skip') as String,
      definitionSource: (j['definition_source'] ?? 'ui') as String,
      definitionPath: j['definition_path'] as String?,
      createdAt: (j['created_at'] ?? '') as String,
      updatedAt: (j['updated_at'] ?? '') as String,
    );
  }
}

/// Metadata describing a single config field of a transform type.
class TransformFieldSpec {
  final String name;
  final String label;
  final String type; // string | text | code | select | boolean | columns
  final bool required;
  final String? placeholder;
  final String? help;
  final List<String>? options;
  final dynamic defaultValue;

  TransformFieldSpec({
    required this.name,
    required this.label,
    required this.type,
    required this.required,
    this.placeholder,
    this.help,
    this.options,
    this.defaultValue,
  });

  factory TransformFieldSpec.fromJson(Map<String, dynamic> j) => TransformFieldSpec(
        name: j['name'] as String,
        label: j['label'] as String,
        type: (j['type'] ?? 'string') as String,
        required: (j['required'] ?? false) as bool,
        placeholder: j['placeholder'] as String?,
        help: j['help'] as String?,
        options: (j['options'] as List?)?.map((e) => e.toString()).toList(),
        defaultValue: j['default'],
      );
}

/// Catalog entry for an available transform type (drives the builder UI).
class TransformCatalogEntry {
  final String type;
  final String label;
  final String category; // schema | values | python | rows
  final String icon;
  final String description;
  final List<TransformFieldSpec> fields;
  final String? example;

  TransformCatalogEntry({
    required this.type,
    required this.label,
    required this.category,
    required this.icon,
    required this.description,
    required this.fields,
    this.example,
  });

  factory TransformCatalogEntry.fromJson(Map<String, dynamic> j) =>
      TransformCatalogEntry(
        type: j['type'] as String,
        label: j['label'] as String,
        category: (j['category'] ?? 'values') as String,
        icon: (j['icon'] ?? 'transform') as String,
        description: (j['description'] ?? '') as String,
        fields: (j['fields'] as List? ?? const [])
            .map((e) => TransformFieldSpec.fromJson(e as Map<String, dynamic>))
            .toList(),
        example: j['example'] as String?,
      );
}

class JobLogEntry {
  final String ts;
  final String level;
  final String message;
  JobLogEntry({required this.ts, required this.level, required this.message});
  factory JobLogEntry.fromJson(Map<String, dynamic> j) => JobLogEntry(
        ts: j['ts'] as String,
        level: (j['level'] ?? 'info') as String,
        message: j['message'] as String,
      );
}

class Job {
  final String id;
  final String pipelineId;
  final String pipelineName;
  final String status;
  final String? startedAt;
  final String? finishedAt;
  final int durationMs;
  final int rowsRead;
  final int rowsWritten;
  final int rowsFailed;
  final String? error;
  final String triggeredBy;
  final List<JobLogEntry> log;

  Job({
    required this.id,
    required this.pipelineId,
    required this.pipelineName,
    required this.status,
    required this.startedAt,
    required this.finishedAt,
    required this.durationMs,
    required this.rowsRead,
    required this.rowsWritten,
    required this.rowsFailed,
    required this.error,
    required this.triggeredBy,
    required this.log,
  });

  factory Job.fromJson(Map<String, dynamic> j) => Job(
        id: j['id'] as String,
        pipelineId: j['pipeline_id'] as String,
        pipelineName: (j['pipeline_name'] ?? '') as String,
        status: j['status'] as String,
        startedAt: j['started_at'] as String?,
        finishedAt: j['finished_at'] as String?,
        durationMs: (j['duration_ms'] ?? 0) as int,
        rowsRead: (j['rows_read'] ?? 0) as int,
        rowsWritten: (j['rows_written'] ?? 0) as int,
        rowsFailed: (j['rows_failed'] ?? 0) as int,
        error: j['error'] as String?,
        triggeredBy: (j['triggered_by'] ?? 'manual') as String,
        log: (j['log'] as List? ?? [])
            .map((e) => JobLogEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class AssetWithStatus {
  final String id;
  final String key;
  final String? description;
  final String pipelineId;
  final String? pipelineName;
  final String? connectionId;
  final String? objectName;
  final List<String> dependsOn;
  final Map<String, dynamic> metadata;
  final Map<String, dynamic> freshnessPolicy;
  final String? definitionPath;
  final String? lastMaterializedAt;
  final String? lastJobId;
  final String? lastStatus;
  final int? rowsWritten;

  bool get hasFreshnessPolicy => freshnessPolicy.isNotEmpty;

  /// Human-readable "auto · 1h" string, or empty when no policy is set.
  String get freshnessLabel {
    final m = freshnessPolicy['max_age_minutes'];
    final h = freshnessPolicy['max_age_hours'];
    final parts = <String>[];
    if (m is num) parts.add(_humanDuration(m.toInt() * 60));
    if (h is num) parts.add(_humanDuration((h * 3600).toInt()));
    if (parts.isEmpty) return '';
    return parts.reduce((a, b) => a.length <= b.length ? a : b);
  }

  AssetWithStatus({
    required this.id,
    required this.key,
    required this.description,
    required this.pipelineId,
    required this.pipelineName,
    required this.connectionId,
    required this.objectName,
    required this.dependsOn,
    required this.metadata,
    required this.freshnessPolicy,
    required this.definitionPath,
    required this.lastMaterializedAt,
    required this.lastJobId,
    required this.lastStatus,
    required this.rowsWritten,
  });

  factory AssetWithStatus.fromJson(Map<String, dynamic> j) => AssetWithStatus(
        id: j['id'] as String,
        key: j['key'] as String,
        description: j['description'] as String?,
        pipelineId: j['pipeline_id'] as String,
        pipelineName: j['pipeline_name'] as String?,
        connectionId: j['connection_id'] as String?,
        objectName: j['object_name'] as String?,
        dependsOn:
            (j['depends_on'] as List? ?? const []).map((e) => e.toString()).toList(),
        metadata:
            Map<String, dynamic>.from(j['asset_metadata'] as Map? ?? const {}),
        freshnessPolicy: Map<String, dynamic>.from(
            j['freshness_policy'] as Map? ?? const {}),
        definitionPath: j['definition_path'] as String?,
        lastMaterializedAt: j['last_materialized_at'] as String?,
        lastJobId: j['last_job_id'] as String?,
        lastStatus: j['last_status'] as String?,
        rowsWritten: j['rows_written'] as int?,
      );
}

class AssetGraph {
  final List<List<String>> layers;
  final List<AssetWithStatus> nodes;

  AssetGraph({required this.layers, required this.nodes});

  factory AssetGraph.fromJson(Map<String, dynamic> j) => AssetGraph(
        layers: (j['layers'] as List? ?? const [])
            .map<List<String>>(
              (row) =>
                  (row as List).map((e) => e.toString()).toList(),
            )
            .toList(),
        nodes: (j['nodes'] as List? ?? const [])
            .map((e) => AssetWithStatus.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class AssetMaterializationRecord {
  final String id;
  final String assetKey;
  final String jobId;
  final String pipelineId;
  final String? dagRunId;
  final int rowsWritten;
  final String ts;

  AssetMaterializationRecord({
    required this.id,
    required this.assetKey,
    required this.jobId,
    required this.pipelineId,
    required this.dagRunId,
    required this.rowsWritten,
    required this.ts,
  });

  factory AssetMaterializationRecord.fromJson(Map<String, dynamic> j) =>
      AssetMaterializationRecord(
        id: j['id'] as String,
        assetKey: j['asset_key'] as String,
        jobId: j['job_id'] as String,
        pipelineId: j['pipeline_id'] as String,
        dagRunId: j['dag_run_id'] as String?,
        rowsWritten: (j['rows_written'] ?? 0) as int,
        ts: j['ts'] as String,
      );
}

class DefinitionsReport {
  final String directory;
  final int pipelinesTotal;
  final int assetsTotal;
  final int errors;
  final List<String> removedPipelines;
  final List<DefinitionsEntry> entries;

  DefinitionsReport({
    required this.directory,
    required this.pipelinesTotal,
    required this.assetsTotal,
    required this.errors,
    required this.removedPipelines,
    required this.entries,
  });

  factory DefinitionsReport.fromJson(Map<String, dynamic> j) =>
      DefinitionsReport(
        directory: (j['directory'] ?? '') as String,
        pipelinesTotal: (j['pipelines_total'] ?? 0) as int,
        assetsTotal: (j['assets_total'] ?? 0) as int,
        errors: (j['errors'] ?? 0) as int,
        removedPipelines: (j['removed_pipelines'] as List? ?? const [])
            .map((e) => e.toString())
            .toList(),
        entries: (j['entries'] as List? ?? const [])
            .map((e) => DefinitionsEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class DefinitionsEntry {
  final String path;
  final String? pipeline;
  final List<String> assets;
  final String action;
  final String? error;

  DefinitionsEntry({
    required this.path,
    required this.pipeline,
    required this.assets,
    required this.action,
    required this.error,
  });

  factory DefinitionsEntry.fromJson(Map<String, dynamic> j) =>
      DefinitionsEntry(
        path: j['path'] as String,
        pipeline: j['pipeline'] as String?,
        assets: (j['assets'] as List? ?? const [])
            .map((e) => e.toString())
            .toList(),
        action: (j['action'] ?? 'synced') as String,
        error: j['error'] as String?,
      );
}

class Stats {
  final int connections;
  final int pipelines;
  final int jobs;
  final int succeeded;
  final int failed;
  final int running;

  Stats({
    required this.connections,
    required this.pipelines,
    required this.jobs,
    required this.succeeded,
    required this.failed,
    required this.running,
  });

  factory Stats.fromJson(Map<String, dynamic> j) => Stats(
        connections: (j['connections'] ?? 0) as int,
        pipelines: (j['pipelines'] ?? 0) as int,
        jobs: (j['jobs'] ?? 0) as int,
        succeeded: (j['succeeded'] ?? 0) as int,
        failed: (j['failed'] ?? 0) as int,
        running: (j['running'] ?? 0) as int,
      );
}
