import 'package:flutter/material.dart';

/// Bifrost palette shared across themes.
class BifrostColors {
  BifrostColors._();

  // Bifrost gradient stops
  static const blue = Color(0xFF2563EB);
  static const purple = Color(0xFF7C3AED);
  static const pink = Color(0xFFEC4899);
  static const amber = Color(0xFFF59E0B);

  static const gradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [blue, purple, pink, amber],
    stops: [0.0, 0.35, 0.65, 1.0],
  );

  // Zinc neutrals
  static const zinc50 = Color(0xFFFAFAFA);
  static const zinc100 = Color(0xFFF4F4F5);
  static const zinc200 = Color(0xFFE4E4E7);
  static const zinc300 = Color(0xFFD4D4D8);
  static const zinc400 = Color(0xFFA1A1AA);
  static const zinc500 = Color(0xFF71717A);
  static const zinc600 = Color(0xFF52525B);
  static const zinc700 = Color(0xFF3F3F46);
  static const zinc800 = Color(0xFF27272A);
  static const zinc900 = Color(0xFF18181B);
  static const zinc950 = Color(0xFF09090B);

  // Status palette
  static const emerald = Color(0xFF10B981);
  static const emeraldFg = Color(0xFF047857);
  static const rose = Color(0xFFE11D48);
  static const roseFg = Color(0xFFBE123C);
  static const amberFg = Color(0xFFB45309);
  static const violet = Color(0xFF7C3AED);
}
