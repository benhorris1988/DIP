import 'package:fl_chart/fl_chart.dart';
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
import '../widgets/ui/status_pill.dart';

class PipelineDetailPage extends ConsumerStatefulWidget {
  const PipelineDetailPage({super.key, required this.id});
  final String id;

  @override
  ConsumerState<PipelineDetailPage> createState() => _PipelineDetailPageState();
}

class _PipelineDetailPageState extends ConsumerState<PipelineDetailPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tab = TabController(length: 4, vsync: this);

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pAsync = ref.watch(pipelineProvider(widget.id));
    final connections = ref.watch(connectionsProvider);
    final jobs =
        ref.watch(jobsProvider(JobsQuery(pipelineId: widget.id, limit: 100)));

    return pAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
      data: (p) {
        final connMap = {
          for (final c in (connections.value ?? const <Connection>[]))
            c.id: c
        };
        final jobList = jobs.value ?? const <Job>[];
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextButton.icon(
                onPressed: () => context.go('/pipelines'),
                icon: const Icon(Icons.arrow_back, size: 14),
                label: const Text('Back'),
              ),
              const SizedBox(height: 8),
              _Header(
                p: p,
                src: connMap[p.sourceConnectionId],
                dst: connMap[p.destinationConnectionId],
                lastStatus:
                    jobList.firstOrNull?.status ?? (p.enabled ? 'healthy' : 'paused'),
              ),
              const SizedBox(height: 16),
              TabBar(
                controller: _tab,
                isScrollable: true,
                tabAlignment: TabAlignment.start,
                labelStyle: const TextStyle(
                    fontSize: 12, fontWeight: FontWeight.w600),
                unselectedLabelStyle: const TextStyle(fontSize: 12),
                indicatorColor: BifrostColors.purple,
                indicatorSize: TabBarIndicatorSize.label,
                dividerColor: context.border,
                tabs: const [
                  Tab(text: 'Overview'),
                  Tab(text: 'Recent batches'),
                  Tab(text: 'Mappings & config'),
                  Tab(text: 'Run history'),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: TabBarView(
                  controller: _tab,
                  children: [
                    _OverviewTab(jobs: jobList),
                    _BatchesTab(jobs: jobList),
                    _ConfigTab(pipeline: p),
                    _HistoryTab(jobs: jobList),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _Header extends ConsumerWidget {
  const _Header({
    required this.p,
    required this.src,
    required this.dst,
    required this.lastStatus,
  });
  final Pipeline p;
  final Connection? src;
  final Connection? dst;
  final String lastStatus;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.start,
      runSpacing: 12,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    p.name,
                    style: context.th.textTheme.titleLarge?.copyWith(
                      fontFamily: 'JetBrainsMono',
                    ),
                  ),
                  const SizedBox(width: 10),
                  StatusPill(status: lastStatus),
                  const SizedBox(width: 6),
                  StatusPill(status: p.mode),
                ],
              ),
              if (p.description != null && p.description!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(p.description!, style: context.th.textTheme.bodySmall),
              ],
              const SizedBox(height: 6),
              Wrap(
                spacing: 12,
                runSpacing: 4,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  if (src != null)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      ConnectorIcon(icon: src!.connectorType, size: 18),
                      const SizedBox(width: 6),
                      Text('${src!.name}:${p.sourceObject}',
                          style: const TextStyle(
                              fontFamily: 'JetBrainsMono', fontSize: 11)),
                    ]),
                  Icon(Icons.arrow_forward, size: 12, color: context.muted),
                  if (dst != null)
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      ConnectorIcon(icon: dst!.connectorType, size: 18),
                      const SizedBox(width: 6),
                      Text('${dst!.name}:${p.destinationObject}',
                          style: const TextStyle(
                              fontFamily: 'JetBrainsMono', fontSize: 11)),
                    ]),
                  Text('•', style: context.th.textTheme.bodySmall),
                  Text(p.schedule ?? 'manual',
                      style: const TextStyle(
                          fontFamily: 'JetBrainsMono', fontSize: 11)),
                ],
              ),
            ],
          ),
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            OutlinedButton.icon(
              onPressed: () async {
                final api = ref.read(apiClientProvider);
                try {
                  await api.updatePipeline(p.id, {'enabled': !p.enabled});
                  ref.invalidate(pipelineProvider(p.id));
                  ref.invalidate(pipelinesProvider);
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context)
                        .showSnackBar(SnackBar(content: Text('$e')));
                  }
                }
              },
              icon: const Icon(Icons.power_settings_new, size: 13),
              label: Text(p.enabled ? 'Pause' : 'Resume'),
            ),
            const SizedBox(width: 6),
            BifrostButton(
              onPressed: p.enabled
                  ? () async {
                      try {
                        await ref.read(apiClientProvider).runPipeline(p.id);
                        invalidateAll(ref);
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context)
                              .showSnackBar(SnackBar(content: Text('$e')));
                        }
                      }
                    }
                  : null,
              label: 'Trigger run',
              icon: Icons.play_arrow,
            ),
            const SizedBox(width: 6),
            OutlinedButton.icon(
              onPressed: () => context.go('/pipelines/${p.id}/edit'),
              icon: const Icon(Icons.edit, size: 13),
              label: const Text('Edit'),
            ),
          ],
        ),
      ],
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.jobs});
  final List<Job> jobs;

  @override
  Widget build(BuildContext context) {
    final succ = jobs.where((j) => j.status == 'succeeded').length;
    final fail = jobs.where((j) => j.status == 'failed').length;
    final total = succ + fail;
    final rate = total == 0 ? 0 : (fail / total * 100).round();
    final rowsTotal = jobs.fold<int>(0, (s, j) => s + j.rowsWritten);
    final avgMs = jobs.isEmpty
        ? 0
        : (jobs.fold<int>(0, (s, j) => s + j.durationMs) / jobs.length).round();
    final recent = jobs.take(14).toList().reversed.toList();

    return ListView(
      children: [
        GridView.count(
          crossAxisCount:
              MediaQuery.sizeOf(context).width >= 900 ? 6 : 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 2.0,
          children: [
            _Metric(label: 'Total batches', value: '${jobs.length}'),
            _Metric(label: 'Rows written', value: formatNumber(rowsTotal)),
            _Metric(
              label: 'Error rate',
              value: '$rate%',
              accent: rate > 10
                  ? BifrostColors.rose
                  : rate > 0
                      ? const Color(0xFFB45309)
                      : BifrostColors.emerald,
            ),
            _Metric(label: 'Avg duration', value: formatDuration(avgMs)),
            _Metric(
                label: 'Succeeded',
                value: '$succ',
                accent: BifrostColors.emerald),
            _Metric(
                label: 'Failed', value: '$fail', accent: BifrostColors.rose),
          ],
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Rows written (recent batches)',
                    style: context.th.textTheme.titleSmall),
                const SizedBox(height: 14),
                SizedBox(
                  height: 200,
                  child: recent.isEmpty
                      ? Center(
                          child: Text('No data yet',
                              style: context.th.textTheme.bodySmall))
                      : BarChart(
                          BarChartData(
                            gridData: const FlGridData(
                                show: true, drawVerticalLine: false),
                            titlesData: const FlTitlesData(show: false),
                            borderData: FlBorderData(show: false),
                            barGroups: [
                              for (var i = 0; i < recent.length; i++)
                                BarChartGroupData(
                                  x: i,
                                  barRods: [
                                    BarChartRodData(
                                      toY: recent[i].rowsWritten.toDouble(),
                                      color: BifrostColors.purple,
                                      width: 14,
                                      borderRadius: const BorderRadius.only(
                                        topLeft: Radius.circular(4),
                                        topRight: Radius.circular(4),
                                      ),
                                    ),
                                  ],
                                ),
                            ],
                          ),
                        ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, this.accent});
  final String label;
  final String value;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(label.toUpperCase(), style: context.th.textTheme.labelSmall),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: accent ?? context.cs.onSurface,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BatchesTab extends StatelessWidget {
  const _BatchesTab({required this.jobs});
  final List<Job> jobs;

  @override
  Widget build(BuildContext context) {
    if (jobs.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Text(
              'No batches yet. Trigger a run to populate this list.',
              style: context.th.textTheme.bodySmall,
            ),
          ),
        ),
      );
    }
    return Card(
      child: ListView.separated(
        itemCount: jobs.length,
        separatorBuilder: (_, __) =>
            Divider(height: 1, color: context.border, thickness: 1),
        itemBuilder: (_, i) {
          final j = jobs[i];
          return InkWell(
            onTap: () => context.go('/jobs/${j.id}'),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  SizedBox(
                    width: 100,
                    child: Text(shortId(j.id),
                        style: const TextStyle(
                            fontFamily: 'JetBrainsMono', fontSize: 11)),
                  ),
                  StatusPill(status: j.status),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      '${formatNumber(j.rowsRead)} → ${formatNumber(j.rowsWritten)} rows',
                      style: context.th.textTheme.bodySmall?.copyWith(
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  SizedBox(
                    width: 70,
                    child: Text(formatDuration(j.durationMs),
                        textAlign: TextAlign.right,
                        style: context.th.textTheme.bodySmall?.copyWith(
                          fontFeatures: const [FontFeature.tabularFigures()],
                        )),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 100,
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
  }
}

class _ConfigTab extends StatelessWidget {
  const _ConfigTab({required this.pipeline});
  final Pipeline pipeline;

  @override
  Widget build(BuildContext context) {
    final yaml = _toYaml(pipeline);
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: context.border)),
            ),
            child: Text('pipeline.yaml',
                style: context.th.textTheme.titleSmall),
          ),
          Expanded(
            child: SingleChildScrollView(
              child: Container(
                width: double.infinity,
                color: BifrostColors.zinc950,
                padding: const EdgeInsets.all(16),
                child: SelectableText(
                  yaml,
                  style: const TextStyle(
                    fontFamily: 'JetBrainsMono',
                    fontSize: 11.5,
                    height: 1.55,
                    color: Color(0xFFDDDDDD),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _toYaml(Pipeline p) {
    final b = StringBuffer();
    b.writeln('# Pipeline definition');
    b.writeln('name: ${p.name}');
    b.writeln('mode: ${p.mode}');
    b.writeln('enabled: ${p.enabled}');
    b.writeln('schedule: ${p.schedule ?? 'manual'}');
    b.writeln('source:');
    b.writeln('  connection: ${p.sourceConnectionId}');
    b.writeln('  object: ${p.sourceObject}');
    b.writeln('destination:');
    b.writeln('  connection: ${p.destinationConnectionId}');
    b.writeln('  object: ${p.destinationObject}');
    b.writeln('field_mappings:');
    if (p.fieldMappings.isEmpty) {
      b.writeln('  []  # pass-through');
    } else {
      for (final m in p.fieldMappings) {
        b.writeln('  - source: ${m.source}');
        b.writeln('    destination: ${m.destination}');
        if (m.transform != null && m.transform!.isNotEmpty) {
          b.writeln('    transform: "${m.transform}"');
        }
      }
    }
    if (p.transformSteps.isNotEmpty) {
      b.writeln('transform:');
      b.writeln('  on_error: ${p.onError}');
      b.writeln('  steps:');
      for (final s in p.transformSteps) {
        b.writeln('    - type: ${s.type}${s.enabled ? '' : '   # disabled'}');
        if (s.config.isNotEmpty) {
          final cfg = s.config.entries
              .map((e) => '${e.key}: ${_yamlScalar(e.value)}')
              .join(', ');
          b.writeln('      config: {$cfg}');
        }
      }
    }
    return b.toString();
  }

  String _yamlScalar(dynamic v) {
    if (v is String) {
      final needsQuote =
          v.contains(RegExp(r'[:#\n{}\[\]]')) || v.trim() != v || v.isEmpty;
      if (needsQuote) return '"${v.replaceAll('"', '\\"').replaceAll('\n', '\\n')}"';
      return v;
    }
    return '$v';
  }
}

class _HistoryTab extends StatelessWidget {
  const _HistoryTab({required this.jobs});
  final List<Job> jobs;

  @override
  Widget build(BuildContext context) {
    if (jobs.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Text('No history yet.', style: context.th.textTheme.bodySmall),
          ),
        ),
      );
    }
    return ListView.separated(
      itemCount: jobs.length > 30 ? 30 : jobs.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (_, i) {
        final j = jobs[i];
        return Card(
          child: InkWell(
            onTap: () => context.go('/jobs/${j.id}'),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  StatusPill(status: j.status),
                  const SizedBox(width: 10),
                  Text(shortId(j.id),
                      style: const TextStyle(
                          fontFamily: 'JetBrainsMono', fontSize: 11)),
                  const SizedBox(width: 12),
                  Text(formatDate(j.startedAt),
                      style: context.th.textTheme.bodySmall),
                  const Spacer(),
                  Text('${formatNumber(j.rowsWritten)} rows',
                      style: context.th.textTheme.bodySmall),
                  const SizedBox(width: 12),
                  Text(formatDuration(j.durationMs),
                      style: context.th.textTheme.bodySmall),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
