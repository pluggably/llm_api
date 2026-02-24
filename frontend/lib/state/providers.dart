/// State management using Riverpod.
library;

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:pluggably_llm_client/sdk.dart';

String canonicalModelProvider(String provider) {
  final normalized = provider.trim().toLowerCase();
  if (normalized.contains('openai')) return 'openai';
  if (normalized.contains('anthropic')) return 'anthropic';
  if (normalized.contains('google') || normalized.contains('gemini')) {
    return 'google';
  }
  if (normalized == 'hf' || normalized.contains('huggingface')) {
    return 'huggingface';
  }
  const localProviderKeys = {
    'local',
    'ollama',
    'llama.cpp',
    'llamacpp',
    'lmstudio',
    'vllm',
    'transformers',
  };
  if (localProviderKeys.contains(normalized) || normalized.contains('local')) {
    return 'local';
  }
  return normalized;
}

String providerDisplayName(String provider) {
  switch (provider) {
    case 'openai':
      return 'OpenAI';
    case 'google':
      return 'Google';
    case 'anthropic':
      return 'Anthropic';
    case 'huggingface':
      return 'Hugging Face';
    case 'local':
      return 'Local';
    case 'xai':
      return 'xAI';
    default:
      if (provider.isEmpty) return 'Unknown';
      return '${provider[0].toUpperCase()}${provider.substring(1)}';
  }
}

List<String> sortProviders(Iterable<String> providers) {
  const preferredOrder = [
    'openai',
    'google',
    'anthropic',
    'huggingface',
    'local',
  ];
  final unique = providers.toSet().toList();
  unique.sort((a, b) {
    final aIndex = preferredOrder.indexOf(a);
    final bIndex = preferredOrder.indexOf(b);
    if (aIndex != -1 && bIndex != -1) return aIndex.compareTo(bIndex);
    if (aIndex != -1) return -1;
    if (bIndex != -1) return 1;
    return a.compareTo(b);
  });
  return unique;
}

const _modelsVisibleProvidersPrefsKey = 'models_visible_providers';

class VisibleProvidersNotifier extends StateNotifier<Set<String>?> {
  final SharedPreferences _prefs;

  VisibleProvidersNotifier(this._prefs) : super(_readInitial(_prefs));

  static Set<String>? _readInitial(SharedPreferences prefs) {
    final stored = prefs.getStringList(_modelsVisibleProvidersPrefsKey);
    if (stored == null) return null;
    return stored.map(canonicalModelProvider).toSet();
  }

  Future<void> showAll() async {
    state = null;
    await _prefs.remove(_modelsVisibleProvidersPrefsKey);
  }

  Future<void> setVisibleProviders(
    Set<String> providers, {
    required Set<String> allProviders,
  }) async {
    final normalized = providers.map(canonicalModelProvider).toSet();
    if (normalized.length == allProviders.length) {
      await showAll();
      return;
    }

    state = normalized;
    await _prefs.setStringList(
      _modelsVisibleProvidersPrefsKey,
      sortProviders(normalized),
    );
  }

  Future<void> toggleProvider(
    String provider, {
    required Set<String> allProviders,
  }) async {
    final normalizedProvider = canonicalModelProvider(provider);
    final current = Set<String>.from(state ?? allProviders);
    if (current.contains(normalizedProvider)) {
      current.remove(normalizedProvider);
    } else {
      current.add(normalizedProvider);
    }

    await setVisibleProviders(current, allProviders: allProviders);
  }
}

// ==================== SDK Provider ====================

/// Provides the shared preferences instance.
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be overridden in main');
});

/// Provides the API base URL from settings.
final baseUrlProvider = StateProvider<String>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  final saved = prefs.getString('base_url');
  if (saved != null && saved.trim().isNotEmpty) {
    return saved;
  }

  if (kIsWeb) {
    final host = Uri.base.host.toLowerCase();
    if (host == 'localhost' || host == '127.0.0.1') {
      return 'http://localhost:8080';
    }
    return '/api';
  }

  return 'http://localhost:8080';
});

/// Provides the auth token.
final authTokenProvider = StateProvider<String?>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return prefs.getString('auth_token');
});

/// Max total attachment size in MB.
final attachmentMaxMbProvider = StateProvider<double>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return prefs.getDouble('attachment_max_mb') ?? 10.0;
});

/// Provides the API client instance.
final apiClientProvider = Provider<LlmApiClient>((ref) {
  final baseUrl = ref.watch(baseUrlProvider);
  final authToken = ref.watch(authTokenProvider);

  final client = LlmApiClient(baseUrl: baseUrl);
  client.setAuthToken(authToken);

  ref.onDispose(() => client.dispose());

  return client;
});

// ==================== Models State ====================

/// State for the list of available models.
final modelsProvider = FutureProvider<List<Model>>((ref) async {
  final client = ref.watch(apiClientProvider);
  return client.listModels();
});

/// Currently selected model ID.
final selectedModelIdProvider = StateProvider<String?>((ref) => null);

/// Selection mode for model routing (auto/free/commercial/model).
final selectionModeProvider = StateProvider<String>((ref) => 'auto');

/// Currently selected modality filter.
final selectedModalityProvider = StateProvider<String?>((ref) => null);

/// Which provider groups are visible in model listings.
///
/// `null` means all providers are visible.
final selectedVisibleProvidersProvider =
    StateNotifierProvider<VisibleProvidersNotifier, Set<String>?>((ref) {
      final prefs = ref.watch(sharedPreferencesProvider);
      return VisibleProvidersNotifier(prefs);
    });

/// All providers available from the current model list, normalized and sorted.
final visibleModelProvidersProvider = Provider<AsyncValue<List<String>>>((ref) {
  final modelsAsync = ref.watch(modelsProvider);
  return modelsAsync.whenData(
    (models) => sortProviders(
      models.map((model) => canonicalModelProvider(model.provider)),
    ),
  );
});

/// Count of models by normalized provider.
final visibleModelProviderCountsProvider =
    Provider<AsyncValue<Map<String, int>>>((ref) {
      final modelsAsync = ref.watch(modelsProvider);
      return modelsAsync.whenData((models) {
        final counts = <String, int>{};
        for (final model in models) {
          final provider = canonicalModelProvider(model.provider);
          counts[provider] = (counts[provider] ?? 0) + 1;
        }
        final ordered = sortProviders(counts.keys);
        return {
          for (final provider in ordered) provider: counts[provider] ?? 0,
        };
      });
    });

/// Filtered models based on selected modality.
final filteredModelsProvider = Provider<AsyncValue<List<Model>>>((ref) {
  final modelsAsync = ref.watch(modelsProvider);
  final modality = ref.watch(selectedModalityProvider);
  final query = ref.watch(modelSearchQueryProvider).toLowerCase();
  final selectedProviders = ref.watch(selectedVisibleProvidersProvider);

  return modelsAsync.whenData((models) {
    final byProvider = selectedProviders == null
        ? models
        : models
              .where(
                (m) => selectedProviders.contains(
                  canonicalModelProvider(m.provider),
                ),
              )
              .toList();
    final filtered = modality == null
        ? byProvider
        : byProvider.where((m) => m.modality == modality).toList();
    if (query.isEmpty) return filtered;
    return filtered.where((m) => m.name.toLowerCase().contains(query)).toList();
  });
});

/// Text filter for models list.
final modelSearchQueryProvider = StateProvider<String>((ref) => '');

/// Schema for the currently selected model.
final modelSchemaProvider = FutureProvider<ModelSchema?>((ref) async {
  final modelId = ref.watch(selectedModelIdProvider);
  if (modelId == null) return null;

  final client = ref.watch(apiClientProvider);
  return client.getSchema(modelId);
});

/// The currently selected model object.
final selectedModelProvider = Provider<Model?>((ref) {
  final modelId = ref.watch(selectedModelIdProvider);
  if (modelId == null) return null;

  final modelsAsync = ref.watch(modelsProvider);
  return modelsAsync.whenOrNull(
    data: (models) => models.where((m) => m.id == modelId).firstOrNull,
  );
});

// ==================== Lifecycle State ====================

/// List of currently loaded models.
final loadedModelsProvider = FutureProvider<List<LoadedModel>>((ref) async {
  final client = ref.watch(apiClientProvider);
  return client.getLoadedModels();
});

// ==================== Jobs State ====================

/// List of download jobs.
final jobsProvider = FutureProvider<List<DownloadJob>>((ref) async {
  final client = ref.watch(apiClientProvider);
  return client.listJobs();
});

/// Active (queued or running) jobs.
final activeJobsProvider = Provider<AsyncValue<List<DownloadJob>>>((ref) {
  return ref
      .watch(jobsProvider)
      .whenData((jobs) => jobs.where((j) => j.isActive).toList());
});

// ==================== Sessions State ====================

/// List of all sessions.
final sessionsProvider = FutureProvider<List<SessionSummary>>((ref) async {
  final client = ref.watch(apiClientProvider);
  return client.listSessions();
});

/// Currently active session ID.
final activeSessionIdProvider = StateProvider<String?>((ref) => null);

/// The currently active session.
final activeSessionProvider = FutureProvider<Session?>((ref) async {
  final sessionId = ref.watch(activeSessionIdProvider);
  if (sessionId == null) return null;

  final client = ref.watch(apiClientProvider);
  return client.getSession(sessionId);
});

// ==================== Parameters State ====================

/// Current parameter values for generation.
final parametersProvider = StateProvider<Map<String, dynamic>>((ref) => {});

// ==================== Chat State ====================

/// Messages for the current chat (local state for streaming).
final chatMessagesProvider =
    StateNotifierProvider<ChatMessagesNotifier, List<Message>>((ref) {
      return ChatMessagesNotifier();
    });

/// Notifier for managing chat messages.
class ChatMessagesNotifier extends StateNotifier<List<Message>> {
  ChatMessagesNotifier() : super([]);

  void addMessage(Message message) {
    state = [...state, message];
  }

  void updateLastMessage(String content) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(content: content),
    ];
  }

  void updateLastMessageModelName(String modelName) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(modelName: modelName),
    ];
  }

  /// Update the last message with images (for image generation responses).
  void updateLastMessageWithImages(List<String> images) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(content: 'Generated image', images: images),
    ];
  }

  /// Update the last message with artifact URLs (for large images stored on server).
  void updateLastMessageWithArtifactUrls(List<String> artifactUrls) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(content: 'Generated image', artifactUrls: artifactUrls),
    ];
  }

  /// Update the last message with a 3D mesh (for 3D generation responses).
  void updateLastMessageWithMesh(String mesh) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(content: 'Generated 3D model', mesh: mesh),
    ];
  }

  /// Update the last message with mesh artifact URLs.
  void updateLastMessageWithMeshArtifactUrls(List<String> urls) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(content: 'Generated 3D model', meshArtifactUrls: urls),
    ];
  }

  void appendToLastMessage(String content) {
    if (state.isEmpty) return;
    final last = state.last;
    state = [
      ...state.sublist(0, state.length - 1),
      last.copyWith(content: last.content + content),
    ];
  }

  void clearMessages() {
    state = [];
  }

  void loadMessages(List<Message> messages) {
    state = messages;
  }
}

/// Whether a generation request is in progress.
final isGeneratingProvider = StateProvider<bool>((ref) => false);

/// Current request ID (for cancellation).
final currentRequestIdProvider = StateProvider<String?>((ref) => null);

// ==================== Auth State ====================

/// Current user profile.
final userProfileProvider = FutureProvider<UserProfile?>((ref) async {
  final token = ref.watch(authTokenProvider);
  if (token == null) return null;

  final client = ref.watch(apiClientProvider);
  try {
    return await client.getProfile();
  } catch (_) {
    return null;
  }
});

/// Whether the user is logged in.
final isLoggedInProvider = Provider<bool>((ref) {
  final token = ref.watch(authTokenProvider);
  return token != null;
});

// ==================== User Tokens State ====================

/// User's API tokens.
final userTokensProvider = FutureProvider<List<UserToken>>((ref) async {
  final isLoggedIn = ref.watch(isLoggedInProvider);
  if (!isLoggedIn) return [];

  final client = ref.watch(apiClientProvider);
  return client.listUserTokens();
});

// ==================== Provider Keys State ====================

/// User's provider API keys.
final providerKeysProvider = FutureProvider<List<ProviderKey>>((ref) async {
  final isLoggedIn = ref.watch(isLoggedInProvider);
  if (!isLoggedIn) return [];

  final client = ref.watch(apiClientProvider);
  return client.listProviderKeys();
});

// ==================== Layout State ====================

/// Layout mode (auto, locked, manual).
enum LayoutMode { auto, locked, manual }

/// Current layout mode.
final layoutModeProvider = StateProvider<LayoutMode>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  final mode = prefs.getString('layout_mode');
  return LayoutMode.values.firstWhere(
    (e) => e.name == mode,
    orElse: () => LayoutMode.auto,
  );
});

/// Selected layout (chat, studio, compact).
enum LayoutType { chat, studio, compact }

/// Current layout type.
final layoutTypeProvider = StateProvider<LayoutType>((ref) {
  final mode = ref.watch(layoutModeProvider);
  final modality = ref.watch(selectedModalityProvider);
  final prefs = ref.watch(sharedPreferencesProvider);

  if (mode == LayoutMode.locked) {
    final locked = prefs.getString('locked_layout');
    return LayoutType.values.firstWhere(
      (e) => e.name == locked,
      orElse: () => LayoutType.chat,
    );
  }

  // Auto mode: text -> chat, image/3d -> studio
  if (mode == LayoutMode.auto) {
    if (modality == 'text' || modality == null) {
      return LayoutType.chat;
    }
    return LayoutType.studio;
  }

  return LayoutType.chat;
});
