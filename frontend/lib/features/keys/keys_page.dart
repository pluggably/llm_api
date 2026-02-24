import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/state.dart';
import 'package:pluggably_llm_client/sdk.dart';

/// Provider and OSS keys management page.
class KeysPage extends ConsumerWidget {
  const KeysPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final keysAsync = ref.watch(providerKeysProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Provider Keys')),
      body: keysAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
              const SizedBox(height: 16),
              Text('Failed to load keys: $error'),
              const SizedBox(height: 16),
              FilledButton.tonal(
                onPressed: () => ref.invalidate(providerKeysProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (keys) {
          if (keys.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.key_outlined,
                    size: 64,
                    color: Colors.grey.shade400,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No provider keys',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.grey.shade600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Add API keys for external providers like OpenAI, Anthropic, etc.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey.shade500,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: keys.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final key = keys[index];
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: _getProviderColor(key.provider),
                    child: Text(
                      key.provider.substring(0, 1).toUpperCase(),
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                  title: Text(key.provider),
                  subtitle: Text('${key.credentialType} • ${key.maskedKey}'),
                  trailing: IconButton(
                    icon: Icon(
                      Icons.delete_outline,
                      color: Colors.red.shade400,
                    ),
                    tooltip: 'Remove',
                    onPressed: () => _removeKey(context, ref, key),
                  ),
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _addKey(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('Add Key'),
      ),
    );
  }

  Color _getProviderColor(String provider) {
    switch (provider.toLowerCase()) {
      case 'openai':
        return const Color(0xFF00A67E);
      case 'anthropic':
        return const Color(0xFFD4A27F);
      case 'google':
        return const Color(0xFF4285F4);
      case 'xai':
        return const Color(0xFF1D1D1D);
      case 'deepseek':
        return const Color(0xFF4D6BFE);
      case 'azure':
        return const Color(0xFF0078D4);
      case 'huggingface':
        return const Color(0xFFFFD21E);
      default:
        return Colors.grey;
    }
  }

  Future<void> _addKey(BuildContext context, WidgetRef ref) async {
    final providerController = TextEditingController();
    final keyController = TextEditingController();
    final endpointController = TextEditingController();
    final oauthController = TextEditingController();
    final serviceAccountController = TextEditingController();
    String credentialType = 'api_key';

    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
        title: const Text('Add Provider Key'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(labelText: 'Provider'),
              items: const [
                DropdownMenuItem(value: 'openai', child: Text('OpenAI')),
                DropdownMenuItem(value: 'anthropic', child: Text('Anthropic')),
                DropdownMenuItem(value: 'google', child: Text('Google')),
                DropdownMenuItem(value: 'xai', child: Text('xAI (Grok)')),
                DropdownMenuItem(value: 'deepseek', child: Text('DeepSeek')),
                DropdownMenuItem(value: 'azure', child: Text('Azure OpenAI')),
                DropdownMenuItem(
                  value: 'huggingface',
                  child: Text('Hugging Face'),
                ),
                DropdownMenuItem(value: 'other', child: Text('Other')),
              ],
              onChanged: (value) {
                providerController.text = value ?? '';
              },
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: credentialType,
              decoration: const InputDecoration(labelText: 'Credential Type'),
              items: const [
                DropdownMenuItem(value: 'api_key', child: Text('API Key')),
                DropdownMenuItem(
                  value: 'endpoint_key',
                  child: Text('Endpoint + Key'),
                ),
                DropdownMenuItem(
                  value: 'oauth_token',
                  child: Text('OAuth Token'),
                ),
                DropdownMenuItem(
                  value: 'service_account',
                  child: Text('Service Account JSON'),
                ),
              ],
              onChanged: (value) => setState(() {
                credentialType = value ?? 'api_key';
              }),
            ),
            const SizedBox(height: 16),
            if (credentialType == 'api_key' || credentialType == 'endpoint_key')
              TextField(
                controller: keyController,
                decoration: const InputDecoration(
                  labelText: 'API Key',
                  hintText: 'sk-...',
                ),
                obscureText: true,
              ),
            if (credentialType == 'endpoint_key')
              TextField(
                controller: endpointController,
                decoration: const InputDecoration(
                  labelText: 'Endpoint',
                ),
              ),
            if (credentialType == 'oauth_token')
              TextField(
                controller: oauthController,
                decoration: const InputDecoration(
                  labelText: 'OAuth Token',
                ),
                obscureText: true,
              ),
            if (credentialType == 'service_account')
              TextField(
                controller: serviceAccountController,
                decoration: const InputDecoration(
                  labelText: 'Service Account JSON',
                ),
                maxLines: 4,
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (providerController.text.isEmpty ||
                  (credentialType == 'api_key' && keyController.text.isEmpty) ||
                  (credentialType == 'endpoint_key' &&
                      (keyController.text.isEmpty ||
                          endpointController.text.isEmpty)) ||
                  (credentialType == 'oauth_token' &&
                      oauthController.text.isEmpty) ||
                  (credentialType == 'service_account' &&
                      serviceAccountController.text.isEmpty)) {
                return;
              }
              Navigator.of(context).pop({
                'provider': providerController.text,
                'credential_type': credentialType,
                'api_key': keyController.text,
                'endpoint': endpointController.text,
                'oauth_token': oauthController.text,
                'service_account_json': serviceAccountController.text,
              });
            },
            child: const Text('Add'),
          ),
        ],
        ),
      ),
    );

    if (result == null) return;

    try {
      final client = ref.read(apiClientProvider);
      await client.addProviderKey(
        provider: result['provider']!,
        credentialType: result['credential_type']!,
        apiKey: result['api_key'],
        endpoint: result['endpoint'],
        oauthToken: result['oauth_token'],
        serviceAccountJson: result['service_account_json'],
      );
      ref.invalidate(providerKeysProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Provider key added')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to add key: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _removeKey(
    BuildContext context,
    WidgetRef ref,
    ProviderKey key,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Key'),
        content: Text(
          'Are you sure you want to remove your ${key.provider} key?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final client = ref.read(apiClientProvider);
      await client.removeProviderKey(key.provider);
      ref.invalidate(providerKeysProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Key removed')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to remove key: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}
