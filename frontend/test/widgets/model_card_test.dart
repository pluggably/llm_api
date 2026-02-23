// ModelCard widget tests.
// Covers: TEST-MAN-016 (status badges), TEST-MAN-018 (loading).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/state/providers.dart';
import 'package:plugai/widgets/model_card.dart';
import 'package:pluggably_llm_client/sdk.dart';

import '../helpers/fake_api_client.dart';

void main() {
  late SharedPreferences prefs;
  late FakeLlmApiClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    client = FakeLlmApiClient();
  });

  Widget buildCard(
    Model model, {
    bool isSelected = false,
    List<LoadedModel> loaded = const [],
  }) {
    client.loadedModelsResponse = loaded;
    return ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        apiClientProvider.overrideWithValue(client),
        loadedModelsProvider.overrideWith((ref) async => loaded),
      ],
      child: MaterialApp(
        home: Scaffold(
          body: ModelCard(
            model: model,
            isSelected: isSelected,
            onTap: () {},
          ),
        ),
      ),
    );
  }

  group('ModelCard', () {
    testWidgets('shows model name and provider', (tester) async {
      final model = Model(
        id: 'gpt-4',
        name: 'GPT-4',
        provider: 'openai',
        modality: 'text',
      );

      await tester.pumpWidget(buildCard(model));
      await tester.pumpAndSettle();

      expect(find.text('GPT-4'), findsOneWidget);
      expect(find.text('openai'), findsOneWidget);
    });

    testWidgets('shows default badge when isDefault is true', (tester) async {
      final model = Model(
        id: 'gpt-4',
        name: 'GPT-4',
        provider: 'openai',
        modality: 'text',
        isDefault: true,
      );

      await tester.pumpWidget(buildCard(model));
      await tester.pumpAndSettle();

      expect(find.text('Default'), findsOneWidget);
      expect(find.byIcon(Icons.star), findsOneWidget);
    });

    testWidgets('shows Ready badge when model is loaded', (tester) async {
      final model = Model(
        id: 'llama-3',
        name: 'Llama 3',
        provider: 'meta',
        modality: 'text',
      );
      final loaded = [
        LoadedModel(
          modelId: 'llama-3',
          status: 'loaded',
          loadedAt: DateTime.now(),
        ),
      ];

      await tester.pumpWidget(buildCard(model, loaded: loaded));
      await tester.pumpAndSettle();

      expect(find.text('Ready'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('shows text modality icon', (tester) async {
      final model = Model(
        id: 'gpt-4',
        name: 'GPT-4',
        provider: 'openai',
        modality: 'text',
      );

      await tester.pumpWidget(buildCard(model));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.chat_bubble_outline), findsOneWidget);
    });

    testWidgets('shows image modality icon', (tester) async {
      final model = Model(
        id: 'sdxl',
        name: 'SDXL',
        provider: 'stabilityai',
        modality: 'image',
      );

      await tester.pumpWidget(buildCard(model));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.image_outlined), findsOneWidget);
    });

    testWidgets('shows 3D modality icon', (tester) async {
      final model = Model(
        id: 'shap-e',
        name: 'Shap-E',
        provider: 'openai',
        modality: '3d',
      );

      await tester.pumpWidget(buildCard(model));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.view_in_ar_outlined), findsOneWidget);
    });

    testWidgets('shows version when present', (tester) async {
      final model = Model(
        id: 'gpt-4',
        name: 'GPT-4',
        provider: 'openai',
        modality: 'text',
        version: '1.0',
      );

      await tester.pumpWidget(buildCard(model));
      await tester.pumpAndSettle();

      expect(find.text('v1.0'), findsOneWidget);
    });

    testWidgets('shows downloading status badge', (tester) async {
      final model = Model(
        id: 'llama-3',
        name: 'Llama 3',
        provider: 'meta',
        modality: 'text',
        status: ModelStatus.downloading,
      );

      await tester.pumpWidget(buildCard(model));
      // Use pump() instead of pumpAndSettle() because the downloading
      // status badge contains a spinner that never settles.
      await tester.pump();
      await tester.pump();

      expect(find.text('Downloading'), findsOneWidget);
    });
  });
}
