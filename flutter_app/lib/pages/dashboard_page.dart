import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';
import '../util/format.dart';
import '../widgets/ui/sparkline.dart';
import '../widgets/ui/status_pill.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(statsProvider);
    final jobs = ref.watch(jobsProvider(const JobsQuery(limit: 50)));
    final pipelines = ref.watch(pipelinesProvider);
    final connections = ref.watch(connectionsProvider);

    final isWide = MediaQuery.sizeOf(context).width >= 1200;

    return RefreshIndicator(
      onRefresh: () async => invalidateAll(ref),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Operator console', style: context.th.textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              'Live status across connections, pipelines and recent batches.',
              style: context.th.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            _StatCards(
              stats: stats.value,
              jobs: jobs.value,
              pipelines: pipelines.value,
              connections: connections.value,
            ),
            const SizedBox(height: 16),
            if (isWide)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: _LeftColumn(jobs: jobs.value ?? const [], pipelines: pipelines.value ?? const [])),
                  const SizedBox(width: 16),
                  SizedBox(width: 320, child: _AlertsRail(jobs: jobs.value ?? const [])),
                ],
              )
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _LeftColumn(jobs: jobs.value ?? const [], pipelines: pipelines.value ?? const []),
                  const SizedBox(height: 16),
                  _AlertsRail(jobs: jobs.value ?? const []),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _StatCards extends StatelessWidget {
  const _StatCards({
    required this.stats,
    required this.jobs,
    required this.pipelines,
    required this.connections,
  });
  final Stats? stats;
  final List<Job>? jobs;
  final List<Pipeline>? pipelines;
  final List<Connection>? connections;

  @override
  Widget build(BuildContext context) {
    final cols = MediaQuery.sizeOf(context).width >= 720 ? 4 : 2;
    final successRate = (() {
      final j = jobs ?? const <Job>[];
      if (j.isEmpty) return null;
      final ok = j.where((x) => x.status == 'succeeded').length;
      return (ok / j.length * 100).round();
    })();
    final rowsTrend = (jobs ?? const <Job>[])
        .take(12)
        .toList()
        .reversed
        .map((j) => j.rowsWritten)
        .toList();

    final cards = [
      _StatCard(
        label: 'Active pipelines',
        value: '${stats?.pipelines ?? 0}',
        sub: '${(pipelines ?? const []).where((p) => p.enabled).length} enabled',
        icon: Icons.account_tree_outlined,
        route: '/pipelines',
      ),
      _StatCard(
        label: 'Batches · 24h',
        value: '${stats?.jobs ?? 0}',
        sub: successRate == null ? '—' : '$successRate% success',
        icon: Icons.bolt_outlined,
        route: '/jobs',
        sparkline: rowsTrend,
      ),
      _StatCard(
        label: 'Failed runs',
        value: '${stats?.failed ?? 0}',
        sub: '${stats?.succeeded ?? 0} succeeded',
        icon: Icons.report_outlined,
        route: '/errors',
        accent: BifrostColors.rose,
      ),
      _StatCard(
        label: 'Connections',
        value: '${stats?.connections ?? 0}',
        sub:
            '${(connections ?? const []).where((c) => c.status == 'healthy').length} healthy',
        icon: Icons.cable_outlined,
        route: '/connections',
      ),
    ];
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: cols,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.9,
      children: cards,
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.sub,
    required this.icon,
    required this.route,
    this.sparkline,
    this.accent,
  });
  final String label;
  final String value;
  final String sub;
  final IconData icon;
  final String route;
  final List<num>? sparkline;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.go(route),
      borderRadius: BorderRadius.circular(14),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 13, color: context.muted),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      label.toUpperCase(),
                      style: context.th.textTheme.labelSmall,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Icon(Icons.north_east, size: 13, color: context.muted),
                ],
              ),
              const Spacer(),
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          value,
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w600,
                            color: accent ?? context.cs.onSurface,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                        Text(sub, style: context.th.textTheme.bodySmall),
                      ],
                    ),
                  ),
                  if (sparkline != null && sparkline!.isNotEmpty)
                    Sparkline(data: sparkline!, color: BifrostColors.emerald),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LeftColumn extends StatelessWidget {
  const _LeftColumn({required this.jobs, required this.pipelines});
  final List<Job> jobs;
  final List<Pipeline> pipelines;

  @override
  Widget build(BuildContext context) {
    final recent = jobs.take(10).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _SectionCard(
          title: 'Pipelines',
          trailingRoute: '/pipelines',
          child: pipelines.isEmpty
              ? _emptyRow(context, 'No pipelines yet — create one to start moving data.')
              : Column(
                  children: pipelines.take(6).map((p) {
                    final last = jobs.where((j) => j.pipelineId == p.id).firstOrNull;
                    return _RowTile(
                      onTap: () => context.go('/pipelines/${p.id}'),
                      title: p.name,
                      subtitle:
                          '${p.sourceObject} → ${p.destinationObject}',
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          StatusPill(
                            status: last?.status ??
                                (p.enabled ? 'healthy' : 'paused'),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            last == null ? '—' : formatDate(last.startedAt),
                            style: context.th.textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'Recent batches',
          trailingRoute: '/jobs',
          child: recent.isEmpty
              ? _emptyRow(context, 'No batch runs yet.')
              : Column(
                  children: recent.map((j) {
                    return _RowTile(
                      onTap: () => context.go('/jobs/${j.id}'),
                      title: j.pipelineName,
                      subtitle: shortId(j.id),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          StatusPill(status: j.status),
                          const SizedBox(width: 10),
                          Text(
                            '${formatNumber(j.rowsWritten)} rows',
                            style: context.th.textTheme.bodySmall?.copyWith(
                              fontFeatures: const [FontFeature.tabularFigures()],
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            formatDuration(j.durationMs),
                            style: context.th.textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
        ),
      ],
    );
  }

  Widget _emptyRow(BuildContext context, String text) => Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: Text(text, style: context.th.textTheme.bodySmall),
        ),
      );
}

class _AlertsRail extends StatelessWidget {
  const _AlertsRail({required this.jobs});
  final List<Job> jobs;

  @override
  Widget build(BuildContext context) {
    final alerts = jobs.where((j) => j.status == 'failed').take(8).toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.notifications_outlined,
                    size: 13, color: context.muted),
                const SizedBox(width: 6),
                Text('RECENT ALERTS',
                    style: context.th.textTheme.labelSmall),
                const Spacer(),
                if (alerts.isNotEmpty) StatusPill(status: 'failed'),
              ],
            ),
            const SizedBox(height: 10),
            if (alerts.isEmpty)
              Row(
                children: [
                  const Icon(Icons.check_circle_outline,
                      size: 14, color: BifrostColors.emerald),
                  const SizedBox(width: 6),
                  Text('Nothing failed recently.',
                      style: context.th.textTheme.bodySmall),
                ],
              ),
            for (final a in alerts) ...[
              const SizedBox(height: 10),
              InkWell(
                onTap: () => context.go('/jobs/${a.id}'),
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    border: Border.all(color: context.border),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(formatDate(a.startedAt),
                          style: context.th.textTheme.bodySmall),
                      const SizedBox(height: 2),
                      Text(a.pipelineName,
                          style: context.th.textTheme.titleSmall
                              ?.copyWith(fontFamily: 'JetBrainsMono')),
                      const SizedBox(height: 4),
                      Text(
                        a.error ?? 'Failed',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 11,
                          color: BifrostColors.rose,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.child,
    this.trailingRoute,
  });
  final String title;
  final Widget child;
  final String? trailingRoute;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: context.border)),
            ),
            child: Row(
              children: [
                Text(title, style: context.th.textTheme.titleSmall),
                const Spacer(),
                if (trailingRoute != null)
                  InkWell(
                    onTap: () => context.go(trailingRoute!),
                    child: const Text(
                      'View all',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: BifrostColors.purple,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          child,
        ],
      ),
    );
  }
}

class _RowTile extends StatelessWidget {
  const _RowTile({
    required this.title,
    required this.subtitle,
    required this.trailing,
    required this.onTap,
  });
  final String title;
  final String subtitle;
  final Widget trailing;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: context.border)),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: context.th.textTheme.bodyMedium?.copyWith(
                        fontFamily: 'JetBrainsMono',
                      )),
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: context.th.textTheme.bodySmall?.copyWith(
                        fontFamily: 'JetBrainsMono',
                      )),
                ],
              ),
            ),
            trailing,
          ],
        ),
      ),
    );
  }
}
