import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/state.dart';
import '../../utils/error_helpers.dart';

/// Sessions management page.
class SessionsPage extends ConsumerWidget {
  const SessionsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionsAsync = ref.watch(sessionsProvider);
    final activeSessionId = ref.watch(activeSessionIdProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sessions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () => ref.invalidate(sessionsProvider),
          ),
        ],
      ),
      body: sessionsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
              const SizedBox(height: 16),
              Text('Failed to load sessions: $error'),
              const SizedBox(height: 16),
              FilledButton.tonal(
                onPressed: () => ref.invalidate(sessionsProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (sessions) {
          if (sessions.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.history, size: 64, color: Colors.grey.shade400),
                  const SizedBox(height: 16),
                  Text(
                    'No sessions yet',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.grey.shade600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Start a conversation to create a session',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey.shade500,
                    ),
                  ),
                ],
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: sessions.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final session = sessions[index];
              final isActive = session.id == activeSessionId;

              return Card(
                color: isActive
                    ? Theme.of(context).colorScheme.primaryContainer
                    : null,
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: isActive
                        ? Theme.of(context).colorScheme.primary
                        : Colors.grey.shade300,
                    child: Icon(
                      Icons.chat_bubble_outline,
                      color: isActive ? Colors.white : Colors.grey.shade600,
                    ),
                  ),
                  title: Text(session.title ?? 'Untitled Session'),
                  subtitle: session.lastUsedAt != null
                      ? Text(_formatDate(session.lastUsedAt!))
                      : null,
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (isActive) const Chip(label: Text('Active')),
                      PopupMenuButton<String>(
                        onSelected: (value) async {
                          if (value == 'delete') {
                            final confirmed = await showDialog<bool>(
                              context: context,
                              builder: (context) => AlertDialog(
                                title: const Text('Delete Session'),
                                content: const Text(
                                  'Are you sure you want to delete this session?',
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () =>
                                        Navigator.of(context).pop(false),
                                    child: const Text('Cancel'),
                                  ),
                                  FilledButton(
                                    onPressed: () =>
                                        Navigator.of(context).pop(true),
                                    child: const Text('Delete'),
                                  ),
                                ],
                              ),
                            );
                            if (confirmed == true) {
                              try {
                                final client = ref.read(apiClientProvider);
                                await client.deleteSession(session.id);
                                ref.invalidate(sessionsProvider);
                                if (activeSessionId == session.id) {
                                  ref
                                          .read(activeSessionIdProvider.notifier)
                                          .state =
                                      null;
                                }
                              } catch (e) {
                                if (context.mounted) {
                                  showErrorSnackBar(context, 'Failed to delete session', e);
                                }
                              }
                            }
                          }
                        },
                        itemBuilder: (context) => [
                          const PopupMenuItem(
                            value: 'delete',
                            child: Row(
                              children: [
                                Icon(Icons.delete_outline, color: Colors.red),
                                SizedBox(width: 8),
                                Text('Delete'),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  onTap: () async {
                    try {
                      ref.read(activeSessionIdProvider.notifier).state =
                          session.id;
                      // Load session messages
                      final client = ref.read(apiClientProvider);
                      final fullSession = await client.getSession(session.id);
                      ref
                          .read(chatMessagesProvider.notifier)
                          .loadMessages(fullSession.messages);
                      if (context.mounted) {
                        context.go('/chat');
                      }
                    } catch (e) {
                      if (context.mounted) {
                        showErrorSnackBar(context, 'Failed to load session', e);
                      }
                    }
                  },
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          try {
            final client = ref.read(apiClientProvider);
            final session = await client.createSession();
            ref.read(activeSessionIdProvider.notifier).state = session.id;
            ref.read(chatMessagesProvider.notifier).clearMessages();
            ref.invalidate(sessionsProvider);
            if (context.mounted) {
              context.go('/chat');
            }
          } catch (e) {
            if (context.mounted) {
              showErrorSnackBar(context, 'Failed to create session', e);
            }
          }
        },
        icon: const Icon(Icons.add),
        label: const Text('New Session'),
      ),
    );
  }

  String _formatDate(DateTime date) {
    return formatRelativeDate(date);
  }
}
