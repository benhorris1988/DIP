import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';
import '../util/format.dart';
import '../widgets/ui/empty_state.dart';
import '../widgets/ui/status_pill.dart';

class ErrorExplorerPage extends ConsumerStatefulWidget {
  const ErrorExplorerPage({super.key});
  @override
  ConsumerState<ErrorExplorerPage> createState() => _ErrorExplorerPageState();
}

class _ErrorExplorerPageState extends ConsumerState<ErrorExplorerPage> {
  String _search = '';
  String? _pipelineId;

  @override
  Widget build(BuildContext context) {
    final failed =
        ref.watch(jobsProvider(const JobsQuery(status: 'failed', limit: 500)));
    final pipelines = ref.watch(pipelinesProvider);

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Error explorer', style: context.th.textTheme.titleLarge),
          Text(
            'Failed batches grouped by error class with full-text search.',
            style: context.th.textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: const InputDecoration(
                    hintText: 'Search error message, pipeline, batch id…',
                    prefixIcon: Icon(Icons.search, size: 16),
                  ),
                  onChanged: (v) => setState(() => _search = v),
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: 220,
                child: DropdownButtonFormField<String?>(
                  value: _pipelineId,
                  decoration:
                      const InputDecoration(labelText: 'PIPELINE FILTER'),
                  items: [
                    const DropdownMenuItem(
                        value: null, child: Text('All pipelines')),
                    for (final p in (pipelines.value ?? const <Pipeline>[]))
                      DropdownMenuItem(value: p.id, child: Text(p.name)),
                  ],
                  onChanged: (v) => setState(() => _pipelineId = v),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: failed.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('$e')),
              data: (all) {
                final rows = all.where((j) {
                  if (_pipelineId != null && j.pipelineId != _pipelineId) {
                    return false;
                  }
                  if (_search.isNotEmpty) {
                    final s = _search.toLowerCase();
                    final hit = (j.error ?? '').toLowerCase().contains(s) ||
                        j.pipelineName.toLowerCase().contains(s) ||
                        j.id.toLowerCase().contains(s);
                    if (!hit) return false;
                  }
                  return true;
                }).toList();
                if (rows.isEmpty) {
                  return const EmptyState(
                    icon: Icons.report_outlined,
                    title: 'No errors found',
                    description: 'No failed batches match the current filters.',
                  );
                }
                final groups = <String, List<Job>>{};
                for (final j in rows) {
                  final key = (j.error ?? 'Unknown error').split(':').first;
                  groups.putIfAbsent(key, () => []).add(j);
                }
                final entries = groups.entries.toList()
                  ..sort((a, b) => b.value.length.compareTo(a.value.length));
                return ListView.separated(
                  itemCount: entries.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (_, i) => _Group(
                    title: entries[i].key,
                    jobs: entries[i].value,
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _Group extends StatelessWidget {
  const _Group({required this.title, required this.jobs});
  final String title;
  final List<Job> jobs;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: context.border)),
            ),
            child: Row(
              children: [
                const Icon(Icons.report,
                    size: 14, color: BifrostColors.rose),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                        fontFamily: 'JetBrainsMono', fontSize: 12),
                  ),
                ),
                StatusPill(status: 'failed'),
                const SizedBox(width: 8),
                Text('${jobs.length}', style: context.th.textTheme.titleSmall),
              ],
            ),
          ),
          for (final j in jobs)
            InkWell(
              onTap: () => context.go('/jobs/${j.id}'),
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                child: Row(
                  children: [
                    SizedBox(
                      width: 90,
                      child: Text(shortId(j.id),
                          style: const TextStyle(
                              fontFamily: 'JetBrainsMono', fontSize: 11)),
                    ),
                    SizedBox(
                      width: 160,
                      child: Text(j.pipelineName,
                          style: const TextStyle(
                              fontFamily: 'JetBrainsMono', fontSize: 12)),
                    ),
                    const SizedBox(width: 8),
                    Text(formatDuration(j.durationMs),
                        style: context.th.textTheme.bodySmall),
                    const SizedBox(width: 8),
                    Text(formatDate(j.startedAt),
                        style: context.th.textTheme.bodySmall),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        j.error ?? '',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 11, color: Color(0xFFBE123C)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
