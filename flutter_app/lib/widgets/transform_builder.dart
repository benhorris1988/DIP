import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/models.dart';
import '../theme/app_theme.dart';
import '../theme/colors.dart';

/// Drag-and-drop builder for a pipeline's in-flight transformation plan.
///
/// Renders an ordered, reorderable list of transformation steps. Each step's
/// config form is driven by the catalog metadata fetched from
/// `GET /api/transforms`, so new backend transform types appear here without
/// any client change. Code-type fields ship inline examples that can be
/// inserted with one tap.
class TransformBuilder extends StatefulWidget {
  const TransformBuilder({
    super.key,
    required this.catalog,
    required this.initialSteps,
    required this.initialOnError,
    required this.onChanged,
  });

  final List<TransformCatalogEntry> catalog;
  final List<TransformStep> initialSteps;
  final String initialOnError;
  final void Function(List<TransformStep> steps, String onError) onChanged;

  @override
  State<TransformBuilder> createState() => _TransformBuilderState();
}

class _StepState {
  _StepState({required this.id, required this.type, this.enabled = true});
  final int id;
  String type;
  bool enabled;
  final Map<String, TextEditingController> controllers = {};
  final Map<String, dynamic> misc = {}; // boolean / select values
  final Map<String, dynamic> raw = {}; // fallback for unknown types
}

class _TransformBuilderState extends State<TransformBuilder> {
  final Map<String, TransformCatalogEntry> _byType = {};
  final List<_StepState> _steps = [];
  late String _onError;
  int _seq = 0;

  @override
  void initState() {
    super.initState();
    for (final e in widget.catalog) {
      _byType[e.type] = e;
    }
    _onError = widget.initialOnError;
    for (final s in widget.initialSteps) {
      _steps.add(_mkStep(s.type, config: s.config, enabled: s.enabled));
    }
  }

  @override
  void dispose() {
    for (final s in _steps) {
      for (final c in s.controllers.values) {
        c.dispose();
      }
    }
    super.dispose();
  }

  _StepState _mkStep(String type,
      {Map<String, dynamic>? config, bool enabled = true}) {
    final s = _StepState(id: _seq++, type: type, enabled: enabled);
    final Map<String, dynamic> cfg = config ?? const {};
    s.raw.addAll(cfg);
    final entry = _byType[type];
    if (entry != null) {
      for (final f in entry.fields) {
        final existing = cfg[f.name];
        switch (f.type) {
          case 'boolean':
            s.misc[f.name] = existing ?? (f.defaultValue ?? false);
            break;
          case 'select':
            s.misc[f.name] = (existing ?? f.defaultValue)?.toString();
            break;
          default:
            s.controllers[f.name] = TextEditingController(
              text: existing?.toString() ?? (f.defaultValue?.toString() ?? ''),
            )..addListener(_emit);
        }
      }
    }
    return s;
  }

  TransformStep _serialize(_StepState s) {
    final entry = _byType[s.type];
    if (entry == null) {
      return TransformStep(
          type: s.type, config: Map.of(s.raw), enabled: s.enabled);
    }
    final config = <String, dynamic>{};
    for (final f in entry.fields) {
      switch (f.type) {
        case 'boolean':
          config[f.name] = s.misc[f.name] ?? (f.defaultValue ?? false);
          break;
        case 'select':
          final v = s.misc[f.name] ?? f.defaultValue;
          if (v != null) config[f.name] = v;
          break;
        default:
          final t = s.controllers[f.name]?.text ?? '';
          if (t.isNotEmpty) config[f.name] = t;
      }
    }
    return TransformStep(type: s.type, config: config, enabled: s.enabled);
  }

  void _emit() {
    widget.onChanged(_steps.map(_serialize).toList(), _onError);
  }

  void _addStep(String type) {
    setState(() => _steps.add(_mkStep(type)));
    _emit();
  }

  void _removeStep(int index) {
    final s = _steps.removeAt(index);
    for (final c in s.controllers.values) {
      c.dispose();
    }
    setState(() {});
    _emit();
  }

  void _onReorder(int oldIndex, int newIndex) {
    setState(() {
      if (newIndex > oldIndex) newIndex -= 1;
      final s = _steps.removeAt(oldIndex);
      _steps.insert(newIndex, s);
    });
    _emit();
  }

  Future<void> _pickType() async {
    final type = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (_) => _TransformPicker(catalog: widget.catalog),
    );
    if (type != null) _addStep(type);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            SizedBox(
              width: 220,
              child: DropdownButtonFormField<String>(
                value: _onError,
                decoration: const InputDecoration(
                  labelText: 'ON ERROR',
                  helperText: 'How to handle a row that fails a step',
                ),
                items: const [
                  DropdownMenuItem(
                      value: 'skip', child: Text('Skip & log bad rows')),
                  DropdownMenuItem(
                      value: 'fail', child: Text('Fail the whole run')),
                ],
                onChanged: (v) {
                  setState(() => _onError = v ?? 'skip');
                  _emit();
                },
              ),
            ),
            const Spacer(),
            OutlinedButton.icon(
              onPressed: widget.catalog.isEmpty ? null : _pickType,
              icon: const Icon(Icons.add, size: 14),
              label: const Text('Add transformation'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (_steps.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: context.border),
            ),
            child: Column(
              children: [
                Icon(Icons.auto_fix_high, size: 20, color: context.muted),
                const SizedBox(height: 8),
                Text(
                  'No transformations yet. Records pass straight through.\n'
                  'Add steps to rename, cast, derive or filter — drag to reorder.',
                  textAlign: TextAlign.center,
                  style: context.th.textTheme.bodySmall,
                ),
              ],
            ),
          )
        else
          ReorderableListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            buildDefaultDragHandles: false,
            itemCount: _steps.length,
            onReorder: _onReorder,
            itemBuilder: (context, index) {
              final s = _steps[index];
              return _StepCard(
                key: ValueKey(s.id),
                index: index,
                step: s,
                entry: _byType[s.type],
                onToggle: (v) {
                  setState(() => s.enabled = v);
                  _emit();
                },
                onDelete: () => _removeStep(index),
                onMiscChanged: (name, value) {
                  setState(() => s.misc[name] = value);
                  _emit();
                },
              );
            },
          ),
      ],
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({
    super.key,
    required this.index,
    required this.step,
    required this.entry,
    required this.onToggle,
    required this.onDelete,
    required this.onMiscChanged,
  });

  final int index;
  final _StepState step;
  final TransformCatalogEntry? entry;
  final ValueChanged<bool> onToggle;
  final VoidCallback onDelete;
  final void Function(String name, dynamic value) onMiscChanged;

  @override
  Widget build(BuildContext context) {
    final e = entry;
    final accent = _categoryColor(e?.category ?? 'values');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: context.border),
          color: context.cs.surface,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: context.border)),
              ),
              child: Row(
                children: [
                  ReorderableDragStartListener(
                    index: index,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: Icon(Icons.drag_indicator,
                          size: 18, color: context.muted),
                    ),
                  ),
                  Container(
                    width: 22,
                    height: 22,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: accent.withOpacity(0.14),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text('${index + 1}',
                        style: TextStyle(
                            fontFamily: 'JetBrainsMono',
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: accent)),
                  ),
                  const SizedBox(width: 8),
                  Icon(_categoryIcon(e?.category ?? 'values'),
                      size: 14, color: accent),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      e?.label ?? step.type,
                      style: context.th.textTheme.titleSmall?.copyWith(
                        color: step.enabled ? null : context.muted,
                      ),
                    ),
                  ),
                  Tooltip(
                    message: step.enabled ? 'Enabled' : 'Disabled (skipped)',
                    child: Transform.scale(
                      scale: 0.8,
                      child: Switch(value: step.enabled, onChanged: onToggle),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Remove step',
                    icon: const Icon(Icons.delete_outline, size: 17),
                    onPressed: onDelete,
                  ),
                ],
              ),
            ),
            // Body
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (e != null && e.description.isNotEmpty) ...[
                    Text(e.description, style: context.th.textTheme.bodySmall),
                    const SizedBox(height: 10),
                  ],
                  if (e == null)
                    Text('Unknown transform "${step.type}". '
                        'Update the app to edit this step.',
                        style: context.th.textTheme.bodySmall)
                  else
                    ...[
                      for (final f in e.fields) ...[
                        _FieldInput(
                          field: f,
                          controller: step.controllers[f.name],
                          miscValue: step.misc[f.name],
                          onMiscChanged: (v) => onMiscChanged(f.name, v),
                        ),
                        const SizedBox(height: 10),
                      ],
                    ],
                  if (e?.example != null && e!.example!.trim().isNotEmpty)
                    _ExampleBlock(
                      example: e.example!,
                      codeController: _firstCodeController(e, step),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  TextEditingController? _firstCodeController(
      TransformCatalogEntry e, _StepState step) {
    for (final f in e.fields) {
      if (f.type == 'code') return step.controllers[f.name];
    }
    return null;
  }
}

class _FieldInput extends StatelessWidget {
  const _FieldInput({
    required this.field,
    required this.controller,
    required this.miscValue,
    required this.onMiscChanged,
  });

  final TransformFieldSpec field;
  final TextEditingController? controller;
  final dynamic miscValue;
  final ValueChanged<dynamic> onMiscChanged;

  @override
  Widget build(BuildContext context) {
    switch (field.type) {
      case 'boolean':
        return Row(
          children: [
            Transform.scale(
              scale: 0.8,
              child: Switch(
                value: miscValue == true,
                onChanged: (v) => onMiscChanged(v),
              ),
            ),
            const SizedBox(width: 6),
            Text(field.label, style: context.th.textTheme.bodyMedium),
          ],
        );
      case 'select':
        final value = miscValue?.toString();
        return DropdownButtonFormField<String>(
          value: (field.options ?? const []).contains(value) ? value : null,
          decoration: InputDecoration(
            labelText: field.label.toUpperCase(),
            helperText: field.help,
          ),
          items: (field.options ?? const [])
              .map((o) => DropdownMenuItem(value: o, child: Text(o)))
              .toList(),
          onChanged: (v) => onMiscChanged(v),
        );
      case 'code':
        return TextField(
          controller: controller,
          minLines: 3,
          maxLines: 10,
          keyboardType: TextInputType.multiline,
          style: const TextStyle(
              fontFamily: 'JetBrainsMono', fontSize: 12.5, height: 1.4),
          decoration: InputDecoration(
            labelText: field.label.toUpperCase(),
            helperText: field.help,
            helperMaxLines: 3,
            hintText: field.placeholder,
            hintStyle: const TextStyle(
                fontFamily: 'JetBrainsMono', fontSize: 12),
            alignLabelWithHint: true,
          ),
        );
      default: // string | text | columns
        return TextField(
          controller: controller,
          minLines: field.type == 'text' ? 2 : 1,
          maxLines: field.type == 'text' ? 4 : 1,
          decoration: InputDecoration(
            labelText: field.label.toUpperCase(),
            helperText: field.help,
            hintText: field.placeholder,
          ),
        );
    }
  }
}

class _ExampleBlock extends StatelessWidget {
  const _ExampleBlock({required this.example, required this.codeController});
  final String example;
  final TextEditingController? codeController;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: context.th.copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: EdgeInsets.zero,
        childrenPadding: EdgeInsets.zero,
        dense: true,
        leading: const Icon(Icons.lightbulb_outline, size: 16),
        title: Text('Examples', style: context.th.textTheme.titleSmall),
        children: [
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(top: 4),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: BifrostColors.zinc950,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SelectableText(
                  example,
                  style: const TextStyle(
                    fontFamily: 'JetBrainsMono',
                    fontSize: 12,
                    height: 1.5,
                    color: Color(0xFFDDDDDD),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (codeController != null)
                      TextButton.icon(
                        onPressed: () {
                          codeController!.text = example;
                        },
                        icon: const Icon(Icons.input, size: 14),
                        label: const Text('Insert into editor'),
                      ),
                    TextButton.icon(
                      onPressed: () => Clipboard.setData(
                          ClipboardData(text: example)),
                      icon: const Icon(Icons.copy, size: 14),
                      label: const Text('Copy'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TransformPicker extends StatelessWidget {
  const _TransformPicker({required this.catalog});
  final List<TransformCatalogEntry> catalog;

  @override
  Widget build(BuildContext context) {
    const order = ['schema', 'values', 'python', 'rows'];
    const titles = {
      'schema': 'Schema — columns & shape',
      'values': 'Values — clean & convert',
      'python': 'Python — custom logic',
      'rows': 'Rows — filtering',
    };
    final grouped = <String, List<TransformCatalogEntry>>{};
    for (final e in catalog) {
      grouped.putIfAbsent(e.category, () => []).add(e);
    }
    final cats = [
      ...order.where(grouped.containsKey),
      ...grouped.keys.where((k) => !order.contains(k)),
    ];

    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.7),
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            Text('Add a transformation',
                style: context.th.textTheme.titleLarge),
            const SizedBox(height: 12),
            for (final cat in cats) ...[
              Padding(
                padding: const EdgeInsets.only(top: 8, bottom: 6),
                child: Text(titles[cat] ?? cat.toUpperCase(),
                    style: context.th.textTheme.labelMedium),
              ),
              for (final e in grouped[cat]!)
                ListTile(
                  dense: true,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 8),
                  leading: Icon(_categoryIcon(e.category),
                      size: 18, color: _categoryColor(e.category)),
                  title: Text(e.label, style: context.th.textTheme.titleSmall),
                  subtitle: Text(e.description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.th.textTheme.bodySmall),
                  onTap: () => Navigator.of(context).pop(e.type),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

Color _categoryColor(String category) {
  switch (category) {
    case 'schema':
      return BifrostColors.blue;
    case 'python':
      return BifrostColors.purple;
    case 'rows':
      return BifrostColors.amberFg;
    default:
      return BifrostColors.emerald;
  }
}

IconData _categoryIcon(String category) {
  switch (category) {
    case 'schema':
      return Icons.view_column_outlined;
    case 'python':
      return Icons.code;
    case 'rows':
      return Icons.filter_alt_outlined;
    default:
      return Icons.tune;
  }
}
