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

  Future<Stats> stats() async {
    final r = await _dio.get('/jobs/stats');
    return Stats.fromJson(r.data as Map<String, dynamic>);
  }
}
