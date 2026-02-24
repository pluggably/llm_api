import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/state.dart';
import 'package:pluggably_llm_client/sdk.dart';
import '../../widgets/model_card.dart';
import '../../widgets/settings_drawer.dart';

/// Models catalog page with modality filtering.
class ModelsPage extends ConsumerWidget {
  const ModelsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final modelsAsync = ref.watch(filteredModelsProvider);
    final providersAsync = ref.watch(visibleModelProvidersProvider);
    final providerCountsAsync = ref.watch(visibleModelProviderCountsProvider);
    final selectedModality = ref.watch(selectedModalityProvider);
    final selectedProviders = ref.watch(selectedVisibleProvidersProvider);
    final selectedModelId = ref.watch(selectedModelIdProvider);
    final query = ref.watch(modelSearchQueryProvider);
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth >= 1024;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Models'),
        actions: [
          // Active downloads indicator
          Consumer(
            builder: (context, ref, _) {
              final activeJobsAsync = ref.watch(activeJobsProvider);
              return activeJobsAsync.when(
                loading: () => const SizedBox.shrink(),
                error: (_, _) => const SizedBox.shrink(),
                data: (jobs) {
                  if (jobs.isEmpty) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: Tooltip(
                      message: '${jobs.length} download(s) in progress',
                      child: ActionChip(
                        avatar: SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            value: jobs.isNotEmpty
                                ? jobs.first.progressPct / 100
                                : null,
                          ),
                        ),
                        label: Text('${jobs.length}'),
                        onPressed: () => _showDownloadsDialog(context, ref),
                      ),
                    ),
                  );
                },
              );
            },
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'add') {
                _showAddModelDialog(context, ref);
              } else if (value == 'refresh') {
                ref.invalidate(modelsProvider);
                ref.invalidate(jobsProvider);
              } else if (value == 'downloads') {
                _showDownloadsDialog(context, ref);
              }
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'add', child: Text('Add model')),
              PopupMenuItem(value: 'downloads', child: Text('View downloads')),
              PopupMenuItem(value: 'refresh', child: Text('Refresh')),
            ],
          ),
        ],
      ),
      body: Row(
        children: [
          // Main content
          Expanded(
            flex: 2,
            child: Column(
              children: [
                // Modality tabs
                _ModalityTabs(
                  selectedModality: selectedModality,
                  onSelected: (modality) {
                    ref.read(selectedModalityProvider.notifier).state =
                        modality;
                  },
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          initialValue: query,
                          decoration: const InputDecoration(
                            labelText: 'Search models',
                            prefixIcon: Icon(Icons.search),
                          ),
                          onChanged: (value) =>
                              ref
                                      .read(modelSearchQueryProvider.notifier)
                                      .state =
                                  value,
                        ),
                      ),
                      const SizedBox(width: 12),
                      FilledButton.icon(
                        onPressed: () => _showAddModelDialog(context, ref),
                        icon: const Icon(Icons.add),
                        label: const Text('Add Model'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                providersAsync.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, _) => const SizedBox.shrink(),
                  data: (providers) {
                    if (providers.isEmpty) return const SizedBox.shrink();
                    final providerCounts = providerCountsAsync.valueOrNull;
                    final allProviders = providers.toSet();
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            FilterChip(
                              label: const Text('All providers'),
                              selected: selectedProviders == null,
                              onSelected: (_) {
                                ref
                                    .read(
                                      selectedVisibleProvidersProvider.notifier,
                                    )
                                    .showAll();
                              },
                            ),
                            for (final provider in providers)
                              FilterChip(
                                label: Text(
                                  '${providerDisplayName(provider)} (${providerCounts?[provider] ?? 0})',
                                ),
                                selected:
                                    selectedProviders?.contains(provider) ??
                                    true,
                                onSelected: (isSelected) {
                                  ref
                                      .read(
                                        selectedVisibleProvidersProvider
                                            .notifier,
                                      )
                                      .toggleProvider(
                                        provider,
                                        allProviders: allProviders,
                                      );
                                },
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
                const SizedBox(height: 8),
                // Models grid
                Expanded(
                  child: modelsAsync.when(
                    loading: () =>
                        const Center(child: CircularProgressIndicator()),
                    error: (error, stack) => Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.error_outline,
                            size: 48,
                            color: Colors.red.shade300,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Failed to load models: $error',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 16),
                          FilledButton.tonal(
                            onPressed: () => ref.invalidate(modelsProvider),
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                    data: (models) {
                      if (models.isEmpty) {
                        return Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.auto_awesome_outlined,
                                size: 64,
                                color: Colors.grey.shade400,
                              ),
                              const SizedBox(height: 16),
                              Text(
                                selectedModality != null
                                    ? 'No $selectedModality models available'
                                    : query.isNotEmpty
                                    ? 'No models match "$query"'
                                    : 'No models available',
                                style: Theme.of(context).textTheme.bodyLarge,
                              ),
                            ],
                          ),
                        );
                      }

                      return GridView.builder(
                        padding: const EdgeInsets.all(16),
                        gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 320,
                          childAspectRatio: isDesktop ? 1.4 : 1.2,
                          crossAxisSpacing: 16,
                          mainAxisSpacing: 16,
                        ),
                        itemCount: models.length,
                        itemBuilder: (context, index) {
                          final model = models[index];
                          final isLocked =
                              model.availability?.access == 'locked';
                          return ModelCard(
                            model: model,
                            isSelected: model.id == selectedModelId,
                            onTap: isLocked
                                ? () => context.go('/keys')
                                : () {
                                    ref
                                        .read(selectedModelIdProvider.notifier)
                                        .state = model
                                        .id;
                                    ref
                                            .read(
                                              selectionModeProvider.notifier,
                                            )
                                            .state =
                                        'model';
                                    ref
                                        .read(selectedModalityProvider.notifier)
                                        .state = model
                                        .modality;
                                    // Navigate to chat after selecting model
                                    context.go('/chat');
                                  },
                            onSetDefault: () async {
                              final client = ref.read(apiClientProvider);
                              try {
                                await client.setDefaultModel(model.id);
                                ref.invalidate(modelsProvider);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Default ${model.modality} model set to ${model.name}',
                                      ),
                                    ),
                                  );
                                }
                              } catch (e) {
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        'Failed to set default: $e',
                                      ),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                }
                              }
                            },
                            onLoad: () async {
                              final client = ref.read(apiClientProvider);
                              try {
                                await client.loadModel(model.id);
                                ref.invalidate(loadedModelsProvider);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Loading ${model.name}...'),
                                    ),
                                  );
                                }
                              } catch (e) {
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Failed to load model: $e'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                }
                              }
                            },
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          // Settings drawer (desktop only)
          if (isDesktop && selectedModelId != null)
            const SizedBox(width: 320, child: SettingsDrawer()),
        ],
      ),
      // Settings drawer for mobile/tablet
      endDrawer: !isDesktop && selectedModelId != null
          ? const Drawer(width: 320, child: SettingsDrawer())
          : null,
    );
  }

  Future<void> _showAddModelDialog(BuildContext context, WidgetRef ref) async {
    final searchController = TextEditingController();
    List<ModelSearchResult> results = [];
    bool isLoading = false;
    String? error;

    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Add Model (Hugging Face)'),
          content: SizedBox(
            width: 420,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: searchController,
                  decoration: const InputDecoration(
                    labelText: 'Search Hugging Face',
                    prefixIcon: Icon(Icons.search),
                  ),
                  onSubmitted: (_) async {
                    setState(() {
                      isLoading = true;
                      error = null;
                    });
                    try {
                      final client = ref.read(apiClientProvider);
                      final response = await client.searchModels(
                        query: searchController.text,
                      );
                      setState(() {
                        results = response.results;
                        isLoading = false;
                      });
                    } catch (e) {
                      setState(() {
                        error = e.toString();
                        isLoading = false;
                      });
                    }
                  },
                ),
                const SizedBox(height: 12),
                if (isLoading) const CircularProgressIndicator(),
                if (error != null)
                  Text(error!, style: TextStyle(color: Colors.red.shade400)),
                if (!isLoading && error == null)
                  SizedBox(
                    height: 360,
                    child: ListView.builder(
                      itemCount: results.length,
                      itemBuilder: (context, index) {
                        final model = results[index];
                        return Card(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          child: ListTile(
                            leading: _modalityIcon(model.modalityHints),
                            title: Text(
                              model.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (model.modalityHints.isNotEmpty)
                                  Text(
                                    model.modalityHints.join(', '),
                                    style: TextStyle(
                                      color: Colors.grey.shade600,
                                      fontSize: 12,
                                    ),
                                  ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    if (model.downloads != null) ...[
                                      Icon(
                                        Icons.download,
                                        size: 14,
                                        color: Colors.grey.shade500,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        model.downloadsFormatted,
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: Colors.grey.shade600,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                    ],
                                    if (model.tags.isNotEmpty)
                                      Expanded(
                                        child: Text(
                                          model.tags.take(3).join(', '),
                                          style: TextStyle(
                                            fontSize: 11,
                                            color: Colors.grey.shade500,
                                          ),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                  ],
                                ),
                              ],
                            ),
                            isThreeLine: true,
                            trailing: IconButton(
                              icon: const Icon(Icons.add_circle_outline),
                              tooltip: 'Add model',
                              onPressed: () =>
                                  _selectAndAddModel(context, ref, model),
                            ),
                            onTap: () => _selectAndAddModel(context, ref, model),
                          ),
                        );
                      },
                    ),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _downloadModel(
    BuildContext context,
    WidgetRef ref,
    ModelSearchResult model,
    {
      required bool installLocal,
    }
  ) async {
    try {
      final client = ref.read(apiClientProvider);
      await client.downloadModel(
        modelId: model.id,
        name: model.name,
        modality: model.modalityHints.isNotEmpty
            ? model.modalityHints.first
            : 'text',
        sourceType: 'huggingface',
        sourceId: model.id,
        installLocal: installLocal,
        provider: installLocal ? 'local' : 'huggingface',
      );
      ref.invalidate(modelsProvider);
      ref.invalidate(jobsProvider);
      if (context.mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              installLocal
                  ? 'Download started: ${model.name}'
                  : 'Added as Hugging Face hosted model: ${model.name}',
            ),
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Download failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  bool _supportsHfHosted(ModelSearchResult model) {
    if (model.modalityHints.isEmpty) return true;
    return model.modalityHints.any((m) => m == 'text' || m == 'image');
  }

  Future<void> _selectAndAddModel(
    BuildContext context,
    WidgetRef ref,
    ModelSearchResult model,
  ) async {
    if (!_supportsHfHosted(model)) {
      await _downloadModel(context, ref, model, installLocal: true);
      return;
    }

    final action = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('Install locally'),
              subtitle: const Text('Download model files to your VPS storage'),
              leading: const Icon(Icons.download),
              onTap: () => Navigator.of(context).pop('local'),
            ),
            ListTile(
              title: const Text('Use Hugging Face hosted'),
              subtitle: const Text('Run via Hugging Face Inference API'),
              leading: const Icon(Icons.cloud_outlined),
              onTap: () => Navigator.of(context).pop('hosted'),
            ),
          ],
        ),
      ),
    );

    if (!context.mounted || action == null) return;
    await _downloadModel(
      context,
      ref,
      model,
      installLocal: action == 'local',
    );
  }

  Widget _modalityIcon(List<String> modalityHints) {
    if (modalityHints.contains('text')) {
      return const Icon(Icons.chat_bubble_outline);
    }
    if (modalityHints.contains('image')) {
      return const Icon(Icons.image_outlined);
    }
    if (modalityHints.contains('3d')) {
      return const Icon(Icons.view_in_ar_outlined);
    }
    return const Icon(Icons.auto_awesome_outlined);
  }

  Future<void> _showDownloadsDialog(BuildContext context, WidgetRef ref) async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Downloads'),
        content: SizedBox(
          width: 400,
          height: 300,
          child: Consumer(
            builder: (context, ref, _) {
              final jobsAsync = ref.watch(jobsProvider);
              return jobsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(child: Text('Error: $e')),
                data: (jobs) {
                  if (jobs.isEmpty) {
                    return Center(
                      child: Text(
                        'No downloads',
                        style: TextStyle(color: Colors.grey.shade500),
                      ),
                    );
                  }
                  return ListView.builder(
                    itemCount: jobs.length,
                    itemBuilder: (context, index) {
                      final job = jobs[index];
                      return ListTile(
                        leading: _jobStatusIcon(job.status),
                        title: Text(
                          job.modelId,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (job.isActive)
                              LinearProgressIndicator(
                                value: job.progressPct / 100,
                              ),
                            Text(
                              _jobStatusText(job),
                              style: TextStyle(
                                fontSize: 12,
                                color: job.status == JobStatus.failed
                                    ? Colors.red
                                    : Colors.grey.shade600,
                              ),
                            ),
                          ],
                        ),
                        trailing: job.isActive
                            ? IconButton(
                                icon: const Icon(Icons.cancel_outlined),
                                tooltip: 'Cancel',
                                onPressed: () async {
                                  final client = ref.read(apiClientProvider);
                                  await client.cancelJob(job.jobId);
                                  ref.invalidate(jobsProvider);
                                },
                              )
                            : null,
                      );
                    },
                  );
                },
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              ref.invalidate(jobsProvider);
            },
            child: const Text('Refresh'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _jobStatusIcon(JobStatus status) {
    switch (status) {
      case JobStatus.queued:
        return const Icon(Icons.schedule, color: Colors.grey);
      case JobStatus.running:
        return const SizedBox(
          width: 24,
          height: 24,
          child: CircularProgressIndicator(strokeWidth: 2),
        );
      case JobStatus.completed:
        return const Icon(Icons.check_circle, color: Colors.green);
      case JobStatus.failed:
        return const Icon(Icons.error, color: Colors.red);
      case JobStatus.cancelled:
        return const Icon(Icons.cancel, color: Colors.orange);
    }
  }

  String _jobStatusText(DownloadJob job) {
    switch (job.status) {
      case JobStatus.queued:
        return 'Queued';
      case JobStatus.running:
        return '${job.progressPct.toStringAsFixed(0)}% complete';
      case JobStatus.completed:
        return 'Completed';
      case JobStatus.failed:
        return job.error ?? 'Failed';
      case JobStatus.cancelled:
        return 'Cancelled';
    }
  }
}

class _ModalityTabs extends StatelessWidget {
  final String? selectedModality;
  final ValueChanged<String?> onSelected;

  const _ModalityTabs({
    required this.selectedModality,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final modalities = ['text', 'image', '3d'];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          FilterChip(
            label: const Text('All'),
            selected: selectedModality == null,
            onSelected: (_) => onSelected(null),
          ),
          const SizedBox(width: 8),
          for (final modality in modalities) ...[
            FilterChip(
              label: Text(_modalityLabel(modality)),
              selected: selectedModality == modality,
              onSelected: (_) => onSelected(modality),
              avatar: Icon(_modalityIcon(modality), size: 18),
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }

  String _modalityLabel(String modality) {
    switch (modality) {
      case 'text':
        return 'Text';
      case 'image':
        return 'Image';
      case '3d':
        return '3D';
      default:
        return modality;
    }
  }

  IconData _modalityIcon(String modality) {
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
}
