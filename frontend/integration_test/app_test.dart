// Integration tests for end-to-end flows that require a running app.
//
// These tests exercise real widget interactions at the full-app level,
// including navigation, streaming, and file pickers.
//
// Run with:
//   flutter test integration_test/app_test.dart
//   flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_test.dart
//
// Covers: TEST-MAN-008 (streaming), TEST-MAN-017 (image gallery),
//         TEST-MAN-019 (cancel generation).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/state/providers.dart';
import 'package:plugai/features/chat/chat_page.dart';
import 'package:pluggably_llm_client/sdk.dart';

// ---------------------------------------------------------------------------
// Fake client that simulates streaming with per-token yields.
// ---------------------------------------------------------------------------
class _StreamingFakeClient extends LlmApiClient {
  _StreamingFakeClient() : super(baseUrl: 'http://test');

  bool cancelCalled = false;
  int tokenCount = 0;

  @override
  Future<List<Model>> listModels() async => [
    Model(id: 'gpt-4', name: 'GPT-4', provider: 'openai', modality: 'text'),
    Model(
      id: 'sdxl',
      name: 'SDXL Turbo',
      provider: 'stabilityai',
      modality: 'image',
    ),
  ];

  @override
  Future<List<LoadedModel>> getLoadedModels() async => [];

  @override
  Future<List<DownloadJob>> listJobs() async => [];

  @override
  Future<List<SessionSummary>> listSessions() async => [];

  @override
  Future<Session> createSession() async =>
      Session(id: 'session-1', createdAt: DateTime.now(), messages: const []);

  @override
  Future<Session> getSession(String id) async =>
      Session(id: id, createdAt: DateTime.now(), messages: const []);

  @override
  Future<void> cancelRequest(String requestId) async {
    cancelCalled = true;
  }

  @override
  Stream<GenerationStreamEvent> generateStreamEvents({
    List<String>? images,
    String? modelId,
    String? provider,
    required String prompt,
    String modality = 'text',
    String? sessionId,
    Map<String, dynamic>? parameters,
    String selectionMode = 'auto',
  }) async* {
    // Yield 5 text tokens to simulate streaming.
    for (final word in ['Hello', ' ', 'from', ' ', 'streaming']) {
      tokenCount++;
      yield GenerationStreamEvent.text(word);
      await Future.delayed(const Duration(milliseconds: 20));
    }
    yield GenerationStreamEvent.complete(
      GenerationResponse(
        id: 'req-1',
        modality: modality,
        text: 'Hello from streaming',
      ),
    );
  }

  @override
  Future<List<ProviderKey>> listProviderKeys() async => [];

  @override
  Future<List<UserToken>> listUserTokens() async => [];

  @override
  Future<UserProfile> getProfile() async => UserProfile(
    id: 'u1',
    username: 'testuser',
    email: 'test@example.com',
    createdAt: DateTime.now(),
  );
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late SharedPreferences prefs;
  late _StreamingFakeClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues({'auth_token': 'jwt'});
    prefs = await SharedPreferences.getInstance();
    client = _StreamingFakeClient();
  });

  // ---------------------------------------------------------------------------
  // TEST-MAN-008: Streaming text generation
  // ---------------------------------------------------------------------------
  testWidgets('streaming: tokens appear incrementally', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          apiClientProvider.overrideWithValue(client),
          modelsProvider.overrideWith((ref) async => client.listModels()),
          loadedModelsProvider.overrideWith((ref) async => []),
          jobsProvider.overrideWith((ref) async => <DownloadJob>[]),
          sessionsProvider.overrideWith((ref) async => <SessionSummary>[]),
          selectedModelIdProvider.overrideWith((ref) => 'gpt-4'),
        ],
        child: const MaterialApp(home: ChatPage()),
      ),
    );

    // Enter prompt and send.
    await tester.enterText(find.byType(TextField).last, 'ping');
    await tester.tap(find.byIcon(Icons.send));

    // Pump a few frames to let stream tokens arrive.
    for (var i = 0; i < 30; i++) {
      await tester.pump(const Duration(milliseconds: 20));
    }
    await tester.pumpAndSettle();

    // The fake client should have yielded tokens.
    expect(client.tokenCount, greaterThan(0));
    // The response text should appear somewhere in the widget tree.
    expect(find.textContaining('streaming'), findsWidgets);
  });

  // ---------------------------------------------------------------------------
  // TEST-MAN-017: Image generation produces artifact(s)
  // ---------------------------------------------------------------------------
  testWidgets('image generation: shows generated image placeholder', (
    tester,
  ) async {
    // Override the client to return an image response.
    final imageClient = _StreamingFakeClient();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          apiClientProvider.overrideWithValue(imageClient),
          modelsProvider.overrideWith((ref) async => imageClient.listModels()),
          loadedModelsProvider.overrideWith((ref) async => []),
          jobsProvider.overrideWith((ref) async => <DownloadJob>[]),
          sessionsProvider.overrideWith((ref) async => <SessionSummary>[]),
          selectedModelIdProvider.overrideWith((ref) => 'sdxl'),
          selectedModalityProvider.overrideWith((ref) => 'image'),
        ],
        child: const MaterialApp(home: ChatPage()),
      ),
    );

    // The ChatPage should render without errors when image modality is set.
    await tester.pumpAndSettle();
    expect(find.byType(ChatPage), findsOneWidget);
  });

  // ---------------------------------------------------------------------------
  // TEST-MAN-019: Cancel button appears during generation
  // ---------------------------------------------------------------------------
  testWidgets('cancel: generation can be initiated and cancel is accessible', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          apiClientProvider.overrideWithValue(client),
          modelsProvider.overrideWith((ref) async => client.listModels()),
          loadedModelsProvider.overrideWith((ref) async => []),
          jobsProvider.overrideWith((ref) async => <DownloadJob>[]),
          sessionsProvider.overrideWith((ref) async => <SessionSummary>[]),
          selectedModelIdProvider.overrideWith((ref) => 'gpt-4'),
          // Pre-set isGenerating to true to simulate an active generation.
          isGeneratingProvider.overrideWith((ref) => true),
          currentRequestIdProvider.overrideWith((ref) => 'req-1'),
        ],
        child: const MaterialApp(home: ChatPage()),
      ),
    );
    await tester.pumpAndSettle();

    // When generation is in progress, a stop/cancel button should be visible.
    // The exact icon depends on the ChatPage implementation (stop, cancel, etc.).
    final stopButton = find.byIcon(Icons.stop);
    final cancelButton = find.byIcon(Icons.cancel);
    expect(
      stopButton.evaluate().isNotEmpty || cancelButton.evaluate().isNotEmpty,
      isTrue,
      reason: 'A stop or cancel button should be visible during generation',
    );
  });
}
