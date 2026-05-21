import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../util/format.dart';
import '../widgets/ui/empty_state.dart';
import '../widgets/ui/status_pill.dart';

class JobsPage extends ConsumerStatefulWidget {
  const JobsPage({super.key});
  @override
  ConsumerState<JobsPage> createState() => _JobsPageState();
}

class _JobsPageState extends ConsumerState<JobsPage> {
  String _status = 'all';

  @override
  Widget build(BuildContext context) {
    final query = JobsQuery(status: _status == 'all' ? null : _status);
    final jobs = ref.watch(jobsProvider(query));
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Batches', style: context.th.textTheme.titleLarge),
                    Text('Recent executions across all pipelines.',
                        style: context.th.textTheme.bodySmall),
                  ],
                ),
              ),
              OutlinedButton.icon(
                onPressed: () => ref.invalidate(jobsProvider),
                icon: const Icon(Icons.refresh, size: 13),
                label: const Text('Refresh'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 6,
            children:
                const ['all', 'running', 'succeeded', 'failed'].map((s) {
              final on = s == _status;
              return ChoiceChip(
                label: Text(s),
                selected: on,
                onSelected: (_) => setState(() => _status = s),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: jobs.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('$e')),
              data: (list) {
                if (list.isEmpty) {
                  return const EmptyState(
                    icon: Icons.bolt_outlined,
                    title: 'No batches yet',
                    description:
                        'Trigger a pipeline to see batch runs appear here.',
                  );
                }
                return Card(
                  child: ListView.separated(
                    itemCount: list.length,
                    separatorBuilder: (_, __) => Divider(
                        height: 1, color: context.border, thickness: 1),
                    itemBuilder: (_, i) {
                      final j = list[i];
                      return InkWell(
                        onTap: () => context.go('/jobs/${j.id}'),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 10),
                          child: Row(
                            children: [
                              SizedBox(
                                width: 90,
                                child: Text(shortId(j.id),
                                    style: const TextStyle(
                                        fontFamily: 'JetBrainsMono',
                                        fontSize: 11)),
                              ),
                              Expanded(
                                child: Text(j.pipelineName,
                                    style: const TextStyle(
                                        fontFamily: 'JetBrainsMono',
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500)),
                              ),
                              StatusPill(status: j.status),
                              const SizedBox(width: 12),
                              SizedBox(
                                width: 110,
                                child: Text(
                                  '${formatNumber(j.rowsRead)} → ${formatNumber(j.rowsWritten)}',
                                  textAlign: TextAlign.right,
                                  style:
                                      context.th.textTheme.bodySmall?.copyWith(
                                    fontFeatures: const [
                                      FontFeature.tabularFigures()
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              SizedBox(
                                width: 64,
                                child: Text(formatDuration(j.durationMs),
                                    textAlign: TextAlign.right,
                                    style: context.th.textTheme.bodySmall),
                              ),
                              const SizedBox(width: 12),
                              SizedBox(
                                width: 110,
                                child: Text(formatDate(j.startedAt),
                                    textAlign: TextAlign.right,
                                    style: context.th.textTheme.bodySmall),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
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
