// Models page widget tests.
// Covers: TEST-MAN-004 (models list), NEW-001–005 (model features).

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/models/models_page.dart';
import 'package:plugai/state/providers.dart';
import 'package:pluggably_llm_client/sdk.dart';

import '../../helpers/fake_api_client.dart';
import '../../helpers/pump_app.dart';

void main() {
  late SharedPreferences prefs;
  late FakeLlmApiClient client;

  final sampleModels = [
    Model(id: 'gpt-4', name: 'GPT-4', provider: 'openai', modality: 'text'),
    Model(
      id: 'sdxl',
      name: 'SDXL Turbo',
      provider: 'stabilityai',
      modality: 'image',
    ),
    Model(
      id: 'shap-e',
      name: 'Shap-E',
      provider: 'openai',
      modality: '3d',
    ),
    Model(
      id: 'llama-3',
      name: 'Llama 3.1',
      provider: 'meta',
      modality: 'text',
    ),
  ];

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    client = FakeLlmApiClient()..modelsResponse = sampleModels;
  });

  group('ModelsPage', () {
    testWidgets('displays all models in grid', (tester) async {
      await tester.pumpWidget(
        buildTestApp(child: const ModelsPage(), prefs: prefs, client: client),
      );
      await tester.pumpAndSettle();

      expect(find.text('GPT-4'), findsOneWidget);
      expect(find.text('SDXL Turbo'), findsOneWidget);
      expect(find.text('Shap-E'), findsOneWidget);
      expect(find.text('Llama 3.1'), findsOneWidget);
    });

    testWidgets('modality filter chips are shown', (tester) async {
      await tester.pumpWidget(
        buildTestApp(child: const ModelsPage(), prefs: prefs, client: client),
      );
      await tester.pumpAndSettle();

      expect(find.text('All'), findsOneWidget);
      expect(find.text('Text'), findsOneWidget);
      expect(find.text('Image'), findsOneWidget);
      expect(find.text('3D'), findsOneWidget);
    });

    testWidgets('search filters models by name', (tester) async {
      await tester.pumpWidget(
        buildTestApp(
          child: const ModelsPage(),
          prefs: prefs,
          client: client,
          overrides: [
            modelSearchQueryProvider.overrideWith((ref) => 'llama'),
          ],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Llama 3.1'), findsOneWidget);
      expect(find.text('GPT-4'), findsNothing);
      expect(find.text('SDXL Turbo'), findsNothing);
    });

    testWidgets('no duplicates when same model listed once', (tester) async {
      // Regression guard: each model ID should appear exactly once.
      await tester.pumpWidget(
        buildTestApp(child: const ModelsPage(), prefs: prefs, client: client),
      );
      await tester.pumpAndSettle();

      expect(find.text('GPT-4'), findsOneWidget);
      expect(find.text('Llama 3.1'), findsOneWidget);
    });

    testWidgets('shows Add Model button', (tester) async {
      await tester.pumpWidget(
        buildTestApp(child: const ModelsPage(), prefs: prefs, client: client),
      );
      await tester.pumpAndSettle();

      expect(find.text('Add Model'), findsOneWidget);
    });

    testWidgets('shows Hosted/Local badges by provider', (tester) async {
      client.modelsResponse = [
        Model(
          id: 'hf-1',
          name: 'HF Hosted Model',
          provider: 'huggingface',
          modality: 'text',
        ),
        Model(
          id: 'local-1',
          name: 'Local Installed Model',
          provider: 'local',
          modality: 'text',
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(child: const ModelsPage(), prefs: prefs, client: client),
      );
      await tester.pumpAndSettle();

      expect(find.text('Hosted'), findsOneWidget);
      expect(find.text('Local'), findsOneWidget);
    });
  });
}
