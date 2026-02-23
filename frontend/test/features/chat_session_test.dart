import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/chat/chat_page.dart';
import 'package:plugai/state/state.dart';
import 'package:pluggably_llm_client/sdk.dart';

class _FakeLlmApiClient extends LlmApiClient {
  _FakeLlmApiClient() : super(baseUrl: 'http://test');

  int createSessionCalls = 0;
  String? lastSessionId;

  @override
  Future<Session> createSession() async {
    createSessionCalls += 1;
    return Session(
      id: 'session-1',
      createdAt: DateTime.parse('2026-02-14T00:00:00Z'),
      messages: const [],
    );
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
    lastSessionId = sessionId;
    final response = GenerationResponse(
      id: 'req-1',
      modality: modality,
      text: 'ok',
    );
    yield GenerationStreamEvent.complete(response);
  }
}

void main() {
  testWidgets('creates a new session when none is active', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final fakeClient = _FakeLlmApiClient();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          apiClientProvider.overrideWithValue(fakeClient),
          selectedModelIdProvider.overrideWith((ref) => 'model-1'),
        ],
        child: const MaterialApp(home: ChatPage()),
      ),
    );

    await tester.enterText(find.byType(TextField).last, 'hello');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(fakeClient.createSessionCalls, 1);
    expect(fakeClient.lastSessionId, 'session-1');

    final context = tester.element(find.byType(ChatPage));
    final container = ProviderScope.containerOf(context);
    expect(container.read(activeSessionIdProvider), 'session-1');
  });

  testWidgets('shows provider submenus in model picker', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final fakeClient = _FakeLlmApiClient();

    final models = [
      const Model(
        id: 'openai-gpt-4o-mini',
        name: 'GPT-4o mini',
        provider: 'openai',
        modality: 'text',
      ),
      const Model(
        id: 'hf-tinyllama',
        name: 'TinyLlama',
        provider: 'huggingface',
        modality: 'text',
      ),
      const Model(
        id: 'local-llama',
        name: 'Local Llama',
        provider: 'local',
        modality: 'text',
      ),
    ];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          apiClientProvider.overrideWithValue(fakeClient),
          modelsProvider.overrideWith((ref) async => models),
        ],
        child: const MaterialApp(home: ChatPage()),
      ),
    );

    await tester.pumpAndSettle();

    await tester.tap(find.byType(OutlinedButton).first);
    await tester.pumpAndSettle();

    expect(find.text('OpenAI (1)'), findsOneWidget);
    expect(find.text('Hugging Face (1)'), findsOneWidget);
    expect(find.text('Local (1)'), findsOneWidget);
  });
}
