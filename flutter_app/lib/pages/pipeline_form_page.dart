import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../widgets/ui/bifrost_button.dart';

class PipelineFormPage extends ConsumerStatefulWidget {
  const PipelineFormPage({super.key, this.id});
  final String? id;
  @override
  ConsumerState<PipelineFormPage> createState() => _PipelineFormPageState();
}

class _PipelineFormPageState extends ConsumerState<PipelineFormPage> {
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _sourceObject = TextEditingController();
  final _destObject = TextEditingController();
  final _schedule = TextEditingController();
  final _incremental = TextEditingController();
  String? _sourceConnectionId;
  String? _destConnectionId;
  String _mode = 'full';
  bool _enabled = true;
  final List<FieldMapping> _mappings = [];
  bool _saving = false;
  String? _error;

  bool get _isEdit => widget.id != null;

  @override
  void initState() {
    super.initState();
    if (_isEdit) {
      Future.microtask(() async {
        final p = await ref.read(apiClientProvider).pipeline(widget.id!);
        if (!mounted) return;
        _name.text = p.name;
        _description.text = p.description ?? '';
        _sourceObject.text = p.sourceObject;
        _destObject.text = p.destinationObject;
        _schedule.text = p.schedule ?? '';
        _incremental.text = p.incrementalField ?? '';
        _sourceConnectionId = p.sourceConnectionId;
        _destConnectionId = p.destinationConnectionId;
        _mode = p.mode;
        _enabled = p.enabled;
        _mappings
          ..clear()
          ..addAll(p.fieldMappings);
        setState(() {});
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final connections = ref.watch(connectionsProvider);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: connections.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (all) {
          final sources = all.where((c) => c.role == 'source').toList();
          final destinations =
              all.where((c) => c.role == 'destination').toList();
          return ListView(
            children: [
              TextButton.icon(
                onPressed: () => context.go('/pipelines'),
                icon: const Icon(Icons.arrow_back, size: 14),
                label: const Text('Back'),
              ),
              const SizedBox(height: 8),
              Text(_isEdit ? 'Edit pipeline' : 'New pipeline',
                  style: context.th.textTheme.titleLarge),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Overview', style: context.th.textTheme.titleSmall),
                      const SizedBox(height: 12),
                      TextField(
                          controller: _name,
                          decoration:
                              const InputDecoration(labelText: 'NAME')),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _description,
                        maxLines: 2,
                        decoration:
                            const InputDecoration(labelText: 'DESCRIPTION'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Source & destination',
                          style: context.th.textTheme.titleSmall),
                      const SizedBox(height: 12),
                      _connectionDropdown(
                          label: 'SOURCE CONNECTION',
                          value: _sourceConnectionId,
                          items: sources,
                          onChanged: (v) =>
                              setState(() => _sourceConnectionId = v)),
                      const SizedBox(height: 10),
                      TextField(
                          controller: _sourceObject,
                          decoration: const InputDecoration(
                              labelText: 'SOURCE OBJECT',
                              helperText:
                                  'Table name, entity set, or query identifier')),
                      const SizedBox(height: 16),
                      _connectionDropdown(
                          label: 'DESTINATION CONNECTION',
                          value: _destConnectionId,
                          items: destinations,
                          onChanged: (v) =>
                              setState(() => _destConnectionId = v)),
                      const SizedBox(height: 10),
                      TextField(
                          controller: _destObject,
                          decoration: const InputDecoration(
                              labelText: 'DESTINATION OBJECT')),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Settings', style: context.th.textTheme.titleSmall),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        value: _mode,
                        decoration:
                            const InputDecoration(labelText: 'MODE'),
                        items: const [
                          DropdownMenuItem(
                              value: 'full', child: Text('Full refresh')),
                          DropdownMenuItem(
                              value: 'incremental',
                              child: Text('Incremental (append)')),
                          DropdownMenuItem(
                              value: 'upsert', child: Text('Upsert by key')),
                        ],
                        onChanged: (v) => setState(() => _mode = v ?? 'full'),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _incremental,
                        decoration: const InputDecoration(
                          labelText: 'INCREMENTAL FIELD',
                          helperText:
                              'Source field used as the high-watermark (incremental/upsert modes)',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _schedule,
                        decoration: const InputDecoration(
                          labelText: 'SCHEDULE (CRON)',
                          helperText: 'e.g. `0 */4 * * *` — leave blank for manual',
                        ),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Switch(
                              value: _enabled,
                              onChanged: (v) => setState(() => _enabled = v)),
                          const SizedBox(width: 8),
                          const Text('Enabled'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('Field mappings',
                              style: context.th.textTheme.titleSmall),
                          const Spacer(),
                          OutlinedButton.icon(
                            onPressed: () => setState(() => _mappings.add(
                                FieldMapping(source: '', destination: ''))),
                            icon: const Icon(Icons.add, size: 13),
                            label: const Text('Add mapping'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Empty list = pass through all source fields. Supported transforms: upper, lower, trim.',
                        style: context.th.textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      for (var i = 0; i < _mappings.length; i++)
                        _mappingRow(i),
                    ],
                  ),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!,
                    style: const TextStyle(color: Color(0xFFBE123C))),
              ],
              const SizedBox(height: 16),
              Row(
                children: [
                  OutlinedButton(
                    onPressed: () => context.go('/pipelines'),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  BifrostButton(
                    onPressed: _saving ? null : _submit,
                    label: _isEdit ? 'Save changes' : 'Create pipeline',
                    icon: Icons.check,
                  ),
                ],
              ),
              const SizedBox(height: 32),
            ],
          );
        },
      ),
    );
  }

  Widget _mappingRow(int i) {
    final m = _mappings[i];
    final srcCtrl = TextEditingController(text: m.source);
    final dstCtrl = TextEditingController(text: m.destination);
    final transformCtrl = TextEditingController(text: m.transform ?? '');
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: srcCtrl,
              decoration: const InputDecoration(labelText: 'SOURCE'),
              onChanged: (v) => _mappings[i] = FieldMapping(
                  source: v, destination: m.destination, transform: m.transform),
            ),
          ),
          const SizedBox(width: 6),
          const Icon(Icons.arrow_forward, size: 14),
          const SizedBox(width: 6),
          Expanded(
            child: TextField(
              controller: dstCtrl,
              decoration: const InputDecoration(labelText: 'DESTINATION'),
              onChanged: (v) => _mappings[i] = FieldMapping(
                  source: m.source, destination: v, transform: m.transform),
            ),
          ),
          const SizedBox(width: 6),
          SizedBox(
            width: 110,
            child: TextField(
              controller: transformCtrl,
              decoration: const InputDecoration(labelText: 'TRANSFORM'),
              onChanged: (v) => _mappings[i] = FieldMapping(
                  source: m.source,
                  destination: m.destination,
                  transform: v.isEmpty ? null : v),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, size: 16),
            onPressed: () => setState(() => _mappings.removeAt(i)),
          ),
        ],
      ),
    );
  }

  Widget _connectionDropdown({
    required String label,
    required String? value,
    required List<Connection> items,
    required ValueChanged<String?> onChanged,
  }) {
    return DropdownButtonFormField<String>(
      value: value,
      decoration: InputDecoration(labelText: label),
      items: items
          .map((c) =>
              DropdownMenuItem(value: c.id, child: Text('${c.name} · ${c.connectorType}')))
          .toList(),
      onChanged: onChanged,
    );
  }

  Future<void> _submit() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    final body = <String, dynamic>{
      'name': _name.text.trim(),
      'description': _description.text.trim(),
      'source_connection_id': _sourceConnectionId,
      'source_object': _sourceObject.text.trim(),
      'destination_connection_id': _destConnectionId,
      'destination_object': _destObject.text.trim(),
      'mode': _mode,
      'enabled': _enabled,
      'schedule': _schedule.text.trim().isEmpty ? null : _schedule.text.trim(),
      'incremental_field':
          _incremental.text.trim().isEmpty ? null : _incremental.text.trim(),
      'field_mappings':
          _mappings.where((m) => m.source.isNotEmpty).map((m) => m.toJson()).toList(),
    };
    try {
      final api = ref.read(apiClientProvider);
      if (_isEdit) {
        await api.updatePipeline(widget.id!, body);
      } else {
        await api.createPipeline(body);
      }
      ref.invalidate(pipelinesProvider);
      if (mounted) context.go('/pipelines');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}
