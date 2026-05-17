import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/theme_provider.dart';
import '../../theme/app_theme.dart';
import '../../theme/colors.dart';

class AppHeader extends ConsumerWidget implements PreferredSizeWidget {
  const AppHeader({super.key, this.showMenuButton = false, this.onMenu});
  final bool showMenuButton;
  final VoidCallback? onMenu;

  @override
  Size get preferredSize => const Size.fromHeight(56);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(themeProvider);
    final loc = GoRouterState.of(context).matchedLocation;
    final parts = loc.split('/').where((p) => p.isNotEmpty).toList();
    final root = parts.isEmpty ? 'dashboard' : parts.first;

    return Container(
      decoration: BoxDecoration(
        color: context.cs.surface.withOpacity(0.95),
        border: Border(bottom: BorderSide(color: context.border)),
      ),
      child: SafeArea(
        bottom: false,
        child: SizedBox(
          height: 56,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                if (showMenuButton)
                  IconButton(
                    icon: const Icon(Icons.menu, size: 18),
                    onPressed: onMenu,
                  ),
                Text(
                  _titleFor(root),
                  style: context.th.textTheme.titleMedium,
                ),
                if (parts.length > 1) ...[
                  const SizedBox(width: 8),
                  Icon(Icons.chevron_right, size: 16, color: context.muted),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      parts.skip(1).join(' / '),
                      overflow: TextOverflow.ellipsis,
                      style: context.th.textTheme.bodySmall?.copyWith(
                        fontFamily: 'JetBrainsMono',
                        color: context.muted,
                      ),
                    ),
                  ),
                ],
                const Spacer(),
                IconButton(
                  tooltip: mode == ThemeMode.dark ? 'Light mode' : 'Dark mode',
                  icon: Icon(
                    mode == ThemeMode.dark ? Icons.light_mode : Icons.dark_mode,
                    size: 16,
                  ),
                  onPressed: () => ref.read(themeProvider.notifier).toggle(),
                ),
                const SizedBox(width: 4),
                Container(
                  width: 28,
                  height: 28,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(
                    gradient: BifrostColors.gradient,
                    shape: BoxShape.circle,
                  ),
                  child: const Text(
                    'A',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

String _titleFor(String root) {
  switch (root) {
    case 'dashboard':
      return 'Dashboard';
    case 'pipelines':
      return 'Pipelines';
    case 'connections':
      return 'Connections';
    case 'jobs':
      return 'Job Runs';
    case 'errors':
      return 'Error Explorer';
    case 'settings':
      return 'Settings';
    default:
      return root;
  }
}
