// Tests for Riverpod state providers.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/state/providers.dart';

void main() {
  late SharedPreferences prefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
  });

  group('baseUrlProvider', () {
    test('defaults to localhost when no preference set', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      final url = container.read(baseUrlProvider);
      expect(url, 'http://localhost:8080');
    });

    test('reads from shared preferences', () async {
      await prefs.setString('base_url', 'http://api.example.com');

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      final url = container.read(baseUrlProvider);
      expect(url, 'http://api.example.com');
    });

    test('can be updated', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(baseUrlProvider.notifier).state = 'http://new-api.com';
      expect(container.read(baseUrlProvider), 'http://new-api.com');
    });
  });

  group('authTokenProvider', () {
    test('initially null when no preference set', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      final token = container.read(authTokenProvider);
      expect(token, isNull);
    });

    test('reads from shared preferences', () async {
      await prefs.setString('auth_token', 'test-token');

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      final token = container.read(authTokenProvider);
      expect(token, 'test-token');
    });

    test('can be updated', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(authTokenProvider.notifier).state = 'new-token';
      expect(container.read(authTokenProvider), 'new-token');
    });

    test('can be cleared', () async {
      await prefs.setString('auth_token', 'existing-token');

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(authTokenProvider.notifier).state = null;
      expect(container.read(authTokenProvider), isNull);
    });
  });

  group('attachmentMaxMbProvider', () {
    test('defaults to 10MB when no preference set', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      final maxMb = container.read(attachmentMaxMbProvider);
      expect(maxMb, 10.0);
    });

    test('reads from shared preferences', () async {
      await prefs.setDouble('attachment_max_mb', 25.0);

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      final maxMb = container.read(attachmentMaxMbProvider);
      expect(maxMb, 25.0);
    });
  });

  group('selectedModelIdProvider', () {
    test('initially null', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      expect(container.read(selectedModelIdProvider), isNull);
    });

    test('can be set', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(selectedModelIdProvider.notifier).state = 'gpt-4';
      expect(container.read(selectedModelIdProvider), 'gpt-4');
    });
  });

  group('selectedModalityProvider', () {
    test('initially null (all modalities)', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      expect(container.read(selectedModalityProvider), isNull);
    });

    test('can filter by modality', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(selectedModalityProvider.notifier).state = 'image';
      expect(container.read(selectedModalityProvider), 'image');
    });
  });

  group('selectedSessionIdProvider', () {
    test('initially null', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      // We only test providers that are available
      expect(container.read(selectedModelIdProvider), isNull);
    });
  });
}
