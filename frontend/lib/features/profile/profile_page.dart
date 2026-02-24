import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/state.dart';
import '../../utils/error_helpers.dart';

/// Profile page for user preferences.
class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userProfileAsync = ref.watch(userProfileProvider);
    final isLoggedIn = ref.watch(isLoggedInProvider);
    final providerKeysAsync = ref.watch(providerKeysProvider);

    if (!isLoggedIn) {
      return Scaffold(
        appBar: AppBar(title: const Text('Profile')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.person_outline, size: 64, color: Colors.grey.shade400),
              const SizedBox(height: 16),
              Text(
                'Sign in to view your profile',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(color: Colors.grey.shade600),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => context.go('/login'),
                icon: const Icon(Icons.login),
                label: const Text('Sign In'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () async {
              final client = ref.read(apiClientProvider);
              try {
                await client.logout();
              } catch (_) {
                // Ignore logout errors
              }
              ref.read(authTokenProvider.notifier).state = null;
              final prefs = ref.read(sharedPreferencesProvider);
              await prefs.remove('auth_token');
              if (context.mounted) {
                context.go('/login');
              }
            },
          ),
        ],
      ),
      body: userProfileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
              const SizedBox(height: 16),
              Text('Failed to load profile: $error'),
              const SizedBox(height: 16),
              FilledButton.tonal(
                onPressed: () => ref.invalidate(userProfileProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (profile) {
          if (profile == null) {
            return const Center(child: Text('No profile data'));
          }

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Profile header
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 48,
                        backgroundColor: Theme.of(context).colorScheme.primary,
                        child: Text(
                          profile.username.substring(0, 1).toUpperCase(),
                          style: const TextStyle(
                            fontSize: 32,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        profile.username,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Member since ${_formatDate(profile.createdAt)}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Provider credentials
              Text(
                'Provider API Keys',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 4),
              Text(
                'Add API keys for commercial LLM providers to access their models.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
              ),
              const SizedBox(height: 12),
              providerKeysAsync.when(
                loading: () => const LinearProgressIndicator(),
                error: (error, _) => Text(
                  'Failed to load credentials: ${friendlyError(error)}',
                  style: TextStyle(color: Colors.red.shade400),
                ),
                data: (keys) => _ProviderKeyCards(existingKeys: keys),
              ),
              const SizedBox(height: 24),

              // Quick actions
              Text(
                'Quick Actions',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 16),
              _ActionCard(
                icon: Icons.vpn_key_outlined,
                title: 'API Tokens',
                subtitle: 'Manage your personal API tokens',
                onTap: () => context.go('/tokens'),
              ),
              const SizedBox(height: 8),
              _ActionCard(
                icon: Icons.key_outlined,
                title: 'Provider Keys',
                subtitle: 'Manage API keys for external providers',
                onTap: () => context.go('/keys'),
              ),
              const SizedBox(height: 8),
              _ActionCard(
                icon: Icons.settings_outlined,
                title: 'Settings',
                subtitle: 'Configure app settings',
                onTap: () => context.go('/settings'),
              ),
            ],
          );
        },
      ),
    );
  }

  String _formatDate(DateTime? date) {
    if (date == null) {
      return 'Unknown';
    }
    return '${date.month}/${date.day}/${date.year}';
  }
}

// ==================== Provider Key Cards ====================

/// Known commercial LLM providers with metadata.
class _ProviderMeta {
  final String id;
  final String name;
  final Color color;
  final IconData icon;
  final String credentialType; // default credential type
  final String keyHint;
  final bool needsEndpoint; // e.g., Azure

  const _ProviderMeta({
    required this.id,
    required this.name,
    required this.color,
    required this.icon,
    this.credentialType = 'api_key',
    this.keyHint = 'sk-...',
    this.needsEndpoint = false,
  });
}

const _providers = [
  _ProviderMeta(
    id: 'openai',
    name: 'OpenAI',
    color: Color(0xFF00A67E),
    icon: Icons.auto_awesome,
    keyHint: 'sk-...',
  ),
  _ProviderMeta(
    id: 'anthropic',
    name: 'Anthropic',
    color: Color(0xFFD4A27F),
    icon: Icons.psychology,
    keyHint: 'sk-ant-...',
  ),
  _ProviderMeta(
    id: 'google',
    name: 'Google AI',
    color: Color(0xFF4285F4),
    icon: Icons.cloud,
    keyHint: 'AIza...',
  ),
  _ProviderMeta(
    id: 'xai',
    name: 'xAI',
    color: Color(0xFF1DA1F2),
    icon: Icons.rocket_launch,
    keyHint: 'xai-...',
  ),
  _ProviderMeta(
    id: 'azure',
    name: 'Azure OpenAI',
    color: Color(0xFF0078D4),
    icon: Icons.cloud_queue,
    credentialType: 'endpoint_key',
    keyHint: 'your-api-key',
    needsEndpoint: true,
  ),
  _ProviderMeta(
    id: 'huggingface',
    name: 'Hugging Face',
    color: Color(0xFFFFD21E),
    icon: Icons.emoji_nature,
    keyHint: 'hf_...',
  ),
];

/// Displays a card for each known provider showing existing key status
/// or an input form to add one.
class _ProviderKeyCards extends ConsumerStatefulWidget {
  final List<dynamic> existingKeys;

  const _ProviderKeyCards({required this.existingKeys});

  @override
  ConsumerState<_ProviderKeyCards> createState() => _ProviderKeyCardsState();
}

class _ProviderKeyCardsState extends ConsumerState<_ProviderKeyCards> {
  /// Which provider card is currently in "edit" mode (showing the form).
  String? _editingProvider;

  Map<String, dynamic> _keysByProvider() {
    final map = <String, dynamic>{};
    for (final key in widget.existingKeys) {
      map[key.provider] = key;
    }
    return map;
  }

  @override
  Widget build(BuildContext context) {
    final byProvider = _keysByProvider();

    return Column(
      children: [
        for (final meta in _providers) ...[
          _ProviderKeyCard(
            meta: meta,
            existingKey: byProvider[meta.id],
            isEditing: _editingProvider == meta.id,
            onEdit: () => setState(() {
              _editingProvider = _editingProvider == meta.id ? null : meta.id;
            }),
            onSaved: () => setState(() => _editingProvider = null),
          ),
          const SizedBox(height: 8),
        ],
      ],
    );
  }
}

class _ProviderKeyCard extends ConsumerStatefulWidget {
  final _ProviderMeta meta;
  final dynamic existingKey;
  final bool isEditing;
  final VoidCallback onEdit;
  final VoidCallback onSaved;

  const _ProviderKeyCard({
    required this.meta,
    required this.existingKey,
    required this.isEditing,
    required this.onEdit,
    required this.onSaved,
  });

  @override
  ConsumerState<_ProviderKeyCard> createState() => _ProviderKeyCardState();
}

class _ProviderKeyCardState extends ConsumerState<_ProviderKeyCard> {
  final _keyController = TextEditingController();
  final _endpointController = TextEditingController();
  bool _saving = false;
  bool _obscure = true;

  @override
  void dispose() {
    _keyController.dispose();
    _endpointController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_keyController.text.trim().isEmpty) return;
    setState(() => _saving = true);

    try {
      final client = ref.read(apiClientProvider);
      await client.addProviderKey(
        provider: widget.meta.id,
        credentialType: widget.meta.credentialType,
        apiKey: _keyController.text.trim(),
        endpoint: widget.meta.needsEndpoint
            ? _endpointController.text.trim()
            : null,
      );
      _keyController.clear();
      _endpointController.clear();
      ref.invalidate(providerKeysProvider);
      ref.invalidate(modelsProvider);
      if (mounted) {
        showSuccessSnackBar(context, '${widget.meta.name} key saved');
        widget.onSaved();
      }
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'Failed to save key', e);
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _remove() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Remove ${widget.meta.name} Key'),
        content: const Text('This will delete your stored credential.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      final client = ref.read(apiClientProvider);
      await client.removeProviderKey(widget.meta.id);
      ref.invalidate(providerKeysProvider);
      ref.invalidate(modelsProvider);
      if (mounted) {
        showSuccessSnackBar(context, '${widget.meta.name} key removed');
      }
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'Failed to remove key', e);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasKey = widget.existingKey != null;
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                CircleAvatar(
                  radius: 16,
                  backgroundColor: widget.meta.color,
                  child: Icon(widget.meta.icon, size: 16, color: Colors.white),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.meta.name, style: theme.textTheme.titleSmall),
                      if (hasKey)
                        Text(
                          widget.existingKey.maskedKey ?? 'Configured',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: Colors.green.shade700,
                          ),
                        )
                      else
                        Text(
                          'Not configured',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: Colors.grey.shade500,
                          ),
                        ),
                    ],
                  ),
                ),
                if (hasKey)
                  IconButton(
                    icon: Icon(
                      Icons.delete_outline,
                      color: Colors.red.shade400,
                      size: 20,
                    ),
                    tooltip: 'Remove',
                    onPressed: _remove,
                  ),
                IconButton(
                  icon: Icon(
                    widget.isEditing
                        ? Icons.expand_less
                        : (hasKey ? Icons.edit : Icons.add),
                    size: 20,
                  ),
                  tooltip: hasKey ? 'Update key' : 'Add key',
                  onPressed: widget.onEdit,
                ),
              ],
            ),
            // Expandable input form
            if (widget.isEditing) ...[
              const SizedBox(height: 12),
              if (widget.meta.needsEndpoint)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: TextField(
                    controller: _endpointController,
                    decoration: const InputDecoration(
                      labelText: 'Endpoint URL',
                      hintText: 'https://your-resource.openai.azure.com/',
                      isDense: true,
                    ),
                  ),
                ),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _keyController,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'API Key',
                        hintText: widget.meta.keyHint,
                        isDense: true,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscure ? Icons.visibility_off : Icons.visibility,
                            size: 18,
                          ),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _saving ? null : _save,
                    child: _saving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Save'),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
