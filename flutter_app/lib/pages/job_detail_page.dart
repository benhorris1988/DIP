import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';
import '../util/format.dart';
import '../widgets/ui/status_pill.dart';

class JobDetailPage extends ConsumerStatefulWidget {
  const JobDetailPage({super.key, required this.id});
  final String id;

  @override
  ConsumerState<JobDetailPage> createState() => _JobDetailPageState();
}

class _JobDetailPageState extends ConsumerState<JobDetailPage> {
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    _poll = Timer.periodic(const Duration(seconds: 3), (_) {
      final state = ref.read(jobProvider(widget.id));
      final s = state.value?.status;
      if (s == 'running' || s == 'pending') {
        ref.invalidate(jobProvider(widget.id));
      }
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final jobAsync = ref.watch(jobProvider(widget.id));
    return jobAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('$e')),
      data: (j) => Padding(
        padding: const EdgeInsets.all(20),
        child: ListView(
          children: [
            TextButton.icon(
              onPressed: () => context.go('/jobs'),
              icon: const Icon(Icons.arrow_back, size: 14),
              label: const Text('Back'),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text(shortId(j.id),
                    style: context.th.textTheme.titleLarge?.copyWith(
                        fontFamily: 'JetBrainsMono')),
                const SizedBox(width: 10),
                StatusPill(status: j.status),
              ],
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 12,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                InkWell(
                  onTap: () => context.go('/pipelines/${j.pipelineId}'),
                  child: Text(j.pipelineName,
                      style: const TextStyle(
                          fontFamily: 'JetBrainsMono',
                          color: BifrostColors.purple,
                          fontSize: 12,
                          fontWeight: FontWeight.w500)),
                ),
                Text(formatDate(j.startedAt),
                    style: context.th.textTheme.bodySmall),
                Text('→', style: context.th.textTheme.bodySmall),
                Text(formatDate(j.finishedAt),
                    style: context.th.textTheme.bodySmall),
                Text(formatDuration(j.durationMs),
                    style: const TextStyle(
                        fontFamily: 'JetBrainsMono', fontSize: 11)),
                Text('triggered: ${j.triggeredBy}',
                    style: context.th.textTheme.bodySmall),
              ],
            ),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount:
                  MediaQuery.sizeOf(context).width >= 700 ? 4 : 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 2.0,
              children: [
                _Metric(label: 'Rows read', value: formatNumber(j.rowsRead)),
                _Metric(
                    label: 'Rows written', value: formatNumber(j.rowsWritten)),
                _Metric(
                    label: 'Rows failed',
                    value: formatNumber(j.rowsFailed),
                    accent: j.rowsFailed > 0 ? BifrostColors.rose : null),
                _Metric(
                    label: 'Duration', value: formatDuration(j.durationMs)),
              ],
            ),
            const SizedBox(height: 16),
            _StepTimeline(job: j),
            const SizedBox(height: 16),
            if (j.error != null)
              Card(
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: const Color(0x14E11D48),
                    border: Border.all(color: const Color(0x4DE11D48)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('ERROR',
                          style: context.th.textTheme.labelSmall?.copyWith(
                            color: const Color(0xFFBE123C),
                          )),
                      const SizedBox(height: 4),
                      SelectableText(
                        j.error!,
                        style: const TextStyle(
                            fontFamily: 'JetBrainsMono',
                            fontSize: 12,
                            color: Color(0xFFBE123C)),
                      ),
                    ],
                  ),
                ),
              ),
            if (j.error != null) const SizedBox(height: 16),
            Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      border:
                          Border(bottom: BorderSide(color: context.border)),
                    ),
                    child: Text('Log stream',
                        style: context.th.textTheme.titleSmall),
                  ),
                  Container(
                    constraints: const BoxConstraints(maxHeight: 400),
                    color: BifrostColors.zinc950,
                    padding: const EdgeInsets.all(12),
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (j.log.isEmpty)
                            const Text('No log entries',
                                style: TextStyle(
                                    fontFamily: 'JetBrainsMono',
                                    fontSize: 11,
                                    color: BifrostColors.zinc500)),
                          for (final l in j.log)
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 1),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    l.ts.length > 19
                                        ? l.ts.substring(11, 19)
                                        : l.ts,
                                    style: const TextStyle(
                                        fontFamily: 'JetBrainsMono',
                                        fontSize: 11,
                                        color: BifrostColors.zinc500),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      l.message,
                                      style: TextStyle(
                                        fontFamily: 'JetBrainsMono',
                                        fontSize: 11,
                                        color: l.level == 'error'
                                            ? const Color(0xFFFCA5A5)
                                            : l.level == 'warn'
                                                ? const Color(0xFFFCD34D)
                                                : BifrostColors.zinc200,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, this.accent});
  final String label;
  final String value;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(label.toUpperCase(), style: context.th.textTheme.labelSmall),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: accent ?? context.cs.onSurface,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StepTimeline extends StatelessWidget {
  const _StepTimeline({required this.job});
  final Job job;

  @override
  Widget build(BuildContext context) {
    final steps = _buildSteps(job);
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: context.border)),
            ),
            child:
                Text('Step timeline', style: context.th.textTheme.titleSmall),
          ),
          if (steps.isEmpty)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text('No steps recorded.',
                  style: context.th.textTheme.bodySmall),
            )
          else
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  for (final s in steps) ...[
                    Row(
                      children: [
                        SizedBox(
                          width: 120,
                          child: Text(s.label,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontFamily: 'JetBrainsMono',
                                  fontSize: 11)),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: SizedBox(
                            height: 10,
                            child: Stack(
                              children: [
                                Container(
                                  decoration: BoxDecoration(
                                    color: context.isDark
                                        ? BifrostColors.zinc800
                                        : BifrostColors.zinc100,
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                ),
                                LayoutBuilder(builder: (_, c) {
                                  return Positioned(
                                    left: c.maxWidth * (s.left / 100),
                                    width: c.maxWidth *
                                        (s.width / 100).clamp(0.02, 1.0),
                                    top: 0,
                                    bottom: 0,
                                    child: Container(
                                      decoration: BoxDecoration(
                                        gradient: s.error
                                            ? const LinearGradient(colors: [
                                                BifrostColors.rose,
                                                BifrostColors.rose
                                              ])
                                            : BifrostColors.gradient,
                                        borderRadius:
                                            BorderRadius.circular(20),
                                      ),
                                    ),
                                  );
                                }),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        SizedBox(
                          width: 60,
                          child: Text(formatDuration(s.durationMs),
                              textAlign: TextAlign.right,
                              style: const TextStyle(
                                  fontFamily: 'JetBrainsMono',
                                  fontSize: 11)),
                        ),
                        const SizedBox(width: 8),
                        Icon(
                          s.error ? Icons.error_outline : Icons.check_circle,
                          size: 13,
                          color: s.error
                              ? BifrostColors.rose
                              : BifrostColors.emerald,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Step {
  final String label;
  final double left;
  final double width;
  final int durationMs;
  final bool error;
  _Step(this.label, this.left, this.width, this.durationMs, this.error);
}

List<_Step> _buildSteps(Job j) {
  if (j.log.isEmpty || j.startedAt == null) return const [];
  final start = DateTime.tryParse(j.startedAt!)?.millisecondsSinceEpoch;
  if (start == null) return const [];
  final end = (j.finishedAt != null
          ? DateTime.tryParse(j.finishedAt!)?.millisecondsSinceEpoch
          : null) ??
      DateTime.now().millisecondsSinceEpoch;
  final total = (end - start).clamp(1, 1 << 31);
  final steps = <_Step>[];
  for (var i = 0; i < j.log.length; i++) {
    final cur = DateTime.tryParse(j.log[i].ts)?.millisecondsSinceEpoch ?? start;
    final next = i < j.log.length - 1
        ? DateTime.tryParse(j.log[i + 1].ts)?.millisecondsSinceEpoch ?? end
        : end;
    final head = j.log[i].message.split(':').first;
    final label = head.length > 22 ? head.substring(0, 22) : head;
    steps.add(_Step(
      label,
      ((cur - start) / total) * 100,
      ((next - cur) / total) * 100,
      next - cur,
      j.log[i].level == 'error',
    ));
  }
  return steps;
}
