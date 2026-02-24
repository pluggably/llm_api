import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/state.dart';
import 'package:pluggably_llm_client/sdk.dart';

/// Model card widget for the models catalog.
class ModelCard extends ConsumerWidget {
  final Model model;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback? onLoad;
  final VoidCallback? onSetDefault;

  const ModelCard({
    super.key,
    required this.model,
    required this.isSelected,
    required this.onTap,
    this.onLoad,
    this.onSetDefault,
  });

  bool get _isLocked => model.availability?.access == 'locked';
  bool get _isHosted => model.provider.toLowerCase() == 'huggingface';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loadedModelsAsync = ref.watch(loadedModelsProvider);

    final isLoaded =
        loadedModelsAsync.whenOrNull(
          data: (loaded) => loaded.any((m) => m.modelId == model.id),
        ) ??
        false;

    return Opacity(
      opacity: _isLocked ? 0.6 : 1.0,
      child: Card(
      color: isSelected ? Theme.of(context).colorScheme.primaryContainer : null,
      child: InkWell(
        onTap: onTap,
        onSecondaryTap: model.isDefault || onSetDefault == null ? null : onSetDefault,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with modality icon and status
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: _getModalityColor(
                        model.modality,
                      ).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(
                      _getModalityIcon(model.modality),
                      color: _getModalityColor(model.modality),
                      size: 24,
                    ),
                  ),
                  const Spacer(),
                  if (_isLocked) ...[
                    const _LockedBadge(),
                    const SizedBox(width: 8),
                  ] else if (model.isDefault) ...[
                    const _DefaultBadge(),
                    const SizedBox(width: 8),
                  ],
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.more_vert, size: 20),
                    tooltip: 'Model actions',
                    onSelected: (value) {
                      if (value == 'set_default') {
                        onSetDefault?.call();
                      }
                      if (value == 'load') {
                        onLoad?.call();
                      }
                    },
                    itemBuilder: (context) => [
                      if (!model.isDefault && onSetDefault != null)
                        const PopupMenuItem(
                          value: 'set_default',
                          child: Text('Set default'),
                        ),
                      if (!isLoaded && onLoad != null)
                        const PopupMenuItem(
                          value: 'load',
                          child: Text('Load model'),
                        ),
                    ],
                  ),
                  _StatusBadge(status: model.status, isLoaded: isLoaded),
                ],
              ),
              const SizedBox(height: 8),

              // Model name and provider (flexible to avoid overflow)
              Flexible(
                fit: FlexFit.loose,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      model.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),

                    Text(
                      model.provider,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey.shade600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),

                    const SizedBox(height: 6),
                    _LocationBadge(isHosted: _isHosted),

                    if (model.version != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        'v${model.version}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey.shade500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),

            ],
          ),
        ),
      ),
    ),
    );
  }

  IconData _getModalityIcon(String modality) {
    switch (modality) {
      case 'text':
        return Icons.chat_bubble_outline;
      case 'image':
        return Icons.image_outlined;
      case '3d':
        return Icons.view_in_ar_outlined;
      default:
        return Icons.auto_awesome_outlined;
    }
  }

  Color _getModalityColor(String modality) {
    switch (modality) {
      case 'text':
        return const Color(0xFF6750A4);
      case 'image':
        return const Color(0xFF00A67E);
      case '3d':
        return const Color(0xFFD4A27F);
      default:
        return Colors.grey;
    }
  }
}

class _LocationBadge extends StatelessWidget {
  final bool isHosted;

  const _LocationBadge({required this.isHosted});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isHosted ? scheme.tertiaryContainer : scheme.secondaryContainer,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        isHosted ? 'Hosted' : 'Local',
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: isHosted ? scheme.onTertiaryContainer : scheme.onSecondaryContainer,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final ModelStatus status;
  final bool isLoaded;

  const _StatusBadge({required this.status, required this.isLoaded});

  @override
  Widget build(BuildContext context) {
    if (isLoaded) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.green.shade50,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle, size: 14, color: Colors.green.shade700),
            const SizedBox(width: 4),
            Text(
              'Ready',
              style: TextStyle(fontSize: 12, color: Colors.green.shade700),
            ),
          ],
        ),
      );
    }

    switch (status) {
      case ModelStatus.downloading:
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.blue.shade50,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.blue.shade700,
                ),
              ),
              const SizedBox(width: 4),
              Text(
                'Downloading',
                style: TextStyle(fontSize: 12, color: Colors.blue.shade700),
              ),
            ],
          ),
        );
      case ModelStatus.loading:
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.orange.shade50,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.orange.shade700,
                ),
              ),
              const SizedBox(width: 4),
              Text(
                'Loading',
                style: TextStyle(fontSize: 12, color: Colors.orange.shade700),
              ),
            ],
          ),
        );
      case ModelStatus.failed:
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.red.shade50,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 14, color: Colors.red.shade700),
              const SizedBox(width: 4),
              Text(
                'Failed',
                style: TextStyle(fontSize: 12, color: Colors.red.shade700),
              ),
            ],
          ),
        );
      case ModelStatus.busy:
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.purple.shade50,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.hourglass_empty,
                size: 14,
                color: Colors.purple.shade700,
              ),
              const SizedBox(width: 4),
              Text(
                'Busy',
                style: TextStyle(fontSize: 12, color: Colors.purple.shade700),
              ),
            ],
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }
}

class _LockedBadge extends StatelessWidget {
  const _LockedBadge();

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Add an API key in Provider Keys to enable this model',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.lock_outline, size: 14, color: Colors.grey.shade700),
            const SizedBox(width: 4),
            Text(
              'Key required',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
            ),
          ],
        ),
      ),
    );
  }
}

class _DefaultBadge extends StatelessWidget {
  const _DefaultBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.amber.shade100,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.star, size: 14, color: Colors.amber.shade900),
          const SizedBox(width: 4),
          Text(
            'Default',
            style: TextStyle(fontSize: 12, color: Colors.amber.shade900),
          ),
        ],
      ),
    );
  }
}
