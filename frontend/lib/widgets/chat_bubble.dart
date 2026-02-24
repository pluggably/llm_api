import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:pluggably_llm_client/sdk.dart';
import 'download_helper.dart';

/// Chat bubble widget for displaying messages.
class ChatBubble extends StatelessWidget {
  final Message message;
  final bool showRegenerate;
  final VoidCallback? onRegenerate;

  const ChatBubble({
    super.key,
    required this.message,
    this.showRegenerate = false,
    this.onRegenerate,
  });

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    final assistantLabel =
        message.modelName != null && message.modelName!.isNotEmpty
        ? message.modelName!
        : 'Assistant';
    final colorScheme = Theme.of(context).colorScheme;
    final hasInlineImages =
        message.images != null && message.images!.isNotEmpty;
    final hasArtifactImages =
        message.artifactUrls != null && message.artifactUrls!.isNotEmpty;
    final hasMeshArtifacts =
        message.meshArtifactUrls != null &&
        message.meshArtifactUrls!.isNotEmpty;
    final hasMesh = message.mesh != null;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.75,
        ),
        margin: EdgeInsets.only(
          top: 8,
          bottom: 8,
          left: isUser ? 48 : 0,
          right: isUser ? 0 : 48,
        ),
        child: Column(
          crossAxisAlignment: isUser
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            // Role label
            Padding(
              padding: const EdgeInsets.only(bottom: 4, left: 4, right: 4),
              child: Text(
                isUser ? 'You' : assistantLabel,
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(color: Colors.grey.shade600),
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 4, left: 4, right: 4),
              child: Text(
                _formatTimestamp(message.createdAt),
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(color: Colors.grey.shade500),
              ),
            ),
            // Message bubble
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isUser
                    ? colorScheme.primaryContainer
                    : colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(isUser ? 16 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 16),
                ),
              ),
              child: isUser
                  ? _buildUserContent(context, message)
                  : hasInlineImages
                  ? _buildImageContent(context, message.images!)
                  : hasArtifactImages && hasMeshArtifacts
                  ? _buildImageAndMeshArtifactContent(
                      context,
                      message.artifactUrls!,
                      message.meshArtifactUrls!,
                    )
                  : hasArtifactImages
                  ? _buildArtifactImageContent(context, message.artifactUrls!)
                  : hasMeshArtifacts
                  ? _buildMeshArtifactContent(
                      context,
                      message.meshArtifactUrls!,
                    )
                  : hasMesh
                  ? _buildMeshPlaceholder(context)
                  : message.content.isEmpty
                  ? Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: colorScheme.primary,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Thinking...',
                          style: TextStyle(
                            color: Colors.grey.shade600,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    )
                  : MarkdownBody(
                      data: message.content,
                      selectable: true,
                      styleSheet: MarkdownStyleSheet(
                        p: Theme.of(context).textTheme.bodyMedium,
                        code: TextStyle(
                          fontFamily: 'monospace',
                          backgroundColor: colorScheme.surfaceContainer,
                        ),
                        codeblockDecoration: BoxDecoration(
                          color: colorScheme.surfaceContainer,
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
            ),
            // Actions
            if (showRegenerate && onRegenerate != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: TextButton.icon(
                  onPressed: onRegenerate,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Regenerate'),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildUserContent(BuildContext context, Message message) {
    final hasImages = message.images != null && message.images!.isNotEmpty;
    if (!hasImages) {
      return SelectableText(message.content);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildImageContent(context, message.images!),
        if (message.content.isNotEmpty) ...[
          const SizedBox(height: 8),
          SelectableText(message.content),
        ],
      ],
    );
  }

  /// Build image content from base64 data.
  Widget _buildImageContent(BuildContext context, List<String> images) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final imageData in images)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  GestureDetector(
                    onTap: () => _showImagePreview(
                      context,
                      MemoryImage(_decodeBase64Image(imageData)),
                    ),
                    child: Image.memory(
                      _decodeBase64Image(imageData),
                      fit: BoxFit.contain,
                      errorBuilder: (context, error, stackTrace) => Container(
                        padding: const EdgeInsets.all(16),
                        color: Colors.grey.shade200,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.broken_image,
                              color: Colors.grey.shade600,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Failed to load image',
                              style: TextStyle(color: Colors.grey.shade600),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: IconButton(
                      icon: const Icon(Icons.download, size: 18),
                      tooltip: 'Download image',
                      onPressed: () => downloadUrl(
                        context,
                        _asDataUrl(imageData),
                        filename: 'image.png',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  /// Build image content from artifact URLs.
  Widget _buildArtifactImageContent(BuildContext context, List<String> urls) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final url in urls)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  GestureDetector(
                    onTap: () => _showImagePreview(context, NetworkImage(url)),
                    child: Image.network(
                      url,
                      fit: BoxFit.contain,
                      loadingBuilder: (context, child, loadingProgress) {
                        if (loadingProgress == null) return child;
                        return Container(
                          padding: const EdgeInsets.all(32),
                          child: Center(
                            child: CircularProgressIndicator(
                              value: loadingProgress.expectedTotalBytes != null
                                  ? loadingProgress.cumulativeBytesLoaded /
                                        loadingProgress.expectedTotalBytes!
                                  : null,
                            ),
                          ),
                        );
                      },
                      errorBuilder: (context, error, stackTrace) => Container(
                        padding: const EdgeInsets.all(16),
                        color: Colors.grey.shade200,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.broken_image,
                              color: Colors.grey.shade600,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Failed to load image',
                              style: TextStyle(color: Colors.grey.shade600),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              url,
                              style: TextStyle(
                                color: Colors.grey.shade500,
                                fontSize: 10,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: IconButton(
                      icon: const Icon(Icons.download, size: 18),
                      tooltip: 'Download image',
                      onPressed: () =>
                          downloadUrl(context, url, filename: 'image.png'),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  /// Build image preview content with mesh download when both are present.
  Widget _buildImageAndMeshArtifactContent(
    BuildContext context,
    List<String> imageUrls,
    List<String> meshUrls,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildArtifactImageContent(context, imageUrls),
        Align(
          alignment: Alignment.centerRight,
          child: IconButton(
            icon: const Icon(Icons.download, size: 18),
            tooltip: 'Download mesh (OBJ)',
            onPressed: () =>
                downloadUrl(context, meshUrls.first, filename: 'mesh.obj'),
          ),
        ),
      ],
    );
  }

  /// Build mesh content from artifact URLs.
  Widget _buildMeshArtifactContent(BuildContext context, List<String> urls) {
    final url = urls.first;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          color: Colors.grey.shade900,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.view_in_ar, size: 48, color: Colors.grey.shade400),
              const SizedBox(height: 8),
              Text(
                '3D preview disabled',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
              ),
              const SizedBox(height: 4),
              Text(
                'Use download to open the OBJ file.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.white54),
              ),
            ],
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: IconButton(
            icon: const Icon(Icons.download, size: 18),
            tooltip: 'Download mesh (OBJ)',
            onPressed: () => downloadUrl(context, url, filename: 'mesh.obj'),
          ),
        ),
      ],
    );
  }

  /// Build a placeholder for 3D mesh content.
  Widget _buildMeshPlaceholder(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.view_in_ar, size: 48, color: Colors.grey.shade600),
          const SizedBox(height: 8),
          Text(
            '3D Model Generated',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Text(
            '3D viewer unavailable',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
          ),
        ],
      ),
    );
  }

  void _showImagePreview(BuildContext context, ImageProvider imageProvider) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.black,
        insetPadding: const EdgeInsets.all(16),
        child: InteractiveViewer(
          child: Image(image: imageProvider, fit: BoxFit.contain),
        ),
      ),
    );
  }

  /// Decode base64 image data (handles data URI prefix if present).
  static Uint8List _decodeBase64Image(String data) {
    // Remove data URI prefix if present (e.g., "data:image/png;base64,")
    String base64Data = data;
    if (data.contains(',')) {
      base64Data = data.split(',').last;
    }
    return base64Decode(base64Data);
  }

  String _asDataUrl(String imageData) {
    if (imageData.startsWith('data:')) {
      return imageData;
    }
    return 'data:image/png;base64,$imageData';
  }

  String _formatTimestamp(DateTime timestamp) {
    return '${timestamp.month}/${timestamp.day} ${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
  }
}
