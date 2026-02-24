import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/state.dart';
import '../../utils/error_helpers.dart';
import 'package:pluggably_llm_client/sdk.dart';

/// Sessions list shown in the left navigation rail.
class SessionsRail extends ConsumerWidget {
  const SessionsRail({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionsAsync = ref.watch(sessionsProvider);
    final activeSessionId = ref.watch(activeSessionIdProvider);

    return LayoutBuilder(
      builder: (context, constraints) {
        final boundedHeight = constraints.hasBoundedHeight;
        final list = sessionsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Padding(
            padding: const EdgeInsets.all(12),
            child: Text(
              'Failed to load sessions: $error',
              style: TextStyle(color: Colors.red.shade400, fontSize: 12),
            ),
          ),
          data: (sessions) {
            if (sessions.isEmpty) {
              return Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  'No sessions yet',
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                ),
              );
            }

            return ListView.builder(
              shrinkWrap: !boundedHeight,
              physics: boundedHeight
                  ? const BouncingScrollPhysics()
                  : const NeverScrollableScrollPhysics(),
              itemCount: sessions.length,
              itemBuilder: (context, index) {
                final session = sessions[index];
                final isActive = session.id == activeSessionId;
                return ListTile(
                  dense: true,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 0,
                  ),
                  title: Text(
                    session.title ?? 'Untitled',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isActive ? FontWeight.w600 : null,
                    ),
                  ),
                  subtitle: session.lastUsedAt != null
                      ? Text(
                          _formatDate(session.lastUsedAt!),
                          style: const TextStyle(fontSize: 10),
                        )
                      : null,
                  selected: isActive,
                  trailing: IconButton(
                    icon: const Icon(Icons.edit, size: 16),
                    tooltip: 'Rename',
                    onPressed: () => _renameSession(context, ref, session),
                  ),
                  onTap: () async {
                    try {
                      ref.read(activeSessionIdProvider.notifier).state =
                          session.id;
                      final client = ref.read(apiClientProvider);
                      final fullSession = await client.getSession(session.id);
                      ref
                          .read(chatMessagesProvider.notifier)
                          .loadMessages(fullSession.messages);
                      if (context.mounted) {
                        context.go('/chat');
                      }
                    } catch (e) {
                      if (e is ApiException && e.statusCode == 404) {
                        ref.read(activeSessionIdProvider.notifier).state = null;
                        ref.read(chatMessagesProvider.notifier).clearMessages();
                        ref.invalidate(sessionsProvider);
                        if (context.mounted) {
                          showErrorSnackBar(
                            context,
                            'Session no longer exists. Start a new chat.',
                            e,
                          );
                        }
                        return;
                      }
                      if (context.mounted) {
                        showErrorSnackBar(context, 'Failed to load session', e);
                      }
                    }
                  },
                );
              },
            );
          },
        );

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: boundedHeight ? MainAxisSize.max : MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Text(
                'Sessions',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            if (boundedHeight) Expanded(child: list) else list,
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: FilledButton.icon(
                onPressed: () async {
                  final client = ref.read(apiClientProvider);
                  final session = await client.createSession();
                  ref.read(activeSessionIdProvider.notifier).state = session.id;
                  ref.read(chatMessagesProvider.notifier).clearMessages();
                  ref.invalidate(sessionsProvider);
                },
                icon: const Icon(Icons.add),
                label: const Text('New'),
              ),
            ),
          ],
        );
      },
    );
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inMinutes < 1) {
      return 'Just now';
    } else if (diff.inHours < 1) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inDays < 1) {
      return '${diff.inHours}h ago';
    } else if (diff.inDays < 7) {
      return '${diff.inDays}d ago';
    } else {
      return '${date.month}/${date.day}/${date.year}';
    }
  }

  Future<void> _renameSession(
    BuildContext context,
    WidgetRef ref,
    SessionSummary session,
  ) async {
    final controller = TextEditingController(text: session.title ?? '');
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Session'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'Title'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result == null) return;
    final client = ref.read(apiClientProvider);
    await client.updateSession(session.id, title: result);
    ref.invalidate(sessionsProvider);
  }
}
