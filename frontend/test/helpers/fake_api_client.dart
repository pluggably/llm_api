/// Shared fake [LlmApiClient] for widget tests.
///
/// Override fields to control return values per test.
/// Set [nextError] to simulate API failures.
library;

import 'package:pluggably_llm_client/sdk.dart';

class FakeLlmApiClient extends LlmApiClient {
  FakeLlmApiClient() : super(baseUrl: 'http://test');

  // ── Error simulation ──────────────────────────────────────────────────
  ApiException? nextError;

  // ── Auth ───────────────────────────────────────────────────────────────
  AuthResponse? loginResponse;
  int loginCalls = 0;
  String? lastLoginUsername;

  AuthResponse? registerResponse;
  int registerCalls = 0;
  String? lastRegisterInviteToken;

  bool logoutCalled = false;

  UserProfile? profileResponse;

  // ── Models ─────────────────────────────────────────────────────────────
  List<Model> modelsResponse = [];
  List<LoadedModel> loadedModelsResponse = [];
  List<DownloadJob> jobsResponse = [];

  // ── Sessions ───────────────────────────────────────────────────────────
  List<SessionSummary> sessionsResponse = [];
  Session? createSessionResponse;
  Session? getSessionResponse;
  Session? updateSessionResponse;
  int createSessionCalls = 0;
  String? lastUpdateTitle;

  // ── Keys ───────────────────────────────────────────────────────────────
  List<ProviderKey> providerKeysResponse = [];
  ProviderKey? addProviderKeyResponse;
  String? lastAddedProvider;
  String? lastAddedCredentialType;
  String? lastRemovedProvider;

  // ── Tokens ─────────────────────────────────────────────────────────────
  List<UserToken> userTokensResponse = [];
  UserTokenWithSecret? createUserTokenResponse;
  String? lastCreatedTokenName;
  String? lastRevokedTokenId;

  // ── Generation ─────────────────────────────────────────────────────────
  String? lastSessionId;

  // =====================================================================
  // Method overrides
  // =====================================================================

  @override
  Future<AuthResponse> login({
    String? username,
    String? email,
    required String password,
  }) async {
    loginCalls++;
    lastLoginUsername = username ?? email;
    if (nextError != null) {
      final err = nextError!;
      nextError = null;
      throw err;
    }
    return loginResponse!;
  }

  @override
  Future<AuthResponse> register({
    String? username,
    String? email,
    required String password,
    String? inviteToken,
  }) async {
    registerCalls++;
    lastRegisterInviteToken = inviteToken;
    if (nextError != null) {
      final err = nextError!;
      nextError = null;
      throw err;
    }
    return registerResponse!;
  }

  @override
  Future<void> logout() async {
    logoutCalled = true;
  }

  @override
  Future<UserProfile> getProfile() async {
    if (nextError != null) {
      final err = nextError!;
      nextError = null;
      throw err;
    }
    return profileResponse ??
        UserProfile(
          id: 'user-1',
          username: 'test',
          email: 'test@example.com',
          createdAt: DateTime.parse('2026-01-01T00:00:00Z'),
        );
  }

  @override
  Future<List<Model>> listModels() async {
    return modelsResponse;
  }

  @override
  Future<List<LoadedModel>> getLoadedModels() async {
    return loadedModelsResponse;
  }

  @override
  Future<List<DownloadJob>> listJobs() async {
    return jobsResponse;
  }

  @override
  Future<List<SessionSummary>> listSessions() async {
    return sessionsResponse;
  }

  @override
  Future<Session> createSession() async {
    createSessionCalls++;
    return createSessionResponse ??
        Session(
          id: 'session-new',
          createdAt: DateTime.now(),
          messages: const [],
        );
  }

  @override
  Future<Session> getSession(String sessionId) async {
    if (nextError != null) {
      final err = nextError!;
      nextError = null;
      throw err;
    }
    return getSessionResponse ??
        Session(id: sessionId, createdAt: DateTime.now(), messages: const []);
  }

  @override
  Future<Session> updateSession(String sessionId, {String? title}) async {
    lastUpdateTitle = title;
    return updateSessionResponse ??
        Session(
          id: sessionId,
          title: title,
          createdAt: DateTime.now(),
          messages: const [],
        );
  }

  @override
  Future<List<ProviderKey>> listProviderKeys() async {
    return providerKeysResponse;
  }

  @override
  Future<ProviderKey> addProviderKey({
    required String provider,
    String? apiKey,
    String credentialType = 'api_key',
    String? endpoint,
    String? oauthToken,
    String? serviceAccountJson,
  }) async {
    lastAddedProvider = provider;
    lastAddedCredentialType = credentialType;
    if (nextError != null) {
      final err = nextError!;
      nextError = null;
      throw err;
    }
    return addProviderKeyResponse ??
        ProviderKey(
          id: 'key-new',
          provider: provider,
          credentialType: credentialType,
          maskedKey: '****${apiKey?.substring(apiKey.length - 4) ?? '1234'}',
          createdAt: DateTime.now(),
        );
  }

  @override
  Future<void> removeProviderKey(String provider) async {
    lastRemovedProvider = provider;
  }

  @override
  Future<List<UserToken>> listUserTokens() async {
    return userTokensResponse;
  }

  @override
  Future<UserTokenWithSecret> createUserToken({String? name}) async {
    lastCreatedTokenName = name;
    return createUserTokenResponse ??
        UserTokenWithSecret(
          id: 'tok-new',
          name: name,
          createdAt: DateTime.now(),
          token: 'plg_test_secret_token_value',
        );
  }

  @override
  Future<void> revokeUserToken(String tokenId) async {
    lastRevokedTokenId = tokenId;
  }

  @override
  Stream<GenerationStreamEvent> generateStreamEvents({
    List<String>? images,
    String? modelId,
    String? provider,
    required String prompt,
    String modality = 'text',
    String? sessionId,
    Map<String, dynamic>? parameters,
    String selectionMode = 'auto',
  }) async* {
    lastSessionId = sessionId;
    final response = GenerationResponse(
      id: 'req-1',
      modality: modality,
      text: 'Test response',
    );
    yield GenerationStreamEvent.complete(response);
  }
}
