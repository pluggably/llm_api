/// Dart client SDK for the Pluggably LLM API Gateway.
library;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

/// Exception thrown when an API call fails.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  final String? detail;

  ApiException(this.statusCode, this.message, {this.detail});

  @override
  String toString() =>
      'ApiException($statusCode): $message${detail != null ? ' - $detail' : ''}';
}

/// Backwards-compatible alias.
/// Previously `ApiError` lived in `pluggably_client.dart`; new code should
/// use [ApiException] directly.
typedef ApiError = ApiException;

/// Main API client for the LLM API.
class LlmApiClient {
  static const Duration _streamHandshakeTimeout = Duration(seconds: 30);
  static const Duration _streamInactivityTimeout = Duration(seconds: 90);

  final String baseUrl;
  final http.Client _httpClient;
  String? _authToken;
  String? _apiKey;

  LlmApiClient({required this.baseUrl, http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  /// Set the authentication token for requests.
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Set the API key for requests (X-Api-Key header).
  void setApiKey(String? apiKey) {
    _apiKey = apiKey;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
        if (_apiKey != null) 'X-Api-Key': _apiKey!,
      };

  Future<T> _get<T>(String path, T Function(dynamic) fromJson) async {
    final response = await _httpClient.get(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );
    return _handleResponse(response, fromJson);
  }

  Future<T> _post<T>(
    String path,
    Map<String, dynamic> body,
    T Function(dynamic) fromJson,
  ) async {
    final response = await _httpClient.post(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return _handleResponse(response, fromJson);
  }

  Future<T> _put<T>(
    String path,
    Map<String, dynamic> body,
    T Function(dynamic) fromJson,
  ) async {
    final response = await _httpClient.put(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return _handleResponse(response, fromJson);
  }

  Future<void> _delete(String path) async {
    final response = await _httpClient.delete(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );
    if (response.statusCode >= 400) {
      _throwApiException(response);
    }
  }

  T _handleResponse<T>(http.Response response, T Function(dynamic) fromJson) {
    if (response.statusCode >= 400) {
      _throwApiException(response);
    }
    final json = jsonDecode(response.body);
    return fromJson(json);
  }

  Never _throwApiException(http.Response response) {
    String message = 'Request failed';
    String? detail;
    try {
      final json = jsonDecode(response.body);
      detail = json['detail']?.toString();
    } catch (_) {}
    throw ApiException(response.statusCode, message, detail: detail);
  }

  // ==================== Models API ====================

  /// List all available models.
  Future<List<Model>> listModels() async {
    return _get('/v1/models', (json) {
      final list = (json['models'] ?? json['data']) as List? ?? [];
      return list.map((e) => Model.fromJson(e)).toList();
    });
  }

  /// Get a specific model by ID.
  Future<Model> getModel(String modelId) async {
    return _get('/v1/models/$modelId', (json) => Model.fromJson(json));
  }

  /// Set the default model for this model's modality.
  Future<Model> setDefaultModel(String modelId) async {
    return _post(
      '/v1/models/$modelId/default',
      {},
      (json) => Model.fromJson(json),
    );
  }

  /// Get the schema for a model.
  Future<ModelSchema> getSchema(String modelId) async {
    return _get(
      '/v1/schema?model=$modelId',
      (json) => ModelSchema.fromJson(json),
    );
  }

  /// Search for models (e.g., Hugging Face catalog).
  Future<ModelSearchResponse> searchModels({
    required String query,
    String source = 'huggingface',
    String? modality,
    String? cursor,
    int? limit,
  }) async {
    final params = <String, String>{
      'query': query,
      'source': source,
      if (modality != null) 'modality': modality,
      if (cursor != null) 'cursor': cursor,
      if (limit != null) 'limit': limit.toString(),
    };
    final uri =
        Uri.parse('$baseUrl/v1/models/search').replace(queryParameters: params);
    final response = await _httpClient.get(uri, headers: _headers);
    return _handleResponse(
        response, (json) => ModelSearchResponse.fromJson(json));
  }

  // ==================== Lifecycle API ====================

  /// Get the runtime status of a specific model.
  Future<LifecycleStatus> getModelStatus(String modelId) async {
    return _get(
        '/v1/models/$modelId/status', (json) => LifecycleStatus.fromJson(json));
  }

  /// Load a model.
  Future<LoadResponse> loadModel(
    String modelId, {
    Map<String, dynamic>? config,
  }) async {
    return _post(
        '/v1/models/$modelId/load',
        {
          if (config != null) 'config': config,
        },
        (json) => LoadResponse.fromJson(json));
  }

  /// Unload a model.
  Future<void> unloadModel(String modelId, {bool force = false}) async {
    await _post('/v1/models/$modelId/unload', {'force': force}, (json) => json);
  }

  /// Get list of loaded models.
  Future<List<LoadedModel>> getLoadedModels() async {
    return _get('/v1/models/loaded', (json) {
      final list = json['models'] as List;
      return list.map((e) => LoadedModel.fromJson(e)).toList();
    });
  }

  /// Download/register a model.
  Future<Map<String, dynamic>> downloadModel({
    required String modelId,
    required String name,
    required String modality,
    required String sourceType,
    required String sourceId,
    bool installLocal = true,
    String? provider,
  }) async {
    final payload = {
      'model': {
        'id': modelId,
        'name': name,
        'version': 'latest',
        'modality': modality,
        if (provider != null) 'provider': provider,
      },
      'source': {
        'type': sourceType,
        'id': sourceId,
      },
      'options': {
        'install_local': installLocal,
      },
    };
    return _post('/v1/models/download', payload, (json) => json);
  }

  /// List all jobs.
  Future<List<DownloadJob>> listJobs() async {
    return _get('/v1/jobs', (json) {
      final list = (json['jobs'] as List?) ?? [];
      return list.map((e) => DownloadJob.fromJson(e)).toList();
    });
  }

  /// Get job status.
  Future<DownloadJob> getJob(String jobId) async {
    return _get('/v1/jobs/$jobId', (json) => DownloadJob.fromJson(json));
  }

  /// Cancel a job.
  Future<void> cancelJob(String jobId) async {
    return _delete('/v1/jobs/$jobId');
  }

  /// Get request status.
  Future<RequestStatus> getRequestStatus(String requestId) async {
    return _get(
      '/v1/requests/$requestId/status',
      (json) => RequestStatus.fromJson(json),
    );
  }

  /// Cancel a request.
  Future<void> cancelRequest(String requestId) async {
    await _post('/v1/requests/$requestId/cancel', {}, (json) => json);
  }

  // ==================== Sessions API ====================

  /// List all sessions.
  Future<List<SessionSummary>> listSessions() async {
    return _get('/v1/sessions', (json) {
      final list = (json is Map ? json['sessions'] : json) as List? ?? [];
      return list.map((e) => SessionSummary.fromJson(e)).toList();
    });
  }

  /// Create a new session.
  Future<Session> createSession() async {
    return _post('/v1/sessions', {}, (json) => Session.fromJson(json));
  }

  /// Get a session by ID.
  Future<Session> getSession(String sessionId) async {
    return _get('/v1/sessions/$sessionId', (json) => Session.fromJson(json));
  }

  /// Update a session.
  Future<Session> updateSession(String sessionId, {String? title}) async {
    return _put(
        '/v1/sessions/$sessionId',
        {
          if (title != null) 'title': title,
        },
        (json) => Session.fromJson(json));
  }

  /// Delete a session.
  Future<void> deleteSession(String sessionId) async {
    await _delete('/v1/sessions/$sessionId');
  }

  /// Regenerate the last assistant response in a session (non-streaming).
  Future<GenerationResponse> regenerate(
    String sessionId, {
    String? model,
    Map<String, dynamic>? parameters,
    String selectionMode = 'auto',
  }) async {
    return _post(
      '/v1/sessions/$sessionId/regenerate',
      {
        if (model != null) 'model': model,
        if (parameters != null) 'parameters': parameters,
        'stream': false,
        'selection_mode': selectionMode,
      },
      (json) => GenerationResponse.fromJson(json),
    );
  }

  /// Regenerate the last assistant response in a session (streaming).
  Stream<GenerationStreamEvent> regenerateStream(
    String sessionId, {
    String? model,
    Map<String, dynamic>? parameters,
    String selectionMode = 'auto',
  }) async* {
    final body = {
      if (model != null) 'model': model,
      if (parameters != null) 'parameters': parameters,
      'stream': true,
      'selection_mode': selectionMode,
    };

    final request = http.Request(
      'POST',
      Uri.parse('$baseUrl/v1/sessions/$sessionId/regenerate'),
    );
    request.headers.addAll(_headers);
    request.body = jsonEncode(body);

    final streamedResponse =
        await _httpClient.send(request).timeout(_streamHandshakeTimeout);

    if (streamedResponse.statusCode >= 400) {
      final body = await streamedResponse.stream.bytesToString();
      String? detail;
      try {
        final json = jsonDecode(body);
        detail = json['detail']?.toString();
      } catch (_) {}
      throw ApiException(
        streamedResponse.statusCode,
        'Regenerate stream request failed',
        detail: detail,
      );
    }

    var sseBuffer = '';
    try {
      await for (final chunk in streamedResponse.stream
          .transform(utf8.decoder)
          .timeout(_streamInactivityTimeout)) {
        // Buffer partial lines across chunks so split SSE events are reassembled
        final lines = (sseBuffer + chunk).split('\n');
        sseBuffer =
            lines.removeLast(); // trailing incomplete line for next chunk
        for (final line in lines) {
          if (line.startsWith('data: ')) {
            final data = line.substring(6).trim();
            if (data == '[DONE]') return;
            try {
              final json = jsonDecode(data);
              if (json is Map<String, dynamic>) {
                if (json['event'] == 'model_selected') {
                  yield GenerationStreamEvent.modelSelected(
                    modelId: json['model']?.toString(),
                    modelName: json['model_name']?.toString(),
                    fallbackUsed: json['fallback_used'] as bool? ?? false,
                    fallbackReason: json['fallback_reason']?.toString(),
                  );
                  continue;
                }
                if (json['error'] != null) {
                  throw ApiException(
                    500,
                    'Stream error',
                    detail: json['error']?.toString(),
                  );
                }
                if (json['output'] != null || json['modality'] != null) {
                  yield GenerationStreamEvent.complete(
                    GenerationResponse.fromJson(json),
                  );
                } else if (json['choices'] != null) {
                  final content =
                      json['choices']?[0]?['delta']?['content']?.toString();
                  if (content != null && content.isNotEmpty) {
                    yield GenerationStreamEvent.text(content);
                  }
                }
              }
            } catch (e) {
              if (e is ApiException) rethrow;
            }
          }
        }
      }
    } on TimeoutException {
      throw ApiException(
        504,
        'Stream timed out',
        detail: 'No stream activity for ${_streamInactivityTimeout.inSeconds}s',
      );
    }
  }

  // ==================== Generation API ====================

  /// Generate a completion (non-streaming).
  Future<GenerationResponse> generate({
    String? modelId,
    String? provider,
    required String prompt,
    String modality = 'text',
    String? sessionId,
    List<String>? images,
    Map<String, dynamic>? parameters,
    String selectionMode = 'auto',
  }) async {
    final body = {
      if (modelId != null) 'model': modelId,
      if (provider != null) 'provider': provider,
      'modality': modality,
      'input': {
        'prompt': prompt,
        if (images != null && images.isNotEmpty) 'images': images,
      },
      if (sessionId != null) 'session_id': sessionId,
      if (parameters != null) 'parameters': parameters,
      'selection_mode': selectionMode,
    };
    return _post(
      '/v1/generate',
      body,
      (json) => GenerationResponse.fromJson(json),
    );
  }

  /// Generate a streaming completion (yields text tokens for text, full response for images).
  ///
  /// For text generation, yields individual tokens as they arrive.
  /// For image/3D generation, yields a single GenerationResponse when complete.
  Stream<GenerationStreamEvent> generateStreamEvents({
    String? modelId,
    String? provider,
    required String prompt,
    String modality = 'text',
    String? sessionId,
    List<String>? images,
    Map<String, dynamic>? parameters,
    String selectionMode = 'auto',
  }) async* {
    final body = {
      if (modelId != null) 'model': modelId,
      if (provider != null) 'provider': provider,
      'modality': modality,
      'input': {
        'prompt': prompt,
        if (images != null && images.isNotEmpty) 'images': images,
      },
      'stream': true,
      if (sessionId != null) 'session_id': sessionId,
      if (parameters != null) 'parameters': parameters,
      'selection_mode': selectionMode,
    };

    final request = http.Request('POST', Uri.parse('$baseUrl/v1/generate'));
    request.headers.addAll(_headers);
    request.body = jsonEncode(body);

    final streamedResponse =
        await _httpClient.send(request).timeout(_streamHandshakeTimeout);

    if (streamedResponse.statusCode >= 400) {
      final body = await streamedResponse.stream.bytesToString();
      String? detail;
      try {
        final json = jsonDecode(body);
        detail = json['detail']?.toString();
      } catch (_) {}
      throw ApiException(
        streamedResponse.statusCode,
        'Stream request failed',
        detail: detail,
      );
    }

    var sseBuffer = '';
    try {
      await for (final chunk in streamedResponse.stream
          .transform(utf8.decoder)
          .timeout(_streamInactivityTimeout)) {
        // Buffer partial lines across chunks so split SSE events are reassembled
        final lines = (sseBuffer + chunk).split('\n');
        sseBuffer =
            lines.removeLast(); // trailing incomplete line for next chunk
        for (final line in lines) {
          if (line.startsWith('data: ')) {
            final data = line.substring(6).trim();
            if (data == '[DONE]') {
              return;
            }
            try {
              final json = jsonDecode(data);
              if (json is Map<String, dynamic>) {
                if (json['event'] == 'model_selected') {
                  yield GenerationStreamEvent.modelSelected(
                    modelId: json['model']?.toString(),
                    modelName: json['model_name']?.toString(),
                    fallbackUsed: json['fallback_used'] as bool? ?? false,
                    fallbackReason: json['fallback_reason']?.toString(),
                  );
                  continue;
                }
                if (json['error'] != null) {
                  throw ApiException(
                    500,
                    'Stream error',
                    detail: json['error']?.toString(),
                  );
                }
                // Check if this is a full response (has output field) or a streaming chunk
                if (json['output'] != null || json['modality'] != null) {
                  // Full response for image/3D
                  yield GenerationStreamEvent.complete(
                    GenerationResponse.fromJson(json),
                  );
                } else if (json['choices'] != null) {
                  // Streaming text chunk
                  final content =
                      json['choices']?[0]?['delta']?['content']?.toString();
                  if (content != null && content.isNotEmpty) {
                    yield GenerationStreamEvent.text(content);
                  }
                }
              }
            } catch (e) {
              if (e is ApiException) rethrow;
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    } on TimeoutException {
      throw ApiException(
        504,
        'Stream timed out',
        detail: 'No stream activity for ${_streamInactivityTimeout.inSeconds}s',
      );
    }
  }

  /// Generate a streaming completion (legacy - yields only text tokens).
  @Deprecated('Use generateStreamEvents instead for multimodal support')
  Stream<String> generateStream({
    required String modelId,
    required String prompt,
    String modality = 'text',
    String? sessionId,
    Map<String, dynamic>? parameters,
  }) async* {
    final body = {
      'model': modelId,
      'modality': modality,
      'input': {'prompt': prompt},
      'stream': true,
      if (sessionId != null) 'session_id': sessionId,
      if (parameters != null) 'parameters': parameters,
    };

    final request = http.Request('POST', Uri.parse('$baseUrl/v1/generate'));
    request.headers.addAll(_headers);
    request.body = jsonEncode(body);

    final streamedResponse = await _httpClient.send(request);

    if (streamedResponse.statusCode >= 400) {
      final body = await streamedResponse.stream.bytesToString();
      String? detail;
      try {
        final json = jsonDecode(body);
        detail = json['detail']?.toString();
      } catch (_) {}
      throw ApiException(
        streamedResponse.statusCode,
        'Stream request failed',
        detail: detail,
      );
    }

    await for (final chunk in streamedResponse.stream.transform(utf8.decoder)) {
      // Parse SSE format
      for (final line in chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          final data = line.substring(6).trim();
          if (data == '[DONE]') {
            return;
          }
          String? content;
          try {
            final json = jsonDecode(data);
            if (json is Map) {
              if (json['error'] != null) {
                throw ApiException(
                  500,
                  'Stream error',
                  detail: json['error']?.toString(),
                );
              }
              content = json['choices']?[0]?['delta']?['content']?.toString();
            } else if (json is String) {
              content = json;
            }
          } catch (_) {
            // Fall back to plain token payloads.
            content = data;
          }
          if (content != null && content.isNotEmpty) {
            yield content;
          }
        }
      }
    }
  }

  // ==================== Auth API ====================

  /// Register a new user with an optional invite token.
  Future<AuthResponse> register({
    String? username,
    String? email,
    required String password,
    String? inviteToken,
  }) async {
    final identifier = (username ?? email)?.trim();
    if (identifier == null || identifier.isEmpty) {
      throw ArgumentError('username or email is required');
    }
    return _post(
        '/v1/users/register',
        {
          'username': identifier,
          if (email != null) 'email': email,
          'password': password,
          if (inviteToken != null) 'invite_token': inviteToken,
        },
        (json) => AuthResponse.fromJson(json));
  }

  /// Login with username/email and password.
  Future<AuthResponse> login({
    String? username,
    String? email,
    required String password,
  }) async {
    final identifier = (username ?? email)?.trim();
    if (identifier == null || identifier.isEmpty) {
      throw ArgumentError('username or email is required');
    }
    return _post(
        '/v1/users/login',
        {
          'username': identifier,
          if (email != null) 'email': email,
          'password': password,
        },
        (json) => AuthResponse.fromJson(json));
  }

  /// Logout (invalidate token).
  Future<void> logout() async {
    // No backend logout endpoint, just clear token locally
    _authToken = null;
  }

  /// Get current user profile.
  Future<UserProfile> getProfile() async {
    return _get('/v1/users/me', (json) => UserProfile.fromJson(json));
  }

  /// Update user profile.
  Future<UserProfile> updateProfile({
    String? displayName,
  }) async {
    return _put(
      '/v1/users/me',
      {'display_name': displayName},
      (json) => UserProfile.fromJson(json),
    );
  }

  // ==================== User API Tokens ====================

  /// List user's API tokens.
  Future<List<UserToken>> listUserTokens() async {
    return _get('/v1/users/tokens', (json) {
      final list = json as List;
      return list.map((e) => UserToken.fromJson(e)).toList();
    });
  }

  /// Create a new API token.
  Future<UserTokenWithSecret> createUserToken({String? name}) async {
    return _post(
        '/v1/users/tokens',
        {
          if (name != null) 'name': name,
        },
        (json) => UserTokenWithSecret.fromJson(json));
  }

  /// Revoke an API token.
  Future<void> revokeUserToken(String tokenId) async {
    await _delete('/v1/users/tokens/$tokenId');
  }

  // ==================== Provider Keys ====================

  /// List user's provider keys.
  Future<List<ProviderKey>> listProviderKeys() async {
    return _get('/v1/users/provider-keys', (json) {
      final list = json as List;
      return list.map((e) => ProviderKey.fromJson(e)).toList();
    });
  }

  /// Add a provider key.
  Future<ProviderKey> addProviderKey({
    required String provider,
    String? apiKey,
    String credentialType = 'api_key',
    String? endpoint,
    String? oauthToken,
    String? serviceAccountJson,
  }) async {
    return _post(
        '/v1/users/provider-keys',
        {
          'provider': provider,
          'credential_type': credentialType,
          if (apiKey != null) 'api_key': apiKey,
          if (endpoint != null) 'endpoint': endpoint,
          if (oauthToken != null) 'oauth_token': oauthToken,
          if (serviceAccountJson != null)
            'service_account_json': serviceAccountJson,
        },
        (json) => ProviderKey.fromJson(json));
  }

  /// Remove a provider key.
  Future<void> removeProviderKey(String provider) async {
    await _delete('/v1/users/provider-keys/$provider');
  }

  /// Dispose of the HTTP client.
  void dispose() {
    _httpClient.close();
  }

  /// Health check endpoint.
  Future<String> getHealth() async {
    return _get('/health', (json) => json['status']?.toString() ?? 'ok');
  }

  /// Version metadata endpoint.
  Future<VersionInfo> getVersion() async {
    return _get('/version', (json) => VersionInfo.fromJson(json));
  }
}
