import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'colors.dart';

class AppTheme {
  AppTheme._();

  static ThemeData light() => _build(Brightness.light);
  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness b) {
    final isDark = b == Brightness.dark;
    final bg = isDark ? BifrostColors.zinc950 : BifrostColors.zinc50;
    final surface = isDark ? BifrostColors.zinc900 : Colors.white;
    final border = isDark ? BifrostColors.zinc800 : BifrostColors.zinc200;
    final fg = isDark ? BifrostColors.zinc100 : BifrostColors.zinc900;
    final muted = isDark ? BifrostColors.zinc400 : BifrostColors.zinc500;

    final base = isDark ? ThemeData.dark() : ThemeData.light();

    final textTheme = GoogleFonts.interTextTheme(base.textTheme).copyWith(
      bodySmall: GoogleFonts.inter(
        fontSize: 11,
        color: muted,
        height: 1.35,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 13,
        color: fg,
        height: 1.4,
      ),
      bodyLarge: GoogleFonts.inter(
        fontSize: 14,
        color: fg,
      ),
      titleSmall: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: fg,
      ),
      titleMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: fg,
      ),
      titleLarge: GoogleFonts.inter(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: fg,
      ),
      labelSmall: GoogleFonts.inter(
        fontSize: 10,
        fontWeight: FontWeight.w600,
        color: muted,
        letterSpacing: 0.6,
      ),
      labelMedium: GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: muted,
        letterSpacing: 0.4,
      ),
    );

    return base.copyWith(
      brightness: b,
      scaffoldBackgroundColor: bg,
      canvasColor: bg,
      colorScheme: ColorScheme(
        brightness: b,
        primary: BifrostColors.purple,
        onPrimary: Colors.white,
        secondary: BifrostColors.pink,
        onSecondary: Colors.white,
        error: BifrostColors.rose,
        onError: Colors.white,
        surface: surface,
        onSurface: fg,
        surfaceContainerHighest: isDark ? BifrostColors.zinc800 : BifrostColors.zinc100,
        outline: border,
      ),
      textTheme: textTheme,
      dividerColor: border,
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          side: BorderSide(color: border),
          borderRadius: BorderRadius.circular(14),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        hintStyle: GoogleFonts.inter(fontSize: 12, color: muted),
        labelStyle: GoogleFonts.inter(fontSize: 11, color: muted, letterSpacing: 0.4),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: BifrostColors.purple, width: 1.5),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BifrostColors.purple,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          textStyle: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: fg,
          side: BorderSide(color: border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          textStyle: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: fg,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          textStyle: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    );
  }
}

/// Extensions on [BuildContext] for convenient theme access.
extension AppThemeContext on BuildContext {
  ThemeData get th => Theme.of(this);
  ColorScheme get cs => Theme.of(this).colorScheme;
  bool get isDark => Theme.of(this).brightness == Brightness.dark;
  Color get muted =>
      isDark ? BifrostColors.zinc400 : BifrostColors.zinc500;
  Color get border =>
      isDark ? BifrostColors.zinc800 : BifrostColors.zinc200;
  Color get rowHover =>
      isDark ? BifrostColors.zinc800.withOpacity(0.5) : BifrostColors.zinc100;
}
