import 'package:flutter/material.dart';

import '../../theme/colors.dart';

/// Filled button rendered with the Bifrost gradient.
class BifrostButton extends StatelessWidget {
  const BifrostButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
    this.enabled = true,
  });

  final VoidCallback? onPressed;
  final String label;
  final IconData? icon;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final disabled = !enabled || onPressed == null;
    return Opacity(
      opacity: disabled ? 0.5 : 1.0,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: disabled ? null : onPressed,
          child: Ink(
            decoration: BoxDecoration(
              gradient: BifrostColors.gradient,
              borderRadius: BorderRadius.circular(8),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(icon, color: Colors.white, size: 14),
                  const SizedBox(width: 6),
                ],
                Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
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
