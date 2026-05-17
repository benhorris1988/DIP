import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../providers/data_providers.dart';
import '../theme/app_theme.dart';
import '../widgets/ui/bifrost_button.dart';
import '../widgets/ui/connector_icon.dart';

class ConnectionFormPage extends ConsumerStatefulWidget {
  const ConnectionFormPage({super.key, this.id});
  final String? id;

  @override
  ConsumerState<ConnectionFormPage> createState() => _ConnectionFormPageState();
}

class _ConnectionFormPageState extends ConsumerState<ConnectionFormPage> {
  final _name = TextEditingController();
  final _description = TextEditingController();
  String _role = 'source';
  String? _connectorType;
  final Map<String, TextEditingController> _config = {};
  final Map<String, TextEditingController> _credentials = {};
  bool _saving = false;
  String? _error;

  bool get _isEdit => widget.id != null;

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    for (final c in _config.values) c.dispose();
    for (final c in _credentials.values) c.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    if (_isEdit) {
      Future.microtask(() async {
        final c = await ref.read(apiClientProvider).connection(widget.id!);
        if (!mounted) return;
        _name.text = c.name;
        _description.text = c.description ?? '';
        _role = c.role;
        _connectorType = c.connectorType;
        c.config.forEach((k, v) {
          _config[k] = TextEditingController(text: v?.toString() ?? '');
        });
        setState(() {});
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final connectors = ref.watch(connectorsProvider);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: connectors.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (all) {
          final byRole = all.where((c) => c.role == _role).toList();
          final selected =
              all.where((c) => c.type == _connectorType).firstOrNull;
          return ListView(
            children: [
              TextButton.icon(
                onPressed: () => context.go('/connections'),
                icon: const Icon(Icons.arrow_back, size: 14),
                label: const Text('Back'),
              ),
              const SizedBox(height: 8),
              Text(_isEdit ? 'Edit connection' : 'New connection',
                  style: context.th.textTheme.titleLarge),
              const SizedBox(height: 4),
              Text(
                  'Pick a connector type and provide its config + credentials.',
                  style: context.th.textTheme.bodySmall),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Role', style: context.th.textTheme.titleSmall),
                      const SizedBox(height: 10),
                      Row(
                        children: ['source', 'destination'].map((r) {
                          final on = _role == r;
                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              label: Text(r),
                              selected: on,
                              onSelected: (_) {
                                setState(() {
                                  _role = r;
                                  _connectorType = null;
                                  _config.clear();
                                  _credentials.clear();
                                });
                              },
                            ),
                          );
                        }).toList(),
                      ),
                      const SizedBox(height: 18),
                      Text('Connector type',
                          style: context.th.textTheme.titleSmall),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: byRole
                            .map((c) => _ConnectorTile(
                                  metadata: c,
                                  selected: c.type == _connectorType,
                                  onTap: () {
                                    setState(() {
                                      _connectorType = c.type;
                                      _config.clear();
                                      _credentials.clear();
                                      for (final f in c.configFields) {
                                        _config[f.name] = TextEditingController(
                                            text:
                                                f.defaultValue?.toString() ?? '');
                                      }
                                      for (final f in c.credentialFields) {
                                        _credentials[f.name] =
                                            TextEditingController();
                                      }
                                    });
                                  },
                                ))
                            .toList(),
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
                      Text('Details', style: context.th.textTheme.titleSmall),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _name,
                        decoration: const InputDecoration(labelText: 'NAME'),
                      ),
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
              if (selected != null) ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Configuration',
                            style: context.th.textTheme.titleSmall),
                        const SizedBox(height: 12),
                        for (final f in selected.configFields)
                          _fieldFor(f, _config),
                      ],
                    ),
                  ),
                ),
                if (selected.credentialFields.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Credentials',
                              style: context.th.textTheme.titleSmall),
                          const SizedBox(height: 4),
                          if (_isEdit)
                            Text(
                                'Leave blank to keep existing credentials unchanged.',
                                style: context.th.textTheme.bodySmall),
                          const SizedBox(height: 12),
                          for (final f in selected.credentialFields)
                            _fieldFor(f, _credentials),
                        ],
                      ),
                    ),
                  ),
                ],
              ],
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!,
                    style: const TextStyle(color: Color(0xFFBE123C))),
              ],
              const SizedBox(height: 16),
              Row(
                children: [
                  OutlinedButton(
                    onPressed: () => context.go('/connections'),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  BifrostButton(
                    onPressed:
                        _saving || _connectorType == null ? null : _submit,
                    label: _isEdit ? 'Save changes' : 'Create connection',
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

  Widget _fieldFor(ConfigField f, Map<String, TextEditingController> bag) {
    final ctrl = bag.putIfAbsent(f.name, () => TextEditingController());
    if (f.type == 'boolean') {
      final on = ctrl.text == 'true';
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          children: [
            Switch(
              value: on,
              onChanged: (v) => setState(() => ctrl.text = v ? 'true' : 'false'),
            ),
            const SizedBox(width: 8),
            Text(f.label),
            if (f.helpText != null) ...[
              const SizedBox(width: 8),
              Expanded(
                child: Text(f.helpText!,
                    style: context.th.textTheme.bodySmall),
              ),
            ],
          ],
        ),
      );
    }
    if (f.options != null) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: DropdownButtonFormField<String>(
          value: f.options!.contains(ctrl.text) ? ctrl.text : null,
          decoration: InputDecoration(labelText: f.label.toUpperCase()),
          items: f.options!
              .map((o) => DropdownMenuItem(value: o, child: Text(o)))
              .toList(),
          onChanged: (v) => ctrl.text = v ?? '',
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: ctrl,
        obscureText: f.secret,
        keyboardType: f.type == 'integer' ? TextInputType.number : null,
        decoration: InputDecoration(
          labelText: f.label.toUpperCase(),
          helperText: f.helpText,
        ),
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    final config = <String, dynamic>{};
    _config.forEach((k, v) {
      if (v.text.isEmpty) return;
      if (v.text == 'true') config[k] = true;
      else if (v.text == 'false') config[k] = false;
      else config[k] = v.text;
    });
    final credentials = <String, dynamic>{};
    _credentials.forEach((k, v) {
      if (v.text.isNotEmpty) credentials[k] = v.text;
    });
    final body = <String, dynamic>{
      'name': _name.text.trim(),
      'description': _description.text.trim(),
      'connector_type': _connectorType,
      'role': _role,
      'config': config,
      if (credentials.isNotEmpty) 'credentials': credentials,
    };
    try {
      final api = ref.read(apiClientProvider);
      if (_isEdit) {
        await api.updateConnection(widget.id!, body);
      } else {
        await api.createConnection(body);
      }
      ref.invalidate(connectionsProvider);
      if (mounted) context.go('/connections');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}

class _ConnectorTile extends StatelessWidget {
  const _ConnectorTile({
    required this.metadata,
    required this.selected,
    required this.onTap,
  });
  final ConnectorMetadata metadata;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        width: 260,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: selected
              ? const Color(0x14C4B5FD)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected
                ? const Color(0xFF7C3AED)
                : context.border,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            ConnectorIcon(icon: metadata.icon),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(metadata.label,
                      style: context.th.textTheme.titleSmall),
                  Text(metadata.description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.th.textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
