// Layout state provider tests.
// Covers: TEST-MAN-015 (layout auto-switch, lock mode).

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

  group('LayoutMode / LayoutType', () {
    test('defaults to auto mode', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      expect(container.read(layoutModeProvider), LayoutMode.auto);
    });

    test('auto mode → text modality yields chat layout', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(selectedModalityProvider.notifier).state = 'text';
      expect(container.read(layoutTypeProvider), LayoutType.chat);
    });

    test('auto mode → image modality yields studio layout', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(selectedModalityProvider.notifier).state = 'image';
      expect(container.read(layoutTypeProvider), LayoutType.studio);
    });

    test('auto mode → 3d modality yields studio layout', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(selectedModalityProvider.notifier).state = '3d';
      expect(container.read(layoutTypeProvider), LayoutType.studio);
    });

    test('auto mode → null modality yields chat layout', () {
      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      container.read(selectedModalityProvider.notifier).state = null;
      expect(container.read(layoutTypeProvider), LayoutType.chat);
    });

    test('locked mode uses stored layout preference', () async {
      await prefs.setString('layout_mode', 'locked');
      await prefs.setString('locked_layout', 'studio');

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      expect(container.read(layoutModeProvider), LayoutMode.locked);
      expect(container.read(layoutTypeProvider), LayoutType.studio);
    });

    test('locked mode defaults to chat when no stored layout', () async {
      await prefs.setString('layout_mode', 'locked');
      // No 'locked_layout' key set.

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ]);
      addTearDown(container.dispose);

      expect(container.read(layoutTypeProvider), LayoutType.chat);
    });
  });
}
