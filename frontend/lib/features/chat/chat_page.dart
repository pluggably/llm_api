import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../../state/state.dart';
import 'package:pluggably_llm_client/sdk.dart';
import '../../widgets/chat_bubble.dart';
import '../../widgets/settings_drawer.dart';
import '../../utils/clipboard_image.dart';
import '../../utils/error_helpers.dart';

class PendingImage {
  final Uint8List bytes;
  final String dataUrl;
  final String source;
  final String? name;

  const PendingImage({
    required this.bytes,
    required this.dataUrl,
    required this.source,
    this.name,
  });
}

/// Chat page with streaming responses.
class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({super.key});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();
  final List<PendingImage> _pendingImages = [];
  bool _showSettings = true;

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  void _showFallbackNotice(String modelName, String? reason) {
    final reasonText = switch (reason) {
      'rate_limited_tier' => 'Rate limited — switched to cheaper model',
      'rate_limited_local' => 'Rate limited — switched to local model',
      'quota_exceeded' => 'Quota exceeded — switched to local model',
      'provider_overloaded' =>
        'Provider overloaded — switched to cheaper model',
      'provider_overloaded_local' =>
        'Provider overloaded — switched to local model',
      _ => 'Switched to fallback model',
    };
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$reasonText: $modelName'),
        backgroundColor: Colors.orange.shade700,
        duration: const Duration(seconds: 5),
      ),
    );
  }

  int _maxAttachmentBytes() {
    final maxMb = ref.read(attachmentMaxMbProvider);
    return (maxMb * 1024 * 1024).round();
  }

  Future<void> _addImageBytes(
    Uint8List bytes, {
    required String source,
    String? name,
  }) async {
    final totalBytes =
        _pendingImages.fold<int>(0, (sum, item) => sum + item.bytes.length) +
        bytes.length;
    if (totalBytes > _maxAttachmentBytes()) {
      _showError('Total attachment size exceeds limit');
      return;
    }

    // Encode as PNG data URL — backend will resize per model constraints
    final b64 = base64Encode(bytes);
    final dataUrl = 'data:image/png;base64,$b64';
    setState(() {
      _pendingImages.add(
        PendingImage(
          bytes: bytes,
          dataUrl: dataUrl,
          source: source,
          name: name,
        ),
      );
    });
  }

  Future<void> _pickImages() async {
    final picker = ImagePicker();
    final files = await picker.pickMultiImage();
    if (files.isEmpty) return;
    for (final file in files) {
      final bytes = await file.readAsBytes();
      await _addImageBytes(bytes, source: 'upload', name: file.name);
    }
  }

  Future<void> _pasteImage() async {
    final bytes = await readClipboardImage();
    if (bytes == null) {
      _showError('Clipboard image not available');
      return;
    }
    await _addImageBytes(bytes, source: 'paste');
  }

  Future<void> _addImageUrl() async {
    final controller = TextEditingController();
    final url = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add image URL'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(hintText: 'https://...'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Add'),
          ),
        ],
      ),
    );

    if (url == null || url.isEmpty) return;

    try {
      final response = await http.get(Uri.parse(url));
      if (!mounted) return;
      if (response.statusCode != 200) {
        _showError('Failed to fetch image URL');
        return;
      }
      final contentType = response.headers['content-type'] ?? '';
      if (!contentType.startsWith('image/')) {
        _showError('URL does not point to an image');
        return;
      }
      await _addImageBytes(response.bodyBytes, source: 'url', name: url);
    } catch (_) {
      if (mounted) _showError('Unable to fetch image (CORS or network error)');
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final prompt = _controller.text.trim();
    if (prompt.isEmpty && _pendingImages.isEmpty) return;

    final modelId = ref.read(selectedModelIdProvider);
    final selectionMode = ref.read(selectionModeProvider);
    final effectiveSelectionMode = modelId != null ? 'model' : selectionMode;
    if (effectiveSelectionMode == 'model' && modelId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a specific model')),
      );
      return;
    }

    _controller.clear();
    _focusNode.requestFocus();

    final uuid = const Uuid();
    final userMessageId = uuid.v4();
    final assistantMessageId = uuid.v4();

    // Add user message
    ref
        .read(chatMessagesProvider.notifier)
        .addMessage(
          Message(
            id: userMessageId,
            role: 'user',
            content: prompt,
            images: _pendingImages.map((img) => img.dataUrl).toList(),
            createdAt: DateTime.now(),
          ),
        );
    _scrollToBottom();

    // Add placeholder for assistant message
    ref
        .read(chatMessagesProvider.notifier)
        .addMessage(
          Message(
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            createdAt: DateTime.now(),
          ),
        );

    ref.read(isGeneratingProvider.notifier).state = true;

    // Generate a request ID for cancellation support
    final requestId = const Uuid().v4();
    ref.read(currentRequestIdProvider.notifier).state = requestId;

    try {
      final client = ref.read(apiClientProvider);
      final parameters = ref.read(parametersProvider);
      var sessionId = ref.read(activeSessionIdProvider);
      final images = _pendingImages.map((img) => img.dataUrl).toList();

      if (sessionId == null) {
        final session = await client.createSession();
        sessionId = session.id;
        ref.read(activeSessionIdProvider.notifier).state = sessionId;
        ref.invalidate(sessionsProvider);
      }

      // Use the new streaming API that handles all modalities
      await for (final event in client.generateStreamEvents(
        modelId: effectiveSelectionMode == 'model' ? modelId : null,
        prompt: prompt,
        sessionId: sessionId,
        images: images.isEmpty ? null : images,
        parameters: parameters,
        selectionMode: effectiveSelectionMode,
      )) {
        debugPrint(
          'SSE Event: isText=${event.isText}, isComplete=${event.isComplete}',
        );
        if (event.isText) {
          // Text token - append to message
          ref
              .read(chatMessagesProvider.notifier)
              .appendToLastMessage(event.textToken!);
        } else if (event.isModelSelected) {
          final modelName = event.modelName ?? event.modelId;
          if (modelName != null && modelName.isNotEmpty) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageModelName(modelName);
            if (event.fallbackUsed) {
              _showFallbackNotice(modelName, event.fallbackReason);
            }
          }
        } else if (event.isComplete && event.response != null) {
          // Complete response - could be text, image, or 3D
          final response = event.response!;
          debugPrint(
            'Complete response: modality=${response.modality}, images=${response.images?.length}, artifacts=${response.artifacts?.length}, mesh=${response.mesh != null}, text=${response.text?.length}',
          );
          if (response.images != null && response.images!.isNotEmpty) {
            debugPrint(
              'Updating message with ${response.images!.length} inline images',
            );
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageWithImages(response.images!);
          } else if (response.imageArtifactUrls.isNotEmpty ||
              response.meshArtifactUrls.isNotEmpty) {
            if (response.imageArtifactUrls.isNotEmpty) {
              // Artifact URLs are now absolute from the backend
              debugPrint(
                'Updating message with ${response.imageArtifactUrls.length} artifact images: ${response.imageArtifactUrls}',
              );
              ref
                  .read(chatMessagesProvider.notifier)
                  .updateLastMessageWithArtifactUrls(
                    response.imageArtifactUrls,
                  );
            }

            if (response.meshArtifactUrls.isNotEmpty) {
              ref
                  .read(chatMessagesProvider.notifier)
                  .updateLastMessageWithMeshArtifactUrls(
                    response.meshArtifactUrls,
                  );
            }
          } else if (response.mesh != null) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageWithMesh(response.mesh!);
          } else if (response.text != null) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessage(response.text!);
          }
        }
        _scrollToBottom();
      }
    } catch (e) {
      if (e is ApiException && e.statusCode == 404) {
        // Distinguish model-not-found 404s from session-not-found 404s
        final detail = e.detail ?? '';
        final isModelError =
            detail.contains('Model not found') ||
            detail.contains('register the model');
        if (isModelError) {
          ref
              .read(chatMessagesProvider.notifier)
              .updateLastMessage('Error: ${friendlyError(e)}');
          if (mounted) {
            showErrorSnackBar(context, 'Model error', e);
          }
        } else {
          ref.read(activeSessionIdProvider.notifier).state = null;
          ref.invalidate(sessionsProvider);
          ref
              .read(chatMessagesProvider.notifier)
              .updateLastMessage('Session expired. Start a new chat.');
          if (mounted) {
            showErrorSnackBar(context, 'Session expired', e);
          }
        }
      } else {
        ref
            .read(chatMessagesProvider.notifier)
            .updateLastMessage('Error: ${friendlyError(e)}');
        if (mounted) {
          showErrorSnackBar(context, 'Generation failed', e);
        }
      }
    } finally {
      ref.read(isGeneratingProvider.notifier).state = false;
      ref.read(currentRequestIdProvider.notifier).state = null;
      setState(() => _pendingImages.clear());
      // Refresh session list to pick up auto-naming from backend
      ref.invalidate(sessionsProvider);
    }
  }

  void _cancelRequest() {
    final requestId = ref.read(currentRequestIdProvider);
    if (requestId != null) {
      final client = ref.read(apiClientProvider);
      client.cancelRequest(requestId);
      ref.read(isGeneratingProvider.notifier).state = false;
      ref.read(currentRequestIdProvider.notifier).state = null;
    }
  }

  /// Regenerate the last assistant response via the backend API.
  Future<void> _regenerate() async {
    final sessionId = ref.read(activeSessionIdProvider);
    if (sessionId == null) return;

    final messages = ref.read(chatMessagesProvider);
    if (messages.isEmpty) return;

    // Remove the last assistant message from local UI
    final lastMessage = messages.last;
    if (lastMessage.role == 'assistant') {
      final updated = messages.sublist(0, messages.length - 1);
      ref.read(chatMessagesProvider.notifier).loadMessages(updated);
    }

    // Add placeholder for new assistant message
    ref
        .read(chatMessagesProvider.notifier)
        .addMessage(
          Message(
            id: const Uuid().v4(),
            role: 'assistant',
            content: '',
            createdAt: DateTime.now(),
          ),
        );

    ref.read(isGeneratingProvider.notifier).state = true;

    try {
      final client = ref.read(apiClientProvider);
      final modelId = ref.read(selectedModelIdProvider);
      final selectionMode = ref.read(selectionModeProvider);
      final effectiveSelectionMode = modelId != null ? 'model' : selectionMode;

      await for (final event in client.regenerateStream(
        sessionId,
        model: effectiveSelectionMode == 'model' ? modelId : null,
        selectionMode: effectiveSelectionMode,
      )) {
        if (event.isText) {
          ref
              .read(chatMessagesProvider.notifier)
              .appendToLastMessage(event.textToken!);
        } else if (event.isModelSelected) {
          final modelName = event.modelName ?? event.modelId;
          if (modelName != null && modelName.isNotEmpty) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageModelName(modelName);
            if (event.fallbackUsed) {
              _showFallbackNotice(modelName, event.fallbackReason);
            }
          }
        } else if (event.isComplete && event.response != null) {
          final response = event.response!;
          if (response.images != null && response.images!.isNotEmpty) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageWithImages(response.images!);
          } else if (response.imageArtifactUrls.isNotEmpty) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageWithArtifactUrls(response.imageArtifactUrls);
          } else if (response.meshArtifactUrls.isNotEmpty) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageWithMeshArtifactUrls(
                  response.meshArtifactUrls,
                );
          } else if (response.mesh != null) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessageWithMesh(response.mesh!);
          } else if (response.text != null) {
            ref
                .read(chatMessagesProvider.notifier)
                .updateLastMessage(response.text!);
          }
        }
        _scrollToBottom();
      }
    } catch (e) {
      ref
          .read(chatMessagesProvider.notifier)
          .updateLastMessage('Error: ${friendlyError(e)}');
      if (mounted) {
        showErrorSnackBar(context, 'Regeneration failed', e);
      }
    } finally {
      ref.read(isGeneratingProvider.notifier).state = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedModel = ref.watch(selectedModelProvider);
    final selectionMode = ref.watch(selectionModeProvider);
    final modelsAsync = ref.watch(modelsProvider);
    final models = modelsAsync.valueOrNull ?? const <Model>[];
    final messages = ref.watch(chatMessagesProvider);
    final isGenerating = ref.watch(isGeneratingProvider);
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth >= 1024;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          selectedModel?.name ??
              (selectionMode == 'free_only'
                  ? 'Chat (Free)'
                  : selectionMode == 'commercial_only'
                  ? 'Chat (Commercial)'
                  : 'Chat'),
        ),
        actions: [
          if (messages.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Clear chat',
              onPressed: () {
                ref.read(chatMessagesProvider.notifier).clearMessages();
              },
            ),
          if (isDesktop && selectedModel != null)
            IconButton(
              icon: Icon(_showSettings ? Icons.tune : Icons.tune_outlined),
              tooltip: _showSettings ? 'Hide settings' : 'Show settings',
              onPressed: () {
                setState(() => _showSettings = !_showSettings);
              },
            ),
          if (!isDesktop && selectedModel != null)
            Builder(
              builder: (context) => IconButton(
                icon: const Icon(Icons.tune),
                tooltip: 'Settings',
                onPressed: () => Scaffold.of(context).openEndDrawer(),
              ),
            ),
        ],
      ),
      body: Row(
        children: [
          // Main chat area
          Expanded(
            flex: 2,
            child: Column(
              children: [
                // Messages list
                Expanded(
                  child: messages.isEmpty
                      ? Center(
                          child: Text(
                            'Start a conversation',
                            style: TextStyle(color: Colors.grey.shade500),
                          ),
                        )
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          itemCount: messages.length,
                          itemBuilder: (context, index) {
                            final message = messages[index];
                            final isLast = index == messages.length - 1;
                            final showRegenerate =
                                isLast &&
                                message.role == 'assistant' &&
                                !isGenerating;

                            return ChatBubble(
                              message: message,
                              showRegenerate: showRegenerate,
                              onRegenerate: _regenerate,
                            );
                          },
                        ),
                ),
                if (_pendingImages.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    child: _AttachmentStrip(
                      images: _pendingImages,
                      onRemove: (index) {
                        setState(() => _pendingImages.removeAt(index));
                      },
                    ),
                  ),
                // Input area
                _ChatInput(
                  controller: _controller,
                  focusNode: _focusNode,
                  isGenerating: isGenerating,
                  onSend: _sendMessage,
                  onCancel: _cancelRequest,
                  onAttach: _pickImages,
                  onPaste: _pasteImage,
                  onAddUrl: _addImageUrl,
                  selectionMode: selectionMode,
                  models: models,
                  selectedModelId: ref.watch(selectedModelIdProvider),
                  onSelectionModeChanged: (mode) {
                    ref.read(selectionModeProvider.notifier).state = mode;
                  },
                  onModelChanged: (modelId) {
                    ref.read(selectedModelIdProvider.notifier).state = modelId;
                  },
                ),
              ],
            ),
          ),
          // Settings drawer (desktop only)
          if (isDesktop && selectedModel != null && _showSettings)
            const SizedBox(width: 320, child: SettingsDrawer()),
        ],
      ),
      endDrawer: !isDesktop && selectedModel != null
          ? const Drawer(width: 320, child: SettingsDrawer())
          : null,
    );
  }
}

class _ChatInput extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final bool isGenerating;
  final VoidCallback onSend;
  final VoidCallback onCancel;
  final VoidCallback onAttach;
  final VoidCallback onPaste;
  final VoidCallback onAddUrl;
  final String selectionMode;
  final List<Model> models;
  final String? selectedModelId;
  final ValueChanged<String> onSelectionModeChanged;
  final ValueChanged<String?> onModelChanged;

  const _ChatInput({
    required this.controller,
    required this.focusNode,
    required this.isGenerating,
    required this.onSend,
    required this.onCancel,
    required this.onAttach,
    required this.onPaste,
    required this.onAddUrl,
    required this.selectionMode,
    required this.models,
    required this.selectedModelId,
    required this.onSelectionModeChanged,
    required this.onModelChanged,
  });

  bool _isCommercialProvider(String provider) {
    const commercial = {
      'openai',
      'anthropic',
      'google',
      'azure',
      'xai',
      'deepseek',
      'huggingface',
    };
    return commercial.contains(provider.toLowerCase());
  }

  String _locationLabel(Model model) {
    return canonicalModelProvider(model.provider) == 'huggingface'
        ? 'Hosted'
        : 'Local';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.attach_file),
            tooltip: 'Attach images',
            onPressed: isGenerating ? null : onAttach,
          ),
          const SizedBox(width: 4),
          Flexible(
            flex: 3,
            child: LayoutBuilder(
              builder: (context, constraints) {
                final isFreeOnly = selectionMode == 'free_only';
                final isCommercialOnly = selectionMode == 'commercial_only';
                final filteredModels = models.where((model) {
                  if (model.isDefault) return true;
                  if (model.availability?.access == 'locked') return false;
                  if (isFreeOnly) {
                    return !_isCommercialProvider(model.provider);
                  }
                  if (isCommercialOnly) {
                    return _isCommercialProvider(model.provider);
                  }
                  return true;
                }).toList();

                final groupedModels = <String, List<Model>>{};
                for (final model in filteredModels) {
                  final provider = canonicalModelProvider(model.provider);
                  groupedModels.putIfAbsent(provider, () => []).add(model);
                }
                final orderedProviders = sortProviders(groupedModels.keys);

                final selectionValue =
                    selectedModelId != null &&
                        filteredModels.any((m) => m.id == selectedModelId)
                    ? selectedModelId
                    : 'auto';

                final selectedModel = selectionValue == 'auto'
                    ? null
                    : filteredModels
                          .where((m) => m.id == selectionValue)
                          .firstOrNull;
                final selectedLabel = selectedModel == null
                    ? 'Auto'
                  : '${providerDisplayName(canonicalModelProvider(selectedModel.provider))} / ${selectedModel.name} · ${_locationLabel(selectedModel)}';

                final menuChildren = <Widget>[
                  MenuItemButton(
                    onPressed: isGenerating
                        ? null
                        : () {
                            onModelChanged(null);
                            if (selectionMode == 'model') {
                              onSelectionModeChanged('auto');
                            }
                          },
                    child: const Text('Auto'),
                  ),
                  if (orderedProviders.isNotEmpty) const Divider(height: 1),
                  ...orderedProviders.map((provider) {
                    final providerModels = groupedModels[provider]!;
                    return SubmenuButton(
                      menuChildren: providerModels
                          .map(
                            (model) => MenuItemButton(
                              onPressed: isGenerating
                                  ? null
                                  : () {
                                      onModelChanged(model.id);
                                      onSelectionModeChanged('model');
                                    },
                              child: Text('${model.name} · ${_locationLabel(model)}'),
                            ),
                          )
                          .toList(),
                      child: Text(
                        '${providerDisplayName(provider)} (${providerModels.length})',
                      ),
                    );
                  }),
                ];

                return Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    SizedBox(
                      width: 220,
                      child: MenuAnchor(
                        menuChildren: menuChildren,
                        builder: (context, controller, child) => OutlinedButton(
                          onPressed: isGenerating ? null : controller.open,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text('Model: '),
                              Expanded(
                                child: Text(
                                  selectedLabel,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: 4),
                              const Icon(Icons.arrow_drop_down),
                            ],
                          ),
                        ),
                      ),
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Checkbox(
                          value: isFreeOnly,
                          onChanged: isGenerating
                              ? null
                              : (value) {
                                  if (value == true) {
                                    onModelChanged(null);
                                    onSelectionModeChanged('free_only');
                                  } else {
                                    onSelectionModeChanged('auto');
                                  }
                                },
                        ),
                        const Text('Free only'),
                      ],
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Checkbox(
                          value: isCommercialOnly,
                          onChanged: isGenerating
                              ? null
                              : (value) {
                                  if (value == true) {
                                    onModelChanged(null);
                                    onSelectionModeChanged('commercial_only');
                                  } else {
                                    onSelectionModeChanged('auto');
                                  }
                                },
                        ),
                        const Text('Commercial only'),
                      ],
                    ),
                  ],
                );
              },
            ),
          ),
          Expanded(
            child: Focus(
              focusNode: focusNode,
              onKeyEvent: (node, event) {
                if (event is KeyDownEvent &&
                    event.logicalKey == LogicalKeyboardKey.enter) {
                  final shiftPressed = HardwareKeyboard.instance.isShiftPressed;
                  if (!shiftPressed && !isGenerating) {
                    onSend();
                    return KeyEventResult.handled;
                  }
                }
                return KeyEventResult.ignored;
              },
              child: TextField(
                controller: controller,
                decoration: const InputDecoration(
                  hintText: 'Type your message...',
                  border: OutlineInputBorder(),
                ),
                maxLines: null,
                keyboardType: TextInputType.multiline,
                textInputAction: TextInputAction.newline,
                enabled: !isGenerating,
              ),
            ),
          ),
          const SizedBox(width: 8),
          if (isGenerating)
            IconButton.filled(
              onPressed: onCancel,
              icon: const Icon(Icons.stop),
              tooltip: 'Cancel',
              style: IconButton.styleFrom(
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
              ),
            )
          else
            IconButton.filled(
              onPressed: onSend,
              icon: const Icon(Icons.send),
              tooltip: 'Send',
            ),
        ],
      ),
    );
  }
}

class _AttachmentStrip extends StatelessWidget {
  final List<PendingImage> images;
  final ValueChanged<int> onRemove;

  const _AttachmentStrip({required this.images, required this.onRemove});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 72,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: images.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final item = images[index];
          return Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.memory(
                  item.bytes,
                  width: 72,
                  height: 72,
                  fit: BoxFit.cover,
                ),
              ),
              Positioned(
                top: -6,
                right: -6,
                child: IconButton(
                  icon: const Icon(Icons.close, size: 16),
                  onPressed: () => onRemove(index),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
