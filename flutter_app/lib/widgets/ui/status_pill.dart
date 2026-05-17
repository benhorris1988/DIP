import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../theme/colors.dart';

enum _PillVariant { emerald, amber, rose, zinc, violet }

class _PillConfig {
  final _PillVariant variant;
  final Color dot;
  final String label;
  final bool pulse;
  const _PillConfig(this.variant, this.dot, this.label, {this.pulse = false});
}

_PillConfig _configFor(String raw) {
  final s = raw.toLowerCase();
  switch (s) {
    case 'healthy':
      return const _PillConfig(_PillVariant.emerald, BifrostColors.emerald, 'healthy');
    case 'succeeded':
      return const _PillConfig(_PillVariant.emerald, BifrostColors.emerald, 'ok');
    case 'running':
      return const _PillConfig(_PillVariant.violet, BifrostColors.violet, 'running',
          pulse: true);
    case 'pending':
      return const _PillConfig(_PillVariant.amber, Color(0xFFF59E0B), 'pending');
    case 'warning':
      return const _PillConfig(_PillVariant.amber, Color(0xFFF59E0B), 'warning');
    case 'failed':
      return const _PillConfig(_PillVariant.rose, BifrostColors.rose, 'error');
    case 'error':
      return const _PillConfig(_PillVariant.rose, BifrostColors.rose, 'error');
    case 'paused':
      return const _PillConfig(_PillVariant.zinc, BifrostColors.zinc400, 'paused');
    case 'cancelled':
      return const _PillConfig(_PillVariant.zinc, BifrostColors.zinc400, 'cancelled');
    case 'untested':
      return const _PillConfig(_PillVariant.zinc, BifrostColors.zinc400, 'untested');
    default:
      return _PillConfig(_PillVariant.zinc, BifrostColors.zinc400, s);
  }
}

({Color bg, Color fg, Color ring}) _palette(_PillVariant v, bool isDark) {
  switch (v) {
    case _PillVariant.emerald:
      return isDark
          ? (
              bg: const Color(0x1A10B981),
              fg: const Color(0xFF6EE7B7),
              ring: const Color(0x4D10B981)
            )
          : (
              bg: const Color(0xFFD1FAE5),
              fg: const Color(0xFF047857),
              ring: const Color(0xFFA7F3D0)
            );
    case _PillVariant.amber:
      return isDark
          ? (
              bg: const Color(0x1AF59E0B),
              fg: const Color(0xFFFCD34D),
              ring: const Color(0x4DF59E0B)
            )
          : (
              bg: const Color(0xFFFEF3C7),
              fg: const Color(0xFFB45309),
              ring: const Color(0xFFFDE68A)
            );
    case _PillVariant.rose:
      return isDark
          ? (
              bg: const Color(0x1AE11D48),
              fg: const Color(0xFFFCA5A5),
              ring: const Color(0x4DE11D48)
            )
          : (
              bg: const Color(0xFFFFE4E6),
              fg: const Color(0xFFBE123C),
              ring: const Color(0xFFFECDD3)
            );
    case _PillVariant.violet:
      return isDark
          ? (
              bg: const Color(0x1A7C3AED),
              fg: const Color(0xFFC4B5FD),
              ring: const Color(0x4D7C3AED)
            )
          : (
              bg: const Color(0xFFEDE9FE),
              fg: const Color(0xFF6D28D9),
              ring: const Color(0xFFDDD6FE)
            );
    case _PillVariant.zinc:
      return isDark
          ? (
              bg: BifrostColors.zinc800,
              fg: BifrostColors.zinc300,
              ring: BifrostColors.zinc700
            )
          : (
              bg: BifrostColors.zinc100,
              fg: BifrostColors.zinc700,
              ring: BifrostColors.zinc200
            );
  }
}

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final cfg = _configFor(status);
    final pal = _palette(cfg.variant, context.isDark);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: pal.bg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: pal.ring),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          StatusDot(status: status, animate: cfg.pulse),
          const SizedBox(width: 5),
          Text(
            cfg.label.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.6,
              color: pal.fg,
            ),
          ),
        ],
      ),
    );
  }
}

class StatusDot extends StatefulWidget {
  const StatusDot({super.key, required this.status, this.animate = false});
  final String status;
  final bool animate;

  @override
  State<StatusDot> createState() => _StatusDotState();
}

class _StatusDotState extends State<StatusDot>
    with SingleTickerProviderStateMixin {
  AnimationController? _ctrl;

  @override
  void initState() {
    super.initState();
    if (widget.animate) {
      _ctrl = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1100),
      )..repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _ctrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = _configFor(widget.status).dot;
    final dot = Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
    if (_ctrl == null) return dot;
    return FadeTransition(
      opacity: Tween<double>(begin: 0.4, end: 1.0).animate(_ctrl!),
      child: dot,
    );
  }
}
