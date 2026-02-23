// Provider keys page widget tests.
// Covers: TEST-MAN-010 (key management), TEST-MAN-011 (credential types),
//         MVP-002 (masked keys).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/keys/keys_page.dart';
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

  group('KeysPage', () {
    testWidgets('shows empty state when no keys', (tester) async {
      client.providerKeysResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const KeysPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No provider keys'), findsOneWidget);
      expect(find.text('Add Key'), findsOneWidget);
    });

    testWidgets('lists keys with masked display', (tester) async {
      client.providerKeysResponse = [
        ProviderKey(
          id: 'k1',
          provider: 'openai',
          credentialType: 'api_key',
          maskedKey: 'sk-****abcd',
          createdAt: DateTime.parse('2026-01-15T00:00:00Z'),
        ),
        ProviderKey(
          id: 'k2',
          provider: 'anthropic',
          credentialType: 'api_key',
          maskedKey: 'sk-ant-****wxyz',
          createdAt: DateTime.parse('2026-01-16T00:00:00Z'),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const KeysPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('openai'), findsOneWidget);
      expect(find.text('anthropic'), findsOneWidget);
      // Masked keys shown in subtitle.
      expect(find.textContaining('sk-****abcd'), findsOneWidget);
      expect(find.textContaining('sk-ant-****wxyz'), findsOneWidget);
    });

    testWidgets('add-key FAB opens dialog with provider dropdown',
        (tester) async {
      client.providerKeysResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const KeysPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      // Tap the FAB.
      await tester.tap(find.text('Add Key'));
      await tester.pumpAndSettle();

      // Dialog should show provider dropdown.
      expect(find.text('Provider'), findsOneWidget);
      expect(find.text('Credential Type'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Add'), findsOneWidget);
    });

    testWidgets('delete icon shows confirmation dialog', (tester) async {
      client.providerKeysResponse = [
        ProviderKey(
          id: 'k1',
          provider: 'openai',
          credentialType: 'api_key',
          maskedKey: 'sk-****abcd',
          createdAt: DateTime.now(),
        ),
      ];

      await tester.pumpWidget(
        buildTestApp(
          child: const KeysPage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.delete_outline));
      await tester.pumpAndSettle();

      expect(find.text('Remove Key'), findsOneWidget);
      expect(find.textContaining('openai'), findsWidgets);
      expect(find.text('Remove'), findsOneWidget);
    });
  });
}
