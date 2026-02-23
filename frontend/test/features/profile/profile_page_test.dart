// Profile page widget tests.
// Covers: TEST-MAN-013 (profile display, logout).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/profile/profile_page.dart';
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

  group('ProfilePage', () {
    testWidgets('shows sign-in prompt when not logged in', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final noAuthPrefs = await SharedPreferences.getInstance();

      await tester.pumpWidget(
        buildTestApp(
          child: const ProfilePage(),
          prefs: noAuthPrefs,
          client: client,
          loggedIn: false,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Sign in'), findsWidgets);
      expect(find.byIcon(Icons.person_outline), findsOneWidget);
    });

    testWidgets('displays username and avatar when logged in', (tester) async {
      client.profileResponse = UserProfile(
        id: 'u1',
        username: 'alice',
        email: 'alice@example.com',
        createdAt: DateTime.parse('2025-06-15T00:00:00Z'),
      );
      client.providerKeysResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const ProfilePage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('alice'), findsOneWidget);
      // CircleAvatar with first letter of username.
      expect(find.text('A'), findsOneWidget);
    });

    testWidgets('shows quick action cards', (tester) async {
      tester.view.physicalSize = const Size(1280, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      client.providerKeysResponse = [];

      await tester.pumpWidget(
        buildTestApp(
          child: const ProfilePage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      // Quick actions are near the bottom of a ListView — scroll to them.
      await tester.scrollUntilVisible(
        find.text('API Tokens'),
        200.0,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      expect(find.text('API Tokens'), findsOneWidget);
      expect(find.text('Provider Keys'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
    });

    testWidgets('shows provider key cards section', (tester) async {
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
          child: const ProfilePage(),
          prefs: prefs,
          client: client,
          loggedIn: true,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Provider API Keys'), findsOneWidget);
      // OpenAI card should be visible.
      expect(find.text('OpenAI'), findsOneWidget);
    });
  });
}
