import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';
import '../util/format.dart';
import '../widgets/ui/bifrost_button.dart';
import '../widgets/ui/connector_icon.dart';
import '../widgets/ui/empty_state.dart';
import '../widgets/ui/sparkline.dart';
import '../widgets/ui/status_pill.dart';

class PipelinesPage extends ConsumerWidget {
  const PipelinesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pipelines = ref.watch(pipelinesProvider);
    final connections = ref.watch(connectionsProvider);
    final jobs = ref.watch(jobsProvider(const JobsQuery(limit: 200)));

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
                    Text('Pipelines', style: context.th.textTheme.titleLarge),
                    Text(
                      'Move data from source to destination on demand or on a schedule.',
                      style: context.th.textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              BifrostButton(
                onPressed: () => context.go('/pipelines/new'),
                label: 'New pipeline',
                icon: Icons.add,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: pipelines.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => _errorBox(context, e),
              data: (list) {
                if (list.isEmpty) {
                  return EmptyState(
                    icon: Icons.account_tree_outlined,
                    title: 'No pipelines yet',
                    description:
                        'Connect a source to a destination to build your first pipeline.',
                    action: BifrostButton(
                      onPressed: () => context.go('/pipelines/new'),
                      label: 'New pipeline',
                      icon: Icons.add,
                    ),
                  );
                }
                final connMap = {
                  for (final c in (connections.value ?? const <Connection>[]))
                    c.id: c
                };
                final byPipe = <String, List<Job>>{};
                for (final j in jobs.value ?? const <Job>[]) {
                  byPipe.putIfAbsent(j.pipelineId, () => []).add(j);
                }
                return Card(
                  child: ListView.separated(
                    itemCount: list.length,
                    separatorBuilder: (_, __) => Divider(
                        height: 1, color: context.border, thickness: 1),
                    itemBuilder: (_, i) {
                      final p = list[i];
                      final src = connMap[p.sourceConnectionId];
                      final dst = connMap[p.destinationConnectionId];
                      final pj = byPipe[p.id] ?? const <Job>[];
                      final trend = pj
                          .take(12)
                          .toList()
                          .reversed
                          .map((j) => j.rowsWritten)
                          .toList();
                      final last = pj.firstOrNull;
                      return _PipelineRow(
                        pipeline: p,
                        src: src,
                        dst: dst,
                        trend: trend,
                        lastJob: last,
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

  Widget _errorBox(BuildContext context, Object e) => Center(
        child: Text('$e', style: context.th.textTheme.bodySmall),
      );
}

class _PipelineRow extends ConsumerWidget {
  const _PipelineRow({
    required this.pipeline,
    required this.src,
    required this.dst,
    required this.trend,
    required this.lastJob,
  });
  final Pipeline pipeline;
  final Connection? src;
  final Connection? dst;
  final List<num> trend;
  final Job? lastJob;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return InkWell(
      onTap: () => context.go('/pipelines/${pipeline.id}'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: LayoutBuilder(
          builder: (context, c) {
            final compact = c.maxWidth < 700;
            final left = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(pipeline.name,
                    style: context.th.textTheme.titleSmall?.copyWith(
                      fontFamily: 'JetBrainsMono',
                    )),
                if (pipeline.description != null &&
                    pipeline.description!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      pipeline.description!,
                      style: context.th.textTheme.bodySmall,
                    ),
                  ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (src != null)
                      ConnectorIcon(
                          icon: src!.connectorType, size: 22),
                    const SizedBox(width: 6),
                    Text(pipeline.sourceObject,
                        style: const TextStyle(
                            fontFamily: 'JetBrainsMono', fontSize: 11)),
                    const SizedBox(width: 6),
                    Icon(Icons.arrow_forward,
                        size: 12, color: context.muted),
                    const SizedBox(width: 6),
                    if (dst != null)
                      ConnectorIcon(
                          icon: dst!.connectorType, size: 22),
                    const SizedBox(width: 6),
                    Text(pipeline.destinationObject,
                        style: const TextStyle(
                            fontFamily: 'JetBrainsMono', fontSize: 11)),
                  ],
                ),
              ],
            );
            final right = Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    StatusPill(
                      status: lastJob?.status ??
                          (pipeline.enabled ? 'healthy' : 'paused'),
                    ),
                    const SizedBox(width: 8),
                    Text(pipeline.mode.toUpperCase(),
                        style: context.th.textTheme.labelSmall),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (trend.isNotEmpty)
                      Sparkline(data: trend, color: BifrostColors.purple),
                    const SizedBox(width: 10),
                    Text(
                      lastJob == null
                          ? '—'
                          : formatDate(lastJob!.startedAt),
                      style: context.th.textTheme.bodySmall,
                    ),
                    const SizedBox(width: 10),
                    _RunButton(pipeline: pipeline),
                  ],
                ),
              ],
            );
            if (compact) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [left, const SizedBox(height: 10), right],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: left),
                right,
              ],
            );
          },
        ),
      ),
    );
  }
}

class _RunButton extends ConsumerStatefulWidget {
  const _RunButton({required this.pipeline});
  final Pipeline pipeline;

  @override
  ConsumerState<_RunButton> createState() => _RunButtonState();
}

class _RunButtonState extends ConsumerState<_RunButton> {
  bool _running = false;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: !widget.pipeline.enabled || _running
          ? null
          : () async {
              setState(() => _running = true);
              try {
                await ref.read(apiClientProvider).runPipeline(widget.pipeline.id);
                if (mounted) invalidateAll(ref);
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Run failed: $e')),
                  );
                }
              } finally {
                if (mounted) setState(() => _running = false);
              }
            },
      icon: const Icon(Icons.play_arrow, size: 13),
      label: const Text('Run'),
    );
  }
}
