// Basic widget tests for PlugAI frontend.

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/main.dart';
import 'package:plugai/state/state.dart';

void main() {
  testWidgets('App renders correctly', (WidgetTester tester) async {
    // Set up shared preferences mock
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    // Build our app and trigger a frame.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: const PlugAIApp(),
      ),
    );

    // Wait for async operations
    await tester.pumpAndSettle();

    // Verify that the app renders (Models page is the default)
    expect(find.text('Models'), findsWidgets);
  });
}

