import 'package:flutter/material.dart';

class _Palette {
  final Color bg;
  final Color fg;
  final String label;
  const _Palette(this.bg, this.fg, this.label);
}

const _icons = <String, _Palette>{
  'sap': _Palette(Color(0xFFE0F2FE), Color(0xFF0369A1), 'SAP'),
  'oracle': _Palette(Color(0xFFFEE2E2), Color(0xFFB91C1C), 'ORA'),
  'surreal': _Palette(Color(0xFFEDE9FE), Color(0xFF6D28D9), 'SDB'),
  'mssql': _Palette(Color(0xFFE0E7FF), Color(0xFF3730A3), 'SQL'),
  'fabric': _Palette(Color(0xFFFEF3C7), Color(0xFFB45309), 'FAB'),
  'databricks': _Palette(Color(0xFFFFEDD5), Color(0xFFC2410C), 'DBX'),
};

class ConnectorIcon extends StatelessWidget {
  const ConnectorIcon({super.key, required this.icon, this.size = 32});
  final String icon;
  final double size;

  @override
  Widget build(BuildContext context) {
    final base = icon.split('_').first.toLowerCase();
    final p = _icons[base] ??
        const _Palette(Color(0xFFF4F4F5), Color(0xFF3F3F46), 'EXT');
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: p.bg,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        p.label,
        style: TextStyle(
          fontSize: size * 0.3,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: p.fg,
        ),
      ),
    );
  }
}
