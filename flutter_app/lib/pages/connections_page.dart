import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../util/format.dart';
import '../widgets/ui/bifrost_button.dart';
import '../widgets/ui/connector_icon.dart';
import '../widgets/ui/empty_state.dart';
import '../widgets/ui/status_pill.dart';

class ConnectionsPage extends ConsumerStatefulWidget {
  const ConnectionsPage({super.key});
  @override
  ConsumerState<ConnectionsPage> createState() => _ConnectionsPageState();
}

class _ConnectionsPageState extends ConsumerState<ConnectionsPage> {
  String _filter = 'all';

  @override
  Widget build(BuildContext context) {
    final connections = ref.watch(connectionsProvider);
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
                    Text('Connections', style: context.th.textTheme.titleLarge),
                    Text(
                      'Configure source and destination systems used by your pipelines.',
                      style: context.th.textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              BifrostButton(
                onPressed: () => context.go('/connections/new'),
                label: 'New connection',
                icon: Icons.add,
              ),
            ],
          ),
          const SizedBox(height: 12),
          _Segmented(
            value: _filter,
            options: const ['all', 'source', 'destination'],
            onChanged: (v) => setState(() => _filter = v),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: connections.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('$e')),
              data: (list) {
                final filtered = _filter == 'all'
                    ? list
                    : list.where((c) => c.role == _filter).toList();
                if (filtered.isEmpty) {
                  return EmptyState(
                    icon: Icons.cable_outlined,
                    title: 'No connections yet',
                    description:
                        'Add your first source or destination to get started.',
                    action: BifrostButton(
                      onPressed: () => context.go('/connections/new'),
                      label: 'New connection',
                      icon: Icons.add,
                    ),
                  );
                }
                return GridView.builder(
                  gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 380,
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 2.1,
                  ),
                  itemCount: filtered.length,
                  itemBuilder: (_, i) =>
                      _ConnectionCard(connection: filtered[i]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _Segmented extends StatelessWidget {
  const _Segmented({
    required this.value,
    required this.options,
    required this.onChanged,
  });
  final String value;
  final List<String> options;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: context.isDark
            ? const Color(0xFF27272A)
            : const Color(0xFFE4E4E7),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: options
            .map((o) => InkWell(
                  onTap: () => onChanged(o),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: value == o
                          ? context.cs.surface
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      o[0].toUpperCase() + o.substring(1),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: value == o ? context.cs.onSurface : context.muted,
                      ),
                    ),
                  ),
                ))
            .toList(),
      ),
    );
  }
}

class _ConnectionCard extends ConsumerStatefulWidget {
  const _ConnectionCard({required this.connection});
  final Connection connection;
  @override
  ConsumerState<_ConnectionCard> createState() => _ConnectionCardState();
}

class _ConnectionCardState extends ConsumerState<_ConnectionCard> {
  String? _testResult;
  bool _ok = false;
  bool _testing = false;

  @override
  Widget build(BuildContext context) {
    final c = widget.connection;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                ConnectorIcon(icon: c.connectorType),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InkWell(
                        onTap: () => context.go('/connections/${c.id}'),
                        child: Text(
                          c.name,
                          style: context.th.textTheme.titleSmall?.copyWith(
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                      ),
                      Text(c.connectorType,
                          style: context.th.textTheme.bodySmall),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          StatusPill(status: c.role),
                          const SizedBox(width: 6),
                          StatusPill(status: c.status),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (c.description != null && c.description!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(c.description!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.th.textTheme.bodySmall),
            ],
            const Spacer(),
            Row(
              children: [
                Text('LAST TESTED  ',
                    style: context.th.textTheme.labelSmall),
                Text(formatDate(c.lastTestedAt),
                    style: const TextStyle(
                        fontSize: 11, fontFamily: 'JetBrainsMono')),
                const Spacer(),
                OutlinedButton.icon(
                  onPressed: _testing
                      ? null
                      : () async {
                          setState(() => _testing = true);
                          try {
                            final r = await ref
                                .read(apiClientProvider)
                                .testConnection(c.id);
                            setState(() {
                              _testResult = r['message'] as String?;
                              _ok = (r['ok'] ?? false) as bool;
                            });
                            ref.invalidate(connectionsProvider);
                          } catch (e) {
                            setState(() {
                              _testResult = '$e';
                              _ok = false;
                            });
                          } finally {
                            if (mounted) setState(() => _testing = false);
                          }
                        },
                  icon: const Icon(Icons.bolt_outlined, size: 13),
                  label: const Text('Test'),
                ),
                const SizedBox(width: 6),
                OutlinedButton(
                  onPressed: () => context.go('/connections/${c.id}'),
                  child: const Text('Edit'),
                ),
              ],
            ),
            if (_testResult != null) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: _ok
                      ? const Color(0x1A10B981)
                      : const Color(0x1AE11D48),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  _testResult!,
                  style: TextStyle(
                    fontSize: 11,
                    color: _ok ? const Color(0xFF047857) : const Color(0xFFBE123C),
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
