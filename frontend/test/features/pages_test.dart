// Tests for feature pages.
// Uses a larger surface size to avoid layout overflow issues in tests.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/state/providers.dart';
import 'package:plugai/features/models/models_page.dart';
import 'package:plugai/features/sessions/sessions_rail.dart';
import 'package:plugai/features/settings/settings_page.dart';

void main() {
  late SharedPreferences prefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
  });

  group('ModelsPage', () {
    testWidgets('displays loading indicator initially', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(prefs),
          ],
          child: const MaterialApp(
            home: ModelsPage(),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('displays modality filter chips', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(prefs),
          ],
          child: const MaterialApp(
            home: ModelsPage(),
          ),
        ),
      );

      await tester.pump();

      expect(find.text('All'), findsOneWidget);
      expect(find.text('Text'), findsOneWidget);
      expect(find.text('Image'), findsOneWidget);
    });
  });

  group('SessionsRail', () {
    testWidgets('renders new session button', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(prefs),
          ],
          child: const MaterialApp(
            home: Scaffold(body: SessionsRail()),
          ),
        ),
      );

      await tester.pump();

      expect(find.byIcon(Icons.add), findsOneWidget);
    });
  });

  group('SettingsPage', () {
    testWidgets('renders without errors', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(prefs),
          ],
          child: const MaterialApp(
            home: SettingsPage(),
          ),
        ),
      );

      await tester.pump();

      // Just verify the page renders
      expect(find.byType(SettingsPage), findsOneWidget);
      expect(find.text('Test Connection'), findsOneWidget);
    });
  });
}
