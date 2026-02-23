/// Helper that wraps a widget with Riverpod, SharedPreferences, and a
/// [FakeLlmApiClient] — ready for widget testing.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:plugai/state/providers.dart';
import 'package:pluggably_llm_client/sdk.dart';

import 'fake_api_client.dart';

/// Pumps [child] inside a [ProviderScope] wired to [prefs] and [client].
///
/// Additional [overrides] are merged after the standard ones.
Widget buildTestApp({
  required Widget child,
  required SharedPreferences prefs,
  required FakeLlmApiClient client,
  List<Override> overrides = const [],
  bool loggedIn = false,
  Size surfaceSize = const Size(1280, 800),
}) {
  return ProviderScope(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      apiClientProvider.overrideWithValue(client),
      // Override FutureProviders that hit the network.
      modelsProvider.overrideWith((ref) async => client.modelsResponse),
      loadedModelsProvider.overrideWith(
        (ref) async => client.loadedModelsResponse,
      ),
      jobsProvider.overrideWith((ref) async => client.jobsResponse),
      sessionsProvider.overrideWith((ref) async => client.sessionsResponse),
      userProfileProvider.overrideWith((ref) async {
        if (!loggedIn) return null;
        return client.profileResponse ??
            UserProfile(
              id: 'user-1',
              username: 'testuser',
              email: 'test@example.com',
              createdAt: DateTime.parse('2026-01-01T00:00:00Z'),
            );
      }),
      providerKeysProvider.overrideWith(
        (ref) async => client.providerKeysResponse,
      ),
      userTokensProvider.overrideWith((ref) async => client.userTokensResponse),
      if (loggedIn) authTokenProvider.overrideWith((ref) => 'fake-jwt-token'),
      ...overrides,
    ],
    child: MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(size: surfaceSize),
        child: child,
      ),
    ),
  );
}
