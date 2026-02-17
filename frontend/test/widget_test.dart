// Basic widget tests for PlugAI frontend.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/main.dart';
import 'package:plugai/state/state.dart';

void main() {
  testWidgets('App renders correctly', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

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

    // Verify that unauthenticated users land on Login
    expect(find.text('Sign in to continue'), findsOneWidget);
  });
}

