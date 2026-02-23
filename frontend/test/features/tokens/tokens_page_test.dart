// API tokens page widget tests.
// Covers: TEST-MAN-014 (token management).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/tokens/tokens_page.dart';
import 'package:pluggably_llm_client/sdk.dart';

import '../../helpers/fake_api_client.dart';
import '../../helpers/pump_app.dart';

void main() {
  late SharedPreferences prefs;
  late FakeLlmApiClient client;

  setUp(() async {
    SharedPreferences.setMockInitialValues({'auth_token': 'jwt'});
    prefs = await SharedPreferences.getInstance();
    client = FakeLlmApiClient();
  });

  group('TokensPage', () {
    testWidgets('shows empty state when no tokens', (tester) async {
      client.userTokensResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const TokensPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No API tokens'), findsOneWidget);
      expect(find.text('Create Token'), findsOneWidget);
    });

    testWidgets('lists existing tokens', (tester) async {
      client.userTokensResponse = [
        UserToken(
          id: 't1',
          name: 'CI Pipeline',
          createdAt: DateTime.parse('2026-02-01T00:00:00Z'),
        ),
        UserToken(
          id: 't2',
          name: 'Local Dev',
          createdAt: DateTime.parse('2026-02-10T00:00:00Z'),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const TokensPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('CI Pipeline'), findsOneWidget);
      expect(find.text('Local Dev'), findsOneWidget);
      // Each token has a revoke icon.
      expect(find.byIcon(Icons.delete_outline), findsNWidgets(2));
    });

    testWidgets('create-token FAB opens dialog', (tester) async {
      client.userTokensResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const TokensPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create Token'));
      await tester.pumpAndSettle();

      expect(find.text('Create API Token'), findsOneWidget);
      expect(find.text('Token Name (optional)'), findsOneWidget);
      expect(find.text('Create'), findsOneWidget);
    });

    testWidgets('revoke icon shows confirmation dialog', (tester) async {
      client.userTokensResponse = [
        UserToken(
          id: 't1',
          name: 'CI Pipeline',
          createdAt: DateTime.now(),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const TokensPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.delete_outline));
      await tester.pumpAndSettle();

      expect(find.text('Revoke Token'), findsOneWidget);
      expect(find.textContaining('CI Pipeline'), findsWidgets);
      expect(find.text('Revoke'), findsOneWidget);
    });
  });
}
