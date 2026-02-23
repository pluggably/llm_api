// Sessions rail widget tests.
// Covers: TEST-MAN-009 (session switching), MVP-003 (session history).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/sessions/sessions_rail.dart';
import 'package:plugai/state/providers.dart';
import 'package:pluggably_llm_client/sdk.dart';

import '../../helpers/fake_api_client.dart';
import '../../helpers/pump_app.dart';

void main() {
  late SharedPreferences prefs;
  late FakeLlmApiClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    client = FakeLlmApiClient();
  });

  group('SessionsRail', () {
    testWidgets('shows New button', (tester) async {
      client.sessionsResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const Scaffold(body: SessionsRail()),
          prefs: prefs,
          client: client,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.add), findsOneWidget);
    });

    testWidgets('lists sessions and highlights active', (tester) async {
      client.sessionsResponse = [
        SessionSummary(
          id: 's1',
          title: 'Chat about Dart',
          createdAt: DateTime.parse('2026-02-01T10:00:00Z'),
        ),
        SessionSummary(
          id: 's2',
          title: 'Image generation',
          createdAt: DateTime.parse('2026-02-02T12:00:00Z'),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const Scaffold(body: SessionsRail()),
          prefs: prefs,
          client: client,
          overrides: [
            activeSessionIdProvider.overrideWith((ref) => 's1'),
          ],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Chat about Dart'), findsOneWidget);
      expect(find.text('Image generation'), findsOneWidget);

      // Active session should be selected (bold).
      final activeTile = tester.widget<ListTile>(
        find.ancestor(
          of: find.text('Chat about Dart'),
          matching: find.byType(ListTile),
        ),
      );
      expect(activeTile.selected, isTrue);
    });

    testWidgets('rename icon is shown for each session', (tester) async {
      client.sessionsResponse = [
        SessionSummary(
          id: 's1',
          title: 'My Chat',
          createdAt: DateTime.now(),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const Scaffold(body: SessionsRail()),
          prefs: prefs,
          client: client,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.edit), findsOneWidget);
    });

    testWidgets('untitled sessions show placeholder', (tester) async {
      client.sessionsResponse = [
        SessionSummary(
          id: 's1',
          title: null,
          createdAt: DateTime.now(),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const Scaffold(body: SessionsRail()),
          prefs: prefs,
          client: client,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Untitled'), findsOneWidget);
    });
  });
}
