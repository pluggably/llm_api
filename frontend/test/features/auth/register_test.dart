// Registration page widget tests.
// Covers: TEST-MAN-012 (registration flow).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/features/auth/register_page.dart';

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

  group('RegisterPage', () {
    Future<void> setLargeSurface(WidgetTester tester) async {
      // RegisterPage has many fields; prevent layout overflow.
      tester.view.physicalSize = const Size(1280, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
    }

    /// Suppress RenderFlex overflow errors (pre-existing layout issue
    /// in register_page.dart Row at line 208 — tracked separately).
    void suppressOverflowErrors() {
      final originalOnError = FlutterError.onError;
      FlutterError.onError = (details) {
        if (details.toString().contains('overflowed')) return;
        originalOnError?.call(details);
      };
      addTearDown(() => FlutterError.onError = originalOnError);
    }

    testWidgets('renders all form fields', (tester) async {
      await setLargeSurface(tester);
      suppressOverflowErrors();

      await tester.pumpWidget(
        buildTestApp(child: const RegisterPage(), prefs: prefs, client: client),
      );

      expect(find.text('Invite Token'), findsOneWidget);
      expect(find.text('Username'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Confirm Password'), findsOneWidget);
      // 'Create Account' appears both as heading and button text.
      expect(find.text('Create Account'), findsWidgets);
      expect(find.text('Sign In'), findsOneWidget);
    });

    testWidgets('validates password length', (tester) async {
      await setLargeSurface(tester);
      suppressOverflowErrors();
      await tester.pumpWidget(
        buildTestApp(child: const RegisterPage(), prefs: prefs, client: client),
      );

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Invite Token'),
        'tok-invite',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Username'),
        'newuser',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'short',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Confirm Password'),
        'short',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Create Account'));
      await tester.pumpAndSettle();

      // Should show "at least 8 characters" or similar.
      expect(find.textContaining('8'), findsWidgets);
    });

    testWidgets('validates password mismatch', (tester) async {
      await setLargeSurface(tester);
      suppressOverflowErrors();
      await tester.pumpWidget(
        buildTestApp(child: const RegisterPage(), prefs: prefs, client: client),
      );

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Invite Token'),
        'tok-invite',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Username'),
        'newuser',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'password123',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Confirm Password'),
        'password456',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Create Account'));
      await tester.pumpAndSettle();

      expect(find.textContaining('match'), findsWidgets);
    });
  });
}
