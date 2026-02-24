library pluggably_llm_client;

import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiError implements Exception {
  final int statusCode;
  final String message;
  final String? code;

  ApiError(this.statusCode, this.message, {this.code});

  @override
  String toString() => 'ApiError($statusCode${code != null ? ", $code" : ""}): $message';
}

class GenerateInput {
  final String? prompt;
  final List<String>? images;
  final String? mesh;

  GenerateInput({this.prompt, this.images, this.mesh});

  Map<String, dynamic> toJson() => {
        if (prompt != null) 'prompt': prompt,
        if (images != null) 'images': images,
        if (mesh != null) 'mesh': mesh,
      };
}

class GenerateParameters {
  final double? temperature;
  final int? maxTokens;
  final String? format;

  GenerateParameters({this.temperature, this.maxTokens, this.format});

  Map<String, dynamic> toJson() => {
        if (temperature != null) 'temperature': temperature,
        if (maxTokens != null) 'max_tokens': maxTokens,
        if (format != null) 'format': format,
      };
}

class GenerateRequest {
  final String? model;
  final String? sessionId;
  final Map<String, dynamic>? stateTokens;
  final String modality;
  final GenerateInput input;
  final GenerateParameters? parameters;
  final bool stream;
  final String? selectionMode;

  GenerateRequest({
    this.model,
    this.sessionId,
    this.stateTokens,
    required this.modality,
    required this.input,
    this.parameters,
    this.stream = false,
    this.selectionMode,
  });

  Map<String, dynamic> toJson() => {
        if (model != null) 'model': model,
        if (sessionId != null) 'session_id': sessionId,
        if (stateTokens != null) 'state_tokens': stateTokens,
        'modality': modality,
        'input': input.toJson(),
        if (parameters != null) 'parameters': parameters!.toJson(),
        'stream': stream,
      if (selectionMode != null) 'selection_mode': selectionMode,
      };
}

class GenerateResponse {
  final String requestId;
  final String model;
  final String modality;
  final String? sessionId;
  final Map<String, dynamic>? stateTokens;
  final Map<String, dynamic> output;
  final Map<String, dynamic> usage;

  GenerateResponse({
    required this.requestId,
    required this.model,
    required this.modality,
    required this.output,
    required this.usage,
    this.sessionId,
    this.stateTokens,
  });

  factory GenerateResponse.fromJson(Map<String, dynamic> json) => GenerateResponse(
        requestId: json['request_id'],
        model: json['model'],
        modality: json['modality'],
        output: (json['output'] as Map<String, dynamic>?) ?? {},
        usage: (json['usage'] as Map<String, dynamic>?) ?? {},
        sessionId: json['session_id'],
        stateTokens: (json['state_tokens'] as Map<String, dynamic>?),
      );
}

class Session {
  final String id;
  final String status;
  final String? createdAt;
  final String? lastUsedAt;

  Session({required this.id, required this.status, this.createdAt, this.lastUsedAt});

  factory Session.fromJson(Map<String, dynamic> json) => Session(
        id: json['id'],
        status: json['status'],
        createdAt: json['created_at'],
        lastUsedAt: json['last_used_at'],
      );
}

class SessionList {
  final List<Session> sessions;

  SessionList(this.sessions);

  factory SessionList.fromJson(Map<String, dynamic> json) => SessionList(
        (json['sessions'] as List<dynamic>? ?? [])
            .map((item) => Session.fromJson(item as Map<String, dynamic>))
            .toList(),
      );
}

class ModelInfo {
  final String id;
  final String name;
  final String version;
  final String modality;
  final String? provider;
  final bool isDefault;

  ModelInfo({
    required this.id,
    required this.name,
    required this.version,
    required this.modality,
    this.provider,
    this.isDefault = false,
  });

  factory ModelInfo.fromJson(Map<String, dynamic> json) => ModelInfo(
    id: json['id'],
    name: json['name'],
    version: json['version'],
    modality: json['modality'],
    provider: json['provider'],
    isDefault: json['is_default'] ?? false,
  );
}

class ModelCatalog {
  final List<ModelInfo> models;

  ModelCatalog(this.models);

  factory ModelCatalog.fromJson(Map<String, dynamic> json) => ModelCatalog(
    (json['models'] as List<dynamic>? ?? [])
    .map((item) => ModelInfo.fromJson(item as Map<String, dynamic>))
    .toList(),
  );
}

class ProviderStatus {
  final String name;
  final bool configured;
  final List<String> supportedModalities;

  ProviderStatus({
    required this.name,
    required this.configured,
    required this.supportedModalities,
  });

  factory ProviderStatus.fromJson(Map<String, dynamic> json) => ProviderStatus(
    name: json['name'],
    configured: json['configured'] ?? false,
    supportedModalities: (json['supported_modalities'] as List<dynamic>? ?? [])
    .map((item) => item.toString())
    .toList(),
  );
}

class ProvidersResponse {
  final List<ProviderStatus> providers;

  ProvidersResponse(this.providers);

  factory ProvidersResponse.fromJson(Map<String, dynamic> json) => ProvidersResponse(
    (json['providers'] as List<dynamic>? ?? [])
    .map((item) => ProviderStatus.fromJson(item as Map<String, dynamic>))
    .toList(),
  );
}

class ModelDownloadRequest {
  final Map<String, dynamic> model;
  final Map<String, dynamic> source;
  final Map<String, dynamic>? options;

  ModelDownloadRequest({required this.model, required this.source, this.options});

  Map<String, dynamic> toJson() => {
    'model': model,
    'source': source,
    if (options != null) 'options': options,
  };
}

class PluggablyClient {
  final String baseUrl;
  final String apiKey;
  final http.Client _client;

  PluggablyClient({required this.baseUrl, required this.apiKey, http.Client? client})
      : _client = client ?? http.Client();

  Future<Map<String, dynamic>> _request(String method, String path, {Map<String, dynamic>? body}) async {
    final url = Uri.parse('${baseUrl.replaceAll(RegExp(r"/+$"), "")}$path');
    final headers = {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
    };

    http.Response response;
    if (method == 'GET') {
      response = await _client.get(url, headers: headers);
    } else if (method == 'DELETE') {
      response = await _client.delete(url, headers: headers);
    } else {
      response = await _client.post(url, headers: headers, body: jsonEncode(body ?? {}));
    }

    if (response.statusCode >= 400) {
      final payload = jsonDecode(response.body);
      final detail = payload is Map<String, dynamic> ? payload['detail'] : null;
      final code = detail is Map<String, dynamic> ? detail['code']?.toString() : null;
      final message = detail is Map<String, dynamic>
          ? detail['message']?.toString()
          : payload is Map<String, dynamic>
              ? payload['message']?.toString() ?? response.body
              : response.body;
      throw ApiError(response.statusCode, message ?? response.body, code: code);
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<GenerateResponse> generate(GenerateRequest request) async {
    final payload = await _request('POST', '/v1/generate', body: request.toJson());
    return GenerateResponse.fromJson(payload);
  }

  Future<GenerateResponse> generateWithSession(String sessionId, GenerateRequest request) async {
    final payload = await _request('POST', '/v1/sessions/$sessionId/generate', body: request.toJson());
    return GenerateResponse.fromJson(payload);
  }

  Future<Session> createSession() async {
    final payload = await _request('POST', '/v1/sessions');
    return Session.fromJson(payload);
  }

  Future<SessionList> listSessions() async {
    final payload = await _request('GET', '/v1/sessions');
    return SessionList.fromJson(payload);
  }

  Future<Session> getSession(String sessionId) async {
    final payload = await _request('GET', '/v1/sessions/$sessionId');
    return Session.fromJson(payload);
  }

  Future<Session> resetSession(String sessionId) async {
    final payload = await _request('POST', '/v1/sessions/$sessionId/reset');
    return Session.fromJson(payload);
  }

  Future<Session> closeSession(String sessionId) async {
    final payload = await _request('DELETE', '/v1/sessions/$sessionId');
    return Session.fromJson(payload);
  }

  Future<ModelCatalog> listModels({String? modality}) async {
    final path = modality == null ? '/v1/models' : '/v1/models?modality=$modality';
    final payload = await _request('GET', path);
    return ModelCatalog.fromJson(payload);
  }

  Future<ModelInfo> getModel(String modelId) async {
    final payload = await _request('GET', '/v1/models/$modelId');
    return ModelInfo.fromJson(payload);
  }

  Future<ProvidersResponse> listProviders() async {
    final payload = await _request('GET', '/v1/providers');
    return ProvidersResponse.fromJson(payload);
  }

  Future<Map<String, dynamic>> getSchema() async {
    return _request('GET', '/v1/schema');
  }

  Future<Map<String, dynamic>> downloadModel(ModelDownloadRequest request) async {
    return _request('POST', '/v1/models/download', body: request.toJson());
  }

  Future<Map<String, dynamic>> getJob(String jobId) async {
    return _request('GET', '/v1/jobs/$jobId');
  }

  Future<Map<String, dynamic>> cancelJob(String jobId) async {
    return _request('DELETE', '/v1/jobs/$jobId');
  }
}
