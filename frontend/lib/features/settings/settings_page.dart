import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/state.dart';

/// Settings page for app configuration.
class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  late TextEditingController _baseUrlController;
  bool? _connectionOk;
  String? _connectionError;

  @override
  void initState() {
    super.initState();
    _baseUrlController = TextEditingController();
  }

  @override
  void dispose() {
    _baseUrlController.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() {
      _connectionOk = null;
      _connectionError = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      await client.getHealth();
      if (mounted) {
        setState(() => _connectionOk = true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _connectionOk = false;
          _connectionError = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final baseUrl = ref.watch(baseUrlProvider);
    final attachmentMaxMb = ref.watch(attachmentMaxMbProvider);
    final layoutMode = ref.watch(layoutModeProvider);
    final layoutType = ref.watch(layoutTypeProvider);
    final frontendVersionAsync = ref.watch(frontendVersionProvider);
    final backendVersionAsync = ref.watch(backendVersionProvider);

    // Update controller if base URL changed
    if (_baseUrlController.text != baseUrl) {
      _baseUrlController.text = baseUrl;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // API Configuration
          Text(
            'API Configuration',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _baseUrlController,
            decoration: const InputDecoration(
              labelText: 'API Base URL',
              hintText: '/api (hosted) or http://localhost:8080 (local)',
              prefixIcon: Icon(Icons.link),
            ),
            onSubmitted: (value) async {
              ref.read(baseUrlProvider.notifier).state = value;
              final prefs = ref.read(sharedPreferencesProvider);
              await prefs.setString('base_url', value);
              if (!context.mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('API URL updated')),
              );
            },
          ),
          const SizedBox(height: 8),
          Text(
            'Press enter to save. The app will use this URL for all API requests.',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 32),

          // Attachments
          Text('Attachments', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Slider(
                  value: attachmentMaxMb.clamp(1.0, 50.0),
                  min: 1.0,
                  max: 50.0,
                  divisions: 49,
                  label: '${attachmentMaxMb.toStringAsFixed(0)} MB',
                  onChanged: (value) async {
                    ref.read(attachmentMaxMbProvider.notifier).state = value;
                    final prefs = ref.read(sharedPreferencesProvider);
                    await prefs.setDouble('attachment_max_mb', value);
                    if (mounted) {
                      setState(() {});
                    }
                  },
                ),
              ),
              const SizedBox(width: 8),
              Text('${attachmentMaxMb.toStringAsFixed(0)} MB'),
            ],
          ),
          Text(
            'Maximum total size for image attachments per message.',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 32),
          Text('Connection', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _testConnection,
                icon: const Icon(Icons.wifi_tethering),
                label: const Text('Test Connection'),
              ),
              const SizedBox(width: 12),
              if (_connectionOk == true)
                const Icon(Icons.check_circle, color: Colors.green)
              else if (_connectionOk == false)
                const Icon(Icons.error_outline, color: Colors.red),
            ],
          ),
          if (_connectionOk == false && _connectionError != null) ...[
            const SizedBox(height: 8),
            Text(
              _connectionError!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.red.shade400,
              ),
            ),
          ],
          const SizedBox(height: 32),

          // Layout Settings
          Text('Layout', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          SegmentedButton<LayoutMode>(
            segments: const [
              ButtonSegment(
                value: LayoutMode.auto,
                label: Text('Auto'),
                icon: Icon(Icons.auto_mode),
              ),
              ButtonSegment(
                value: LayoutMode.locked,
                label: Text('Locked'),
                icon: Icon(Icons.lock),
              ),
              ButtonSegment(
                value: LayoutMode.manual,
                label: Text('Manual'),
                icon: Icon(Icons.tune),
              ),
            ],
            selected: {layoutMode},
            onSelectionChanged: (selected) async {
              final mode = selected.first;
              ref.read(layoutModeProvider.notifier).state = mode;
              final prefs = ref.read(sharedPreferencesProvider);
              await prefs.setString('layout_mode', mode.name);
            },
          ),
          const SizedBox(height: 16),
          if (layoutMode == LayoutMode.locked ||
              layoutMode == LayoutMode.manual)
            SegmentedButton<LayoutType>(
              segments: const [
                ButtonSegment(
                  value: LayoutType.chat,
                  label: Text('Chat'),
                  icon: Icon(Icons.chat_bubble_outline),
                ),
                ButtonSegment(
                  value: LayoutType.studio,
                  label: Text('Studio'),
                  icon: Icon(Icons.dashboard),
                ),
                ButtonSegment(
                  value: LayoutType.compact,
                  label: Text('Compact'),
                  icon: Icon(Icons.phone_android),
                ),
              ],
              selected: {layoutType},
              onSelectionChanged: (selected) async {
                final type = selected.first;
                ref.read(layoutTypeProvider.notifier).state = type;
                final prefs = ref.read(sharedPreferencesProvider);
                await prefs.setString('locked_layout', type.name);
              },
            ),
          const SizedBox(height: 8),
          Text(
            layoutMode == LayoutMode.auto
                ? 'Layout automatically adjusts based on the selected model modality.'
                : layoutMode == LayoutMode.locked
                ? 'Layout is locked to your selection.'
                : 'You can manually switch layouts.',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 32),

          // About
          Text('About', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.info_outline),
              title: const Text('PlugAI'),
              subtitle: Text(
                frontendVersionAsync.when(
                  data: (version) => 'Frontend $version',
                  loading: () => 'Frontend loading...',
                  error: (_, __) => 'Frontend unknown',
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: const Icon(Icons.code),
              title: const Text('Pluggably LLM API Gateway'),
              subtitle: Text(
                backendVersionAsync.when(
                  data: (info) => 'Backend ${info.version}',
                  loading: () => 'Backend loading...',
                  error: (_, __) => 'Backend unavailable',
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
