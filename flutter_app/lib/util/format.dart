import 'package:intl/intl.dart';

String formatDuration(num? ms) {
  if (ms == null) return '—';
  final v = ms.toInt();
  if (v < 1000) return '${v}ms';
  final s = v / 1000.0;
  if (s < 60) return '${s.toStringAsFixed(1)}s';
  final m = s / 60.0;
  if (m < 60) return '${m.toStringAsFixed(1)}m';
  final h = m / 60.0;
  return '${h.toStringAsFixed(1)}h';
}

String formatDate(String? iso) {
  if (iso == null || iso.isEmpty) return '—';
  final dt = DateTime.tryParse(iso);
  if (dt == null) return iso;
  final now = DateTime.now();
  final diff = now.difference(dt.toLocal());
  if (diff.inMinutes < 1) return 'just now';
  if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
  if (diff.inHours < 24) return '${diff.inHours}h ago';
  if (diff.inDays < 7) return '${diff.inDays}d ago';
  return DateFormat('yyyy-MM-dd HH:mm').format(dt.toLocal());
}

String formatNumber(num n) {
  return NumberFormat.decimalPattern().format(n);
}

String shortId(String id) => id.length > 8 ? id.substring(0, 8) : id;
