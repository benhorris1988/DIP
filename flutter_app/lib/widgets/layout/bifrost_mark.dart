import 'package:flutter/material.dart';

import '../../theme/colors.dart';

/// Concentric gradient arcs — the Bifrost logomark.
class BifrostMark extends StatelessWidget {
  const BifrostMark({super.key, this.size = 28});
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _BifrostMarkPainter()),
    );
  }
}

class _BifrostMarkPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    final stops = [
      (0.0, 0.75, [BifrostColors.blue, BifrostColors.purple]),
      (0.2, 0.6, [BifrostColors.purple, BifrostColors.pink]),
      (0.4, 0.45, [BifrostColors.pink, BifrostColors.amber]),
    ];

    for (final (insetTop, insetBottom, gradient) in stops) {
      final rect = Rect.fromLTRB(
        w * 0.05,
        h * insetTop,
        w * 0.95,
        h * insetBottom + h * 0.35,
      );
      final paint = Paint()
        ..shader = LinearGradient(colors: gradient).createShader(rect)
        ..strokeWidth = w * 0.07
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;

      final path = Path()
        ..moveTo(rect.left, rect.bottom * 0.8)
        ..quadraticBezierTo(
          rect.center.dx,
          rect.top,
          rect.right,
          rect.bottom * 0.8,
        );
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
