import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';
import '../util/format.dart';
import '../widgets/dag_runs_live.dart';
import '../widgets/ui/bifrost_button.dart';
import '../widgets/ui/empty_state.dart';
import '../widgets/ui/status_pill.dart';

class AssetsPage extends ConsumerWidget {
  const AssetsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final graphAsync = ref.watch(assetGraphProvider);

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
                    Text('Assets', style: context.th.textTheme.titleLarge),
                    Text(
                      'Data products produced by pipelines. Layered by '
                      'dependency depth — upstream on the left.',
                      style: context.th.textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              OutlinedButton.icon(
                onPressed: () async {
                  try {
                    final r = await ref
                        .read(apiClientProvider)
                        .reloadDefinitions();
                    invalidateAll(ref);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            'Reloaded · ${r.pipelinesTotal} pipelines · '
                            '${r.assetsTotal} assets · ${r.errors} errors',
                          ),
                        ),
                      );
                    }
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context)
                          .showSnackBar(SnackBar(content: Text('Reload failed: $e')));
                    }
                  }
                },
                icon: const Icon(Icons.refresh, size: 13),
                label: const Text('Reload definitions'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const DagRunsLive(),
          Expanded(
            child: graphAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('$e')),
              data: (g) {
                if (g.nodes.isEmpty) {
                  return const EmptyState(
                    icon: Icons.hub_outlined,
                    title: 'No assets yet',
                    description:
                        'Drop a YAML file under backend/definitions/ and hit '
                        '"Reload definitions".',
                  );
                }
                final byKey = {for (final n in g.nodes) n.key: n};
                return SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (var i = 0; i < g.layers.length; i++) ...[
                        _Layer(
                          index: i,
                          keys: g.layers[i],
                          byKey: byKey,
                        ),
                        if (i < g.layers.length - 1)
                          Padding(
                            padding:
                                const EdgeInsets.symmetric(horizontal: 4),
                            child: Icon(
                              Icons.arrow_forward,
                              size: 18,
                              color: context.muted,
                            ),
                          ),
                      ],
                    ],
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

class _Layer extends StatelessWidget {
  const _Layer({
    required this.index,
    required this.keys,
    required this.byKey,
  });
  final int index;
  final List<String> keys;
  final Map<String, AssetWithStatus> byKey;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 280,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 8),
            child: Text(
              'LAYER ${index + 1}'.toUpperCase(),
              style: context.th.textTheme.labelSmall,
            ),
          ),
          for (final k in keys) ...[
            _AssetCard(
              keyId: k,
              asset: byKey[k.startsWith('? ') ? k.substring(2) : k],
              isCycle: k.startsWith('? '),
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _AssetCard extends ConsumerWidget {
  const _AssetCard({
    required this.keyId,
    required this.asset,
    required this.isCycle,
  });
  final String keyId;
  final AssetWithStatus? asset;
  final bool isCycle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (asset == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Text(keyId, style: context.th.textTheme.titleSmall),
        ),
      );
    }
    final a = asset!;
    return Card(
      child: InkWell(
        onTap: () => context.go('/assets/${a.key}'),
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      a.key,
                      style: const TextStyle(
                        fontFamily: 'JetBrainsMono',
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (a.hasFreshnessPolicy) ...[
                    Tooltip(
                      message: 'Auto-materialises if older than '
                          '${a.freshnessLabel}',
                      child: Container(
                        margin: const EdgeInsets.only(right: 4),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: context.isDark
                              ? const Color(0xFF1E2530)
                              : const Color(0xFFEFF6FF),
                          borderRadius: BorderRadius.circular(3),
                          border: Border.all(
                              color: BifrostColors.purple.withOpacity(0.4)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.schedule,
                                size: 9, color: BifrostColors.purple),
                            const SizedBox(width: 3),
                            Text(
                              'auto · ${a.freshnessLabel}',
                              style: const TextStyle(
                                fontFamily: 'JetBrainsMono',
                                fontSize: 9,
                                color: BifrostColors.purple,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  if (isCycle)
                    const Icon(Icons.error_outline,
                        size: 14, color: BifrostColors.rose)
                  else
                    StatusPill(status: a.lastStatus ?? 'untested'),
                ],
              ),
              if (a.description != null && a.description!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  a.description!,
                  style: context.th.textTheme.bodySmall,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(Icons.update, size: 11, color: context.muted),
                  const SizedBox(width: 4),
                  Text(
                    formatDate(a.lastMaterializedAt),
                    style: context.th.textTheme.bodySmall,
                  ),
                  const Spacer(),
                  if (a.rowsWritten != null)
                    Text(
                      '${formatNumber(a.rowsWritten!)} rows',
                      style: context.th.textTheme.bodySmall?.copyWith(
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                ],
              ),
              if (a.dependsOn.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: [
                    for (final dep in a.dependsOn)
                      InkWell(
                        onTap: () => context.go('/assets/$dep'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: context.isDark
                                ? const Color(0xFF27272A)
                                : const Color(0xFFF4F4F5),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            dep,
                            style: const TextStyle(
                              fontFamily: 'JetBrainsMono',
                              fontSize: 10,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  if (a.pipelineName != null)
                    Expanded(
                      child: InkWell(
                        onTap: () =>
                            context.go('/pipelines/${a.pipelineId}'),
                        child: Text(
                          a.pipelineName!,
                          style: const TextStyle(
                            fontFamily: 'JetBrainsMono',
                            fontSize: 10,
                            color: BifrostColors.purple,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                  else
                    const Spacer(),
                  _MaterializeButton(assetKey: a.key),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MaterializeButton extends ConsumerStatefulWidget {
  const _MaterializeButton({required this.assetKey});
  final String assetKey;

  @override
  ConsumerState<_MaterializeButton> createState() => _MaterializeButtonState();
}

class _MaterializeButtonState extends ConsumerState<_MaterializeButton> {
  bool _running = false;

  @override
  Widget build(BuildContext context) {
    return BifrostButton(
      onPressed: _running
          ? null
          : () async {
              setState(() => _running = true);
              try {
                await ref
                    .read(apiClientProvider)
                    .materializeAssets([widget.assetKey]);
                invalidateAll(ref);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Materialized ${widget.assetKey}'),
                    ),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed: $e')),
                  );
                }
              } finally {
                if (mounted) setState(() => _running = false);
              }
            },
      label: 'Run',
      icon: Icons.play_arrow,
    );
  }
}
