// Login page widget tests.
// Covers: TEST-MAN-012 (login flow).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/auth/login_page.dart';
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

  group('LoginPage', () {
    testWidgets('renders username and password fields', (tester) async {
      await tester.pumpWidget(
        buildTestApp(child: const LoginPage(), prefs: prefs, client: client),
      );

      expect(find.text('Username'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Sign In'), findsOneWidget);
      expect(find.text('Register'), findsOneWidget);
    });

    testWidgets('shows validation errors on empty submit', (tester) async {
      await tester.pumpWidget(
        buildTestApp(child: const LoginPage(), prefs: prefs, client: client),
      );

      // Tap Sign In without entering anything.
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      // Validation messages should appear.
      expect(find.textContaining('username'), findsWidgets);
    });

    testWidgets('shows error snackbar on login failure', (tester) async {
      client.nextError = ApiException(401, 'Unauthorized');

      await tester.pumpWidget(
        buildTestApp(child: const LoginPage(), prefs: prefs, client: client),
      );

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Username'),
        'user1',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'wrong-pass',
      );
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      expect(client.loginCalls, 1);
      // SnackBar or error text should appear.
      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('password visibility toggle works', (tester) async {
      await tester.pumpWidget(
        buildTestApp(child: const LoginPage(), prefs: prefs, client: client),
      );

      // Initially password is obscured.
      final passwordField = tester.widget<TextField>(
        find.byType(TextField).last,
      );
      expect(passwordField.obscureText, isTrue);

      // Tap visibility icon.
      await tester.tap(find.byIcon(Icons.visibility_outlined));
      await tester.pump();

      final updatedField = tester.widget<TextField>(
        find.byType(TextField).last,
      );
      expect(updatedField.obscureText, isFalse);
    });
  });
}
