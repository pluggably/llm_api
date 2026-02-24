import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/state.dart';
import 'package:pluggably_llm_client/sdk.dart';

/// Dynamic settings drawer for model parameters.
class SettingsDrawer extends ConsumerStatefulWidget {
  const SettingsDrawer({super.key});

  @override
  ConsumerState<SettingsDrawer> createState() => _SettingsDrawerState();
}

class _SettingsDrawerState extends ConsumerState<SettingsDrawer> {
  final Map<String, dynamic> _localValues = {};
  String? _lastLoggedSchemaId;

  @override
  Widget build(BuildContext context) {
    final schemaAsync = ref.watch(modelSchemaProvider);
    final selectedModel = ref.watch(selectedModelProvider);

    return Container(
      decoration: BoxDecoration(
        border: Border(left: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
            ),
            child: Row(
              children: [
                const Icon(Icons.tune),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Parameters',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Reset to defaults',
                  onPressed: () {
                    ref.read(parametersProvider.notifier).state = {};
                    setState(() => _localValues.clear());
                  },
                ),
              ],
            ),
          ),

          // Model info
          if (selectedModel != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 16,
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    child: const Icon(
                      Icons.auto_awesome,
                      size: 16,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          selectedModel.name,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(fontWeight: FontWeight.w600),
                        ),
                        Text(
                          selectedModel.provider,
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

          // Parameters
          Expanded(
            child: schemaAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stack) => Center(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 32,
                        color: Colors.red.shade300,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Failed to load schema',
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                      const SizedBox(height: 8),
                      TextButton(
                        onPressed: () => ref.invalidate(modelSchemaProvider),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),
              data: (schema) {
                if (schema != null && schema.modelId != _lastLoggedSchemaId) {
                  _lastLoggedSchemaId = schema.modelId;
                  final params = schema.parameters.map((key, value) {
                    return MapEntry(key, {
                      'type': value.type,
                      'minimum': value.minimum,
                      'maximum': value.maximum,
                      'default': value.defaultValue,
                    });
                  });
                  debugPrint(
                    'Schema loaded for model=${schema.modelId}: $params',
                  );
                }

                if (schema == null || schema.parameters.isEmpty) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'No configurable parameters',
                        style: TextStyle(color: Colors.grey.shade600),
                      ),
                    ),
                  );
                }

                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    for (final param in schema.parameters.entries)
                      _ParameterField(
                        param: param.value,
                        value:
                            _localValues[param.key] ?? param.value.defaultValue,
                        onChanged: (value) {
                          setState(() => _localValues[param.key] = value);
                          final current = Map<String, dynamic>.from(
                            ref.read(parametersProvider),
                          );
                          current[param.key] = value;
                          ref.read(parametersProvider.notifier).state = current;
                        },
                      ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _ParameterField extends StatelessWidget {
  final SchemaParameter param;
  final dynamic value;
  final ValueChanged<dynamic> onChanged;

  const _ParameterField({
    required this.param,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Label
          Text(
            param.title ?? param.name,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
          ),
          if (param.description != null) ...[
            const SizedBox(height: 2),
            Text(
              param.description!,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
            ),
          ],
          const SizedBox(height: 8),
          // Field
          _buildField(context),
        ],
      ),
    );
  }

  Widget _buildField(BuildContext context) {
    // Enum -> dropdown
    if (param.enumValues != null && param.enumValues!.isNotEmpty) {
      return DropdownButtonFormField<dynamic>(
        initialValue: value,
        decoration: const InputDecoration(
          isDense: true,
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
        items: param.enumValues!
            .map((e) => DropdownMenuItem(value: e, child: Text(e.toString())))
            .toList(),
        onChanged: (v) => onChanged(v),
      );
    }

    // Boolean -> switch
    if (param.type == 'boolean') {
      return Switch(value: value == true, onChanged: onChanged);
    }

    // Number with range -> slider
    final minValue = param.minimum;
    final maxValue = param.maximum;

    if ((param.type == 'number' || param.type == 'integer') &&
        minValue is num &&
        maxValue is num) {
      final currentValue = (value as num?)?.toDouble() ?? minValue.toDouble();
      return Column(
        children: [
          Slider(
            value: currentValue.clamp(
              minValue.toDouble(),
              maxValue.toDouble(),
            ),
            min: minValue.toDouble(),
            max: maxValue.toDouble(),
            divisions: param.type == 'integer'
                ? (maxValue.toInt() - minValue.toInt())
                : null,
            label: currentValue.toStringAsFixed(
              param.type == 'integer' ? 0 : 2,
            ),
            onChanged: (v) =>
                onChanged(param.type == 'integer' ? v.round() : v),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                minValue.toString(),
                style: Theme.of(context).textTheme.bodySmall,
              ),
              Text(
                currentValue.toStringAsFixed(param.type == 'integer' ? 0 : 2),
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
              ),
              Text(
                maxValue.toString(),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ],
      );
    }

    // Number without range -> text field with validation
    if (param.type == 'number' || param.type == 'integer') {
      return TextFormField(
        initialValue: value?.toString() ?? '',
        decoration: const InputDecoration(
          isDense: true,
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        ),
        keyboardType: TextInputType.number,
        onChanged: (v) {
          if (v.isEmpty) {
            onChanged(null);
          } else {
            final parsed = param.type == 'integer'
                ? int.tryParse(v)
                : double.tryParse(v);
            if (parsed != null) {
              onChanged(parsed);
            }
          }
        },
      );
    }

    // Default -> text field
    return TextFormField(
      initialValue: value?.toString() ?? '',
      decoration: const InputDecoration(
        isDense: true,
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      ),
      onChanged: onChanged,
    );
  }
}
