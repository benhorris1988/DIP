// ignore_for_file: invalid_annotation_target

/// Plain data classes mirroring the FastAPI schemas. Hand-rolled (no codegen)
/// to keep the bootstrap lightweight.

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
        configFields: (j['config_fields'] as List? ?? [])
            .map((e) => ConfigField.fromJson(e as Map<String, dynamic>))
            .toList(),
        credentialFields: (j['credential_fields'] as List? ?? [])
            .map((e) => ConfigField.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class ConfigField {
  final String name;
  final String label;
  final String type;
  final bool required;
  final String? helpText;
  final dynamic defaultValue;
  final List<String>? options;
  final bool secret;

  ConfigField({
    required this.name,
    required this.label,
    required this.type,
    required this.required,
    this.helpText,
    this.defaultValue,
    this.options,
    this.secret = false,
  });

  factory ConfigField.fromJson(Map<String, dynamic> j) => ConfigField(
        name: j['name'] as String,
        label: j['label'] as String,
        type: (j['type'] ?? 'string') as String,
        required: (j['required'] ?? false) as bool,
        helpText: j['help_text'] as String?,
        defaultValue: j['default'],
        options: (j['options'] as List?)?.map((e) => e.toString()).toList(),
        secret: (j['secret'] ?? false) as bool,
      );
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
    required this.createdAt,
    required this.updatedAt,
  });

  factory Pipeline.fromJson(Map<String, dynamic> j) => Pipeline(
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
        createdAt: (j['created_at'] ?? '') as String,
        updatedAt: (j['updated_at'] ?? '') as String,
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
