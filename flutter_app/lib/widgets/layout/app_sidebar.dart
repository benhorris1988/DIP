import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/data_providers.dart';
import '../../theme/app_theme.dart';
import '../ui/status_pill.dart';
import 'bifrost_mark.dart';

class NavItem {
  final String label;
  final String route;
  final IconData icon;
  const NavItem(this.label, this.route, this.icon);
}

const navItems = [
  NavItem('Dashboard', '/dashboard', Icons.space_dashboard_outlined),
  NavItem('Assets', '/assets', Icons.hub_outlined),
  NavItem('Pipelines', '/pipelines', Icons.account_tree_outlined),
  NavItem('Connections', '/connections', Icons.cable_outlined),
  NavItem('Job Runs', '/jobs', Icons.bolt_outlined),
  NavItem('Error Explorer', '/errors', Icons.report_outlined),
  NavItem('Settings', '/settings', Icons.tune_outlined),
];

class AppSidebar extends ConsumerWidget {
  const AppSidebar({super.key, this.onItemTap});
  final VoidCallback? onItemTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    return Container(
      width: 240,
      decoration: BoxDecoration(
        color: context.cs.surface,
        border: Border(right: BorderSide(color: context.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              children: [
                for (final item in navItems)
                  _NavTile(
                    item: item,
                    active: location.startsWith(item.route),
                    onTap: () {
                      onItemTap?.call();
                      context.go(item.route);
                    },
                  ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  child: Text('PIPELINES',
                      style: context.th.textTheme.labelSmall),
                ),
                _PipelinesList(onTap: onItemTap),
              ],
            ),
          ),
          _BackendStatus(),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration:
          BoxDecoration(border: Border(bottom: BorderSide(color: context.border))),
      child: Row(
        children: [
          const BifrostMark(size: 28),
          const SizedBox(width: 10),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Data Integration',
                  style: context.th.textTheme.titleSmall
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 1),
              Text('Operator Console',
                  style: context.th.textTheme.labelSmall),
            ],
          ),
        ],
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile(
      {required this.item, required this.active, required this.onTap});
  final NavItem item;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = active
        ? (context.isDark ? Colors.white : const Color(0xFF18181B))
        : context.muted;
    return Material(
      color: active ? context.rowHover : Colors.transparent,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          child: Row(
            children: [
              Icon(item.icon, size: 16, color: color),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  item.label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: color,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PipelinesList extends ConsumerWidget {
  const _PipelinesList({this.onTap});
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pipelines = ref.watch(pipelinesProvider);
    return pipelines.when(
      loading: () => const SizedBox.shrink(),
      error: (e, _) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        child: Text('—',
            style: context.th.textTheme.bodySmall
                ?.copyWith(color: context.muted)),
      ),
      data: (list) {
        if (list.isEmpty) {
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            child: Text('No pipelines yet',
                style: context.th.textTheme.bodySmall),
          );
        }
        final location = GoRouterState.of(context).matchedLocation;
        return Column(
          children: list.take(50).map((p) {
            final route = '/pipelines/${p.id}';
            final active = location == route;
            return Material(
              color: active ? context.rowHover : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              child: InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: () {
                  onTap?.call();
                  context.go(route);
                },
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  child: Row(
                    children: [
                      StatusDot(status: p.enabled ? 'healthy' : 'paused'),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          p.name,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12,
                            fontFamily: 'JetBrainsMono',
                            color: context.cs.onSurface,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        );
      },
    );
  }
}

class _BackendStatus extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(healthProvider);
    final ok = health.maybeWhen(data: (h) => h['status'] == 'ok', orElse: () => false);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration:
          BoxDecoration(border: Border(top: BorderSide(color: context.border))),
      child: Row(
        children: [
          StatusDot(status: ok ? 'healthy' : 'error'),
          const SizedBox(width: 8),
          Text('Backend', style: context.th.textTheme.bodySmall),
          const Spacer(),
          Text(
            ok ? 'online' : 'offline',
            style: context.th.textTheme.bodySmall?.copyWith(
              fontFamily: 'JetBrainsMono',
              color: context.muted,
            ),
          ),
        ],
      ),
    );
  }
}
