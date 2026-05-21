import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';
import '../util/format.dart';
import '../widgets/ui/bifrost_button.dart';
import '../widgets/ui/status_pill.dart';

class AssetDetailPage extends ConsumerWidget {
  const AssetDetailPage({super.key, required this.assetKey});
  final String assetKey;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asset = ref.watch(assetProvider(assetKey));
    final mats = ref.watch(assetMaterializationsProvider(assetKey));

    return asset.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
      data: (a) => Padding(
        padding: const EdgeInsets.all(20),
        child: ListView(
          children: [
            TextButton.icon(
              onPressed: () => context.go('/assets'),
              icon: const Icon(Icons.arrow_back, size: 14),
              label: const Text('Back'),
            ),
            const SizedBox(height: 8),
            Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 10,
              runSpacing: 6,
              children: [
                Text(
                  a.key,
                  style: context.th.textTheme.titleLarge?.copyWith(
                      fontFamily: 'JetBrainsMono'),
                ),
                StatusPill(status: a.lastStatus ?? 'untested'),
              ],
            ),
            if (a.description != null && a.description!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(a.description!, style: context.th.textTheme.bodySmall),
            ],
            const SizedBox(height: 10),
            Wrap(
              spacing: 16,
              runSpacing: 4,
              children: [
                if (a.pipelineName != null)
                  _meta(context, 'PIPELINE', a.pipelineName!,
                      onTap: () => context.go('/pipelines/${a.pipelineId}')),
                if (a.objectName != null)
                  _meta(context, 'OBJECT', a.objectName!),
                _meta(
                  context,
                  'LAST MATERIALIZED',
                  formatDate(a.lastMaterializedAt),
                ),
                if (a.rowsWritten != null)
                  _meta(
                    context,
                    'ROWS',
                    formatNumber(a.rowsWritten!),
                  ),
                if (a.definitionPath != null)
                  _meta(context, 'SOURCE',
                      a.definitionPath!.split('/').last),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                BifrostButton(
                  onPressed: () async {
                    try {
                      await ref
                          .read(apiClientProvider)
                          .materializeAssets([a.key]);
                      invalidateAll(ref);
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Materialization started')),
                        );
                      }
                    } catch (e) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Failed: $e')),
                        );
                      }
                    }
                  },
                  label: 'Materialize (with upstream)',
                  icon: Icons.play_arrow,
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: () async {
                    try {
                      await ref
                          .read(apiClientProvider)
                          .materializeAssets([a.key], includeUpstream: false);
                      invalidateAll(ref);
                    } catch (e) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Failed: $e')),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.refresh, size: 13),
                  label: const Text('Just this asset'),
                ),
              ],
            ),
            const SizedBox(height: 18),
            if (a.dependsOn.isNotEmpty) ...[
              Text('Depends on', style: context.th.textTheme.titleSmall),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final dep in a.dependsOn)
                    InkWell(
                      onTap: () => context.go('/assets/$dep'),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: context.isDark
                              ? const Color(0xFF27272A)
                              : const Color(0xFFF4F4F5),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          dep,
                          style: const TextStyle(
                            fontFamily: 'JetBrainsMono',
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 18),
            ],
            if (a.metadata.isNotEmpty) ...[
              Text('Metadata', style: context.th.textTheme.titleSmall),
              const SizedBox(height: 6),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final e in a.metadata.entries)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Row(
                            children: [
                              SizedBox(
                                width: 120,
                                child: Text(
                                  e.key.toUpperCase(),
                                  style: context.th.textTheme.labelSmall,
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  '${e.value}',
                                  style: const TextStyle(
                                      fontFamily: 'JetBrainsMono',
                                      fontSize: 12),
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 18),
            ],
            Text('Materialization history',
                style: context.th.textTheme.titleSmall),
            const SizedBox(height: 6),
            mats.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(20),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (e, _) => Text('$e'),
              data: (rows) {
                if (rows.isEmpty) {
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Center(
                        child: Text(
                          'No materializations yet — run the asset to start the history.',
                          style: context.th.textTheme.bodySmall,
                        ),
                      ),
                    ),
                  );
                }
                return Card(
                  child: Column(
                    children: [
                      for (var i = 0; i < rows.length; i++) ...[
                        if (i > 0)
                          Divider(
                              height: 1,
                              color: context.border,
                              thickness: 1),
                        InkWell(
                          onTap: () =>
                              context.go('/jobs/${rows[i].jobId}'),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                            child: Row(
                              children: [
                                const Icon(Icons.check_circle,
                                    size: 14, color: BifrostColors.emerald),
                                const SizedBox(width: 8),
                                Text(
                                  formatDate(rows[i].ts),
                                  style: context.th.textTheme.bodySmall,
                                ),
                                const SizedBox(width: 12),
                                Text(
                                  shortId(rows[i].jobId),
                                  style: const TextStyle(
                                      fontFamily: 'JetBrainsMono',
                                      fontSize: 11),
                                ),
                                const Spacer(),
                                Text(
                                  '${formatNumber(rows[i].rowsWritten)} rows',
                                  style: context.th.textTheme.bodySmall
                                      ?.copyWith(
                                    fontFeatures: const [
                                      FontFeature.tabularFigures()
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _meta(BuildContext context, String label, String value,
      {VoidCallback? onTap}) {
    final w = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: context.th.textTheme.labelSmall),
        Text(
          value,
          style: TextStyle(
            fontFamily: 'JetBrainsMono',
            fontSize: 12,
            color: onTap != null
                ? BifrostColors.purple
                : context.cs.onSurface,
          ),
        ),
      ],
    );
    return onTap == null ? w : InkWell(onTap: onTap, child: w);
  }
}
