import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/data_providers.dart';
import '../providers/theme_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui/connector_icon.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(healthProvider);
    final connectors = ref.watch(connectorsProvider);
    final mode = ref.watch(themeProvider);

    return Padding(
      padding: const EdgeInsets.all(20),
      child: ListView(
        children: [
          Text('Settings', style: context.th.textTheme.titleLarge),
          Text('Platform information and installed connectors.',
              style: context.th.textTheme.bodySmall),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('System', style: context.th.textTheme.titleSmall),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      _Info(label: 'Status', value: health.value?['status'] ?? '—'),
                      const SizedBox(width: 24),
                      _Info(label: 'Environment', value: health.value?['env'] ?? '—'),
                      const SizedBox(width: 24),
                      _Info(label: 'App', value: health.value?['app'] ?? '—'),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Appearance', style: context.th.textTheme.titleSmall),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 6,
                    children: [
                      for (final m in const [
                        (ThemeMode.light, 'Light'),
                        (ThemeMode.dark, 'Dark'),
                        (ThemeMode.system, 'System'),
                      ])
                        ChoiceChip(
                          label: Text(m.$2),
                          selected: mode == m.$1,
                          onSelected: (_) =>
                              ref.read(themeProvider.notifier).set(m.$1),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Installed connectors',
                      style: context.th.textTheme.titleSmall),
                  const SizedBox(height: 4),
                  Text(
                    'Connectors are loaded from the backend connector registry. Drop a new connector module under app/connectors/* and it appears here.',
                    style: context.th.textTheme.bodySmall,
                  ),
                  const SizedBox(height: 12),
                  connectors.when(
                    loading: () =>
                        const Center(child: CircularProgressIndicator()),
                    error: (e, _) => Text('$e'),
                    data: (list) => Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: list.map((c) {
                        return Container(
                          width: 320,
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            border: Border.all(color: context.border),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            children: [
                              ConnectorIcon(icon: c.icon),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(c.label,
                                        style: const TextStyle(
                                            fontFamily: 'JetBrainsMono',
                                            fontSize: 13,
                                            fontWeight: FontWeight.w500)),
                                    Text(c.description,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: context.th.textTheme.bodySmall),
                                    const SizedBox(height: 4),
                                    Text(c.role.toUpperCase(),
                                        style: context.th.textTheme.labelSmall),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      }).toList(),
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

class _Info extends StatelessWidget {
  const _Info({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: context.th.textTheme.labelSmall),
        const SizedBox(height: 2),
        Text(value, style: context.th.textTheme.titleSmall),
      ],
    );
  }
}
