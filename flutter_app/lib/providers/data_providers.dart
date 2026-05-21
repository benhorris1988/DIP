import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/models.dart';

final apiClientProvider = Provider<ApiClient>((_) => ApiClient());

final connectorsProvider = FutureProvider<List<ConnectorMetadata>>((ref) async {
  return ref.read(apiClientProvider).connectors();
});

final connectionsProvider = FutureProvider<List<Connection>>((ref) async {
  return ref.read(apiClientProvider).connections();
});

final connectionProvider =
    FutureProvider.family<Connection, String>((ref, id) async {
  return ref.read(apiClientProvider).connection(id);
});

final pipelinesProvider = FutureProvider<List<Pipeline>>((ref) async {
  return ref.read(apiClientProvider).pipelines();
});

final pipelineProvider =
    FutureProvider.family<Pipeline, String>((ref, id) async {
  return ref.read(apiClientProvider).pipeline(id);
});

class JobsQuery {
  final String? pipelineId;
  final String? status;
  final int limit;
  const JobsQuery({this.pipelineId, this.status, this.limit = 100});

  @override
  bool operator ==(Object other) =>
      other is JobsQuery &&
      other.pipelineId == pipelineId &&
      other.status == status &&
      other.limit == limit;

  @override
  int get hashCode => Object.hash(pipelineId, status, limit);
}

final jobsProvider =
    FutureProvider.family<List<Job>, JobsQuery>((ref, q) async {
  return ref.read(apiClientProvider).jobs(
        pipelineId: q.pipelineId,
        status: q.status,
        limit: q.limit,
      );
});

final jobProvider = FutureProvider.family<Job, String>((ref, id) async {
  return ref.read(apiClientProvider).job(id);
});

/// Live job feed from the backend SSE endpoint.
///
/// Resolves the initial snapshot via REST so the UI never shows an empty
/// shell, then merges every SSE update on top. The stream stays open until
/// the consumer disposes — Riverpod cancels the subscription for us.
final jobStreamProvider =
    StreamProvider.family<Job, String>((ref, id) async* {
  final api = ref.read(apiClientProvider);
  yield await api.job(id);
  await for (final j in api.streamJob(id)) {
    yield j;
  }
});

final statsProvider = FutureProvider<Stats>((ref) async {
  return ref.read(apiClientProvider).stats();
});

final assetsProvider = FutureProvider<List<AssetWithStatus>>((ref) async {
  return ref.read(apiClientProvider).assets();
});

final assetGraphProvider = FutureProvider<AssetGraph>((ref) async {
  return ref.read(apiClientProvider).assetGraph();
});

final assetProvider =
    FutureProvider.family<AssetWithStatus, String>((ref, key) async {
  return ref.read(apiClientProvider).asset(key);
});

final assetMaterializationsProvider = FutureProvider.family<
    List<AssetMaterializationRecord>, String>((ref, key) async {
  return ref.read(apiClientProvider).assetMaterializations(key);
});

final healthProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.read(apiClientProvider).health();
});

/// Convenience: invalidate the data providers a write would affect.
void invalidateAll(WidgetRef ref) {
  ref.invalidate(connectionsProvider);
  ref.invalidate(pipelinesProvider);
  ref.invalidate(jobsProvider);
  ref.invalidate(statsProvider);
  ref.invalidate(assetsProvider);
  ref.invalidate(assetGraphProvider);
}
