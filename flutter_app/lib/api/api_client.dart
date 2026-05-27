import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'models.dart';

/// Base URL of the FastAPI backend. Override at build time with
/// --dart-define=API_BASE_URL=https://your-host/api
const String _baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: kIsWeb ? '/api' : 'http://localhost:8000/api',
);

class ApiException implements Exception {
  final int? statusCode;
  final String message;
  ApiException(this.message, {this.statusCode});
  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiClient {
  ApiClient({String? baseUrl})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl ?? _baseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 30),
          headers: const {'Content-Type': 'application/json'},
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onResponse: (r, handler) {
        // Detect the classic "API_BASE_URL points at the SPA, not the
        // backend" foot-gun: the request 200'd but returned text/html.
        // Dio's `data as Map<...>` would otherwise blow up downstream
        // with a useless TypeError on the HTML body.
        final ct = r.headers.value('content-type') ?? '';
        final isJsonRequest =
            !r.requestOptions.responseType.toString().contains('stream');
        if (isJsonRequest && ct.startsWith('text/html')) {
          handler.reject(DioException(
            requestOptions: r.requestOptions,
            response: r,
            error: ApiException(
              'API returned HTML instead of JSON. Is API_BASE_URL pointing at '
              'the backend? Got ${r.requestOptions.uri}',
              statusCode: r.statusCode,
            ),
          ));
          return;
        }
        handler.next(r);
      },
      onError: (e, handler) {
        final msg = _extractError(e);
        handler.reject(DioException(
          requestOptions: e.requestOptions,
          response: e.response,
          error: ApiException(msg, statusCode: e.response?.statusCode),
        ));
      },
    ));
  }

  final Dio _dio;
  String get baseUrl => _dio.options.baseUrl;

  String _extractError(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) return data['detail'].toString();
    if (data is String) return data;
    return e.message ?? 'Network error';
  }

  // Health
  Future<Map<String, dynamic>> health() async {
    final r = await _dio.get('/health');
    return Map<String, dynamic>.from(r.data as Map);
  }

  // Connector metadata
  Future<List<ConnectorMetadata>> connectors() async {
    final r = await _dio.get('/connectors');
    return (r.data as List)
        .map((e) => ConnectorMetadata.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // Transform catalog
  Future<List<TransformCatalogEntry>> transforms() async {
    final r = await _dio.get('/transforms');
    return (r.data as List)
        .map((e) => TransformCatalogEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // Connections
  Future<List<Connection>> connections({String? role}) async {
    final r = await _dio.get('/connections',
        queryParameters: role != null ? {'role': role} : null);
    return (r.data as List)
        .map((e) => Connection.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Connection> connection(String id) async {
    final r = await _dio.get('/connections/$id');
    return Connection.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Connection> createConnection(Map<String, dynamic> body) async {
    final r = await _dio.post('/connections', data: body);
    return Connection.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Connection> updateConnection(
      String id, Map<String, dynamic> body) async {
    final r = await _dio.patch('/connections/$id', data: body);
    return Connection.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> deleteConnection(String id) async {
    await _dio.delete('/connections/$id');
  }

  Future<Map<String, dynamic>> testConnection(String id) async {
    final r = await _dio.post('/connections/$id/test');
    return Map<String, dynamic>.from(r.data as Map);
  }

  Future<List<String>> listObjects(String id) async {
    final r = await _dio.get('/connections/$id/objects');
    return (r.data as List).map((e) => e.toString()).toList();
  }

  // Pipelines
  Future<List<Pipeline>> pipelines() async {
    final r = await _dio.get('/pipelines');
    return (r.data as List)
        .map((e) => Pipeline.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Pipeline> pipeline(String id) async {
    final r = await _dio.get('/pipelines/$id');
    return Pipeline.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Pipeline> createPipeline(Map<String, dynamic> body) async {
    final r = await _dio.post('/pipelines', data: body);
    return Pipeline.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Pipeline> updatePipeline(String id, Map<String, dynamic> body) async {
    final r = await _dio.patch('/pipelines/$id', data: body);
    return Pipeline.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> deletePipeline(String id) async {
    await _dio.delete('/pipelines/$id');
  }

  Future<Job> runPipeline(String id) async {
    final r = await _dio.post('/pipelines/$id/run');
    return Job.fromJson(r.data as Map<String, dynamic>);
  }

  // Jobs
  Future<List<Job>> jobs({
    String? pipelineId,
    String? status,
    int limit = 100,
  }) async {
    final r = await _dio.get('/jobs', queryParameters: {
      if (pipelineId != null) 'pipeline_id': pipelineId,
      if (status != null) 'status': status,
      'limit': limit,
    });
    return (r.data as List)
        .map((e) => Job.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Job> job(String id) async {
    final r = await _dio.get('/jobs/$id');
    return Job.fromJson(r.data as Map<String, dynamic>);
  }

  Stream<Job> streamJob(String id) =>
      _sseJson(path: '/jobs/$id/stream').map(Job.fromJson);

  Stream<Job> streamAllJobs() =>
      _sseJson(path: '/jobs/stream').map(Job.fromJson);

  /// Live feed of DAG run state changes (`planned`, `step_started`,
  /// `step_succeeded`, `step_failed`, `completed`). Payload is the raw
  /// JSON from the backend so callers can pull `event`, `current_assets`,
  /// `job_id`, etc. without a typed wrapper.
  Stream<Map<String, dynamic>> streamAllDagRuns() =>
      _sseJson(path: '/dag-runs/stream');

  Stream<Map<String, dynamic>> streamDagRun(String id) =>
      _sseJson(path: '/dag-runs/$id/stream');

  /// Opens an SSE stream, decodes each ``data: {...}`` frame into a
  /// JSON map, and emits maps on a broadcast stream. Heartbeats (``:``
  /// comment lines) are ignored. The stream closes when the underlying
  /// response stream ends or the subscription is cancelled.
  Stream<Map<String, dynamic>> _sseJson({required String path}) {
    final controller = StreamController<Map<String, dynamic>>.broadcast();
    final cancelToken = CancelToken();
    StreamSubscription<List<int>>? sub;

    controller.onListen = () async {
      try {
        final r = await _dio.get<ResponseBody>(
          path,
          options: Options(
            responseType: ResponseType.stream,
            headers: const {'Accept': 'text/event-stream'},
          ),
          cancelToken: cancelToken,
        );
        final body = r.data;
        if (body == null) {
          await controller.close();
          return;
        }
        var buffer = '';
        sub = body.stream.listen(
          (bytes) {
            buffer += utf8.decode(bytes, allowMalformed: true);
            while (true) {
              final ix = buffer.indexOf('\n\n');
              if (ix < 0) break;
              final raw = buffer.substring(0, ix);
              buffer = buffer.substring(ix + 2);
              final event = _parseSse(raw);
              if (event == null) continue;
              try {
                final decoded = json.decode(event) as Map<String, dynamic>;
                controller.add(decoded);
              } catch (e, s) {
                controller.addError(e, s);
              }
            }
          },
          onError: controller.addError,
          onDone: () => controller.close(),
          cancelOnError: false,
        );
      } catch (e, s) {
        controller.addError(e, s);
        await controller.close();
      }
    };

    controller.onCancel = () async {
      await sub?.cancel();
      if (!cancelToken.isCancelled) cancelToken.cancel('listener cancelled');
    };

    return controller.stream;
  }

  String? _parseSse(String raw) {
    // SSE frames are line-based: ``event: foo`` and ``data: bar`` pairs.
    // ``:`` lines are comments (heartbeats) and ignored.
    final lines = raw.split('\n');
    final data = StringBuffer();
    for (final line in lines) {
      if (line.isEmpty || line.startsWith(':')) continue;
      if (line.startsWith('data:')) {
        if (data.isNotEmpty) data.write('\n');
        data.write(line.substring(5).trimLeft());
      }
    }
    return data.isEmpty ? null : data.toString();
  }

  // Assets
  Future<List<AssetWithStatus>> assets() async {
    final r = await _dio.get('/assets');
    return (r.data as List)
        .map((e) => AssetWithStatus.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<AssetGraph> assetGraph() async {
    final r = await _dio.get('/assets/graph');
    return AssetGraph.fromJson(r.data as Map<String, dynamic>);
  }

  Future<AssetWithStatus> asset(String key) async {
    final r = await _dio.get('/assets/$key');
    return AssetWithStatus.fromJson(r.data as Map<String, dynamic>);
  }

  Future<List<AssetMaterializationRecord>> assetMaterializations(String key) async {
    final r = await _dio.get('/assets/$key/materializations');
    return (r.data as List)
        .map((e) =>
            AssetMaterializationRecord.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<Map<String, dynamic>> materializeAssets(
    List<String> keys, {
    bool includeUpstream = true,
  }) async {
    final r = await _dio.post(
      '/assets/materialize',
      data: {'keys': keys, 'include_upstream': includeUpstream},
    );
    return Map<String, dynamic>.from(r.data as Map);
  }

  // DAG runs
  Future<List<Map<String, dynamic>>> dagRuns({int limit = 50}) async {
    final r = await _dio.get('/dag-runs', queryParameters: {'limit': limit});
    return (r.data as List)
        .map<Map<String, dynamic>>((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<Map<String, dynamic>> dagRun(String id) async {
    final r = await _dio.get('/dag-runs/$id');
    return Map<String, dynamic>.from(r.data as Map);
  }

  // Definitions
  Future<DefinitionsReport> reloadDefinitions() async {
    final r = await _dio.post('/definitions/reload');
    return DefinitionsReport.fromJson(r.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> definitionsStatus() async {
    final r = await _dio.get('/definitions/status');
    return Map<String, dynamic>.from(r.data as Map);
  }

  Future<Stats> stats() async {
    final r = await _dio.get('/jobs/stats');
    return Stats.fromJson(r.data as Map<String, dynamic>);
  }
}
