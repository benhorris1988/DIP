import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';

/// Subscribes to ``/api/dag-runs/stream`` and shows a small live tile
/// summarising what's currently materialising. Hidden when no runs are
/// in flight so it doesn't take screen space when idle.
class DagRunsLive extends ConsumerStatefulWidget {
  const DagRunsLive({super.key});

  @override
  ConsumerState<DagRunsLive> createState() => _DagRunsLiveState();
}

class _DagRunsLiveState extends ConsumerState<DagRunsLive> {
  StreamSubscription<Map<String, dynamic>>? _sub;
  // Map<run_id, latest payload> — only running runs are kept.
  final Map<String, Map<String, dynamic>> _runs = {};

  @override
  void initState() {
    super.initState();
    _connect();
  }

  void _connect() {
    final client = ref.read(apiClientProvider);
    _sub = client.streamAllDagRuns().listen(
      (payload) {
        final id = payload['id'] as String?;
        if (id == null) return;
        setState(() {
          final status = payload['status'] as String?;
          final event = payload['event'] as String?;
          if (status == 'running' && event != 'completed') {
            _runs[id] = payload;
          } else {
            _runs.remove(id);
          }
        });
        if (payload['event'] == 'completed') {
          // Surface the result + refresh the assets list / graph
          invalidateAll(ref);
        }
      },
      onError: (_) {},
    );
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_runs.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: context.isDark
            ? const Color(0xFF1E2530)
            : const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: context.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 10,
                height: 10,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: BifrostColors.purple,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${_runs.length} DAG run${_runs.length == 1 ? '' : 's'} in flight',
                style: context.th.textTheme.titleSmall,
              ),
            ],
          ),
          const SizedBox(height: 4),
          for (final r in _runs.values)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Text(
                _line(r),
                style: const TextStyle(
                  fontFamily: 'JetBrainsMono',
                  fontSize: 11,
                ),
              ),
            ),
        ],
      ),
    );
  }

  String _line(Map<String, dynamic> r) {
    final triggered = r['triggered_by'] ?? 'manual';
    final pipeline = r['current_pipeline_name'] ?? '...';
    final currentAssets =
        (r['current_assets'] as List?)?.join(', ') ?? '';
    final resolved =
        (r['resolved_assets'] as List?)?.length ?? 0;
    final tag = triggered == 'auto' ? '[auto]' : '[$triggered]';
    return '$tag $pipeline → $currentAssets ($resolved assets total)';
  }
}
