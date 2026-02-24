/// Data models for the LLM API client.
library;

import 'package:equatable/equatable.dart';

/// An artifact stored on the server (for large images/meshes).
class Artifact extends Equatable {
  final String id;
  final String type;
  final String url;
  final DateTime? expiresAt;

  const Artifact({
    required this.id,
    required this.type,
    required this.url,
    this.expiresAt,
  });

  factory Artifact.fromJson(Map<String, dynamic> json) {
    return Artifact(
      id: json['id'] as String,
      type: json['type'] as String,
      url: json['url'] as String,
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'] as String)
          : null,
    );
  }

  @override
  List<Object?> get props => [id, type, url, expiresAt];
}

/// Represents a model available in the API.
class Model extends Equatable {
  final String id;
  final String name;
  final String provider;
  final String modality;
  final String? version;
  final String? description;
  final ModelStatus status;
  final bool isDefault;
  final AvailabilityInfo? availability;

  const Model({
    required this.id,
    required this.name,
    required this.provider,
    required this.modality,
    this.version,
    this.description,
    this.status = ModelStatus.ready,
    this.isDefault = false,
    this.availability,
  });

  factory Model.fromJson(Map<String, dynamic> json) {
    return Model(
      id: json['id'] as String,
      name: json['name'] as String? ?? json['id'] as String,
      provider: json['provider'] as String? ?? 'unknown',
      modality: json['modality'] as String? ?? 'text',
      version: json['version'] as String?,
      description: json['description'] as String?,
      isDefault: json['is_default'] as bool? ?? false,
      availability: json['availability'] != null
          ? AvailabilityInfo.fromJson(
              json['availability'] as Map<String, dynamic>,
            )
          : null,
      status: ModelStatus.values.firstWhere(
        (e) => e.name == (json['status'] as String?),
        orElse: () => ModelStatus.ready,
      ),
    );
  }

  @override
  List<Object?> get props => [
        id,
        name,
        provider,
        modality,
        version,
        description,
        status,
        isDefault,
        availability,
      ];
}

/// Provider credit/usage status.
class CreditsStatus extends Equatable {
  final String provider;
  final String status; // available | exhausted | unknown
  final double? remaining;
  final DateTime? resetAt;

  const CreditsStatus({
    required this.provider,
    required this.status,
    this.remaining,
    this.resetAt,
  });

  factory CreditsStatus.fromJson(Map<String, dynamic> json) {
    return CreditsStatus(
      provider: json['provider'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      remaining: (json['remaining'] as num?)?.toDouble(),
      resetAt: json['reset_at'] != null
          ? DateTime.parse(json['reset_at'] as String)
          : null,
    );
  }

  @override
  List<Object?> get props => [provider, status, remaining, resetAt];
}

/// Model availability for a user.
class AvailabilityInfo extends Equatable {
  final String provider;
  final String access; // available | locked | unknown
  final CreditsStatus? creditsStatus;

  const AvailabilityInfo({
    required this.provider,
    required this.access,
    this.creditsStatus,
  });

  factory AvailabilityInfo.fromJson(Map<String, dynamic> json) {
    return AvailabilityInfo(
      provider: json['provider'] as String? ?? '',
      access: json['access'] as String? ?? 'unknown',
      creditsStatus: json['credits_status'] != null
          ? CreditsStatus.fromJson(
              json['credits_status'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  @override
  List<Object?> get props => [provider, access, creditsStatus];
}

/// Selection metadata for a generation response.
class SelectionInfo extends Equatable {
  final String selectedModel;
  final String? selectedProvider;
  final bool fallbackUsed;
  final String? fallbackReason;

  const SelectionInfo({
    required this.selectedModel,
    this.selectedProvider,
    this.fallbackUsed = false,
    this.fallbackReason,
  });

  factory SelectionInfo.fromJson(Map<String, dynamic> json) {
    return SelectionInfo(
      selectedModel: json['selected_model'] as String? ?? '',
      selectedProvider: json['selected_provider'] as String?,
      fallbackUsed: json['fallback_used'] as bool? ?? false,
      fallbackReason: json['fallback_reason'] as String?,
    );
  }

  @override
  List<Object?> get props =>
      [selectedModel, selectedProvider, fallbackUsed, fallbackReason];
}

/// Status of a model.
enum ModelStatus { ready, downloading, failed, loading, loaded, busy, unloaded }

/// Status of a download job.
enum JobStatus { queued, running, completed, failed, cancelled }

/// A download job.
class DownloadJob extends Equatable {
  final String jobId;
  final String modelId;
  final JobStatus status;
  final double progressPct;
  final String? error;
  final DateTime createdAt;

  const DownloadJob({
    required this.jobId,
    required this.modelId,
    required this.status,
    required this.progressPct,
    this.error,
    required this.createdAt,
  });

  factory DownloadJob.fromJson(Map<String, dynamic> json) {
    return DownloadJob(
      jobId: json['job_id'] as String,
      modelId: json['model_id'] as String,
      status: _parseJobStatus(json['status'] as String),
      progressPct: (json['progress_pct'] as num?)?.toDouble() ?? 0.0,
      error: json['error'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  bool get isActive =>
      status == JobStatus.queued || status == JobStatus.running;

  @override
  List<Object?> get props =>
      [jobId, modelId, status, progressPct, error, createdAt];
}

JobStatus _parseJobStatus(String status) {
  switch (status) {
    case 'queued':
      return JobStatus.queued;
    case 'running':
      return JobStatus.running;
    case 'completed':
      return JobStatus.completed;
    case 'failed':
      return JobStatus.failed;
    case 'cancelled':
      return JobStatus.cancelled;
    default:
      return JobStatus.queued;
  }
}

/// Result from model search.
class ModelSearchResult extends Equatable {
  final String id;
  final String name;
  final List<String> tags;
  final List<String> modalityHints;
  final int? downloads;
  final DateTime? lastModified;

  const ModelSearchResult({
    required this.id,
    required this.name,
    this.tags = const [],
    this.modalityHints = const [],
    this.downloads,
    this.lastModified,
  });

  factory ModelSearchResult.fromJson(Map<String, dynamic> json) {
    return ModelSearchResult(
      id: json['id'] as String,
      name: json['name'] as String? ?? json['id'] as String,
      tags: (json['tags'] as List?)?.cast<String>() ?? const [],
      modalityHints:
          (json['modality_hints'] as List?)?.cast<String>() ?? const [],
      downloads: json['downloads'] as int?,
      lastModified: json['last_modified'] != null
          ? DateTime.tryParse(json['last_modified'] as String)
          : null,
    );
  }

  String get downloadsFormatted {
    if (downloads == null) return '';
    if (downloads! >= 1000000) {
      return '${(downloads! / 1000000).toStringAsFixed(1)}M';
    }
    if (downloads! >= 1000) {
      return '${(downloads! / 1000).toStringAsFixed(1)}K';
    }
    return downloads.toString();
  }

  @override
  List<Object?> get props =>
      [id, name, tags, modalityHints, downloads, lastModified];
}

/// Paginated model search response.
class ModelSearchResponse extends Equatable {
  final List<ModelSearchResult> results;
  final String? nextCursor;

  const ModelSearchResponse({required this.results, this.nextCursor});

  factory ModelSearchResponse.fromJson(Map<String, dynamic> json) {
    final list = (json['results'] as List?) ?? const [];
    return ModelSearchResponse(
      results: list.map((e) => ModelSearchResult.fromJson(e)).toList(),
      nextCursor: json['next_cursor'] as String?,
    );
  }

  @override
  List<Object?> get props => [results, nextCursor];
}

/// Schema for model parameters.
class ModelSchema extends Equatable {
  final String modelId;
  final String? version;
  final Map<String, SchemaParameter> parameters;

  const ModelSchema({
    required this.modelId,
    this.version,
    required this.parameters,
  });

  factory ModelSchema.fromJson(Map<String, dynamic> json) {
    final properties = json['properties'] as Map<String, dynamic>? ?? {};
    final parameters = <String, SchemaParameter>{};
    for (final entry in properties.entries) {
      parameters[entry.key] = SchemaParameter.fromJson(
        entry.key,
        entry.value as Map<String, dynamic>,
      );
    }
    return ModelSchema(
      modelId: json['model_id'] as String? ?? '',
      version: json['version'] as String?,
      parameters: parameters,
    );
  }

  @override
  List<Object?> get props => [modelId, version, parameters];
}

/// A parameter in the model schema.
class SchemaParameter extends Equatable {
  final String name;
  final String type;
  final String? title;
  final String? description;
  final dynamic defaultValue;
  final num? minimum;
  final num? maximum;
  final List<dynamic>? enumValues;
  final bool required;

  const SchemaParameter({
    required this.name,
    required this.type,
    this.title,
    this.description,
    this.defaultValue,
    this.minimum,
    this.maximum,
    this.enumValues,
    this.required = false,
  });

  factory SchemaParameter.fromJson(String name, Map<String, dynamic> json) {
    return SchemaParameter(
      name: name,
      type: json['type'] as String? ?? 'string',
      title: json['title'] as String?,
      description: json['description'] as String?,
      defaultValue: json['default'],
      minimum: json['minimum'] as num?,
      maximum: json['maximum'] as num?,
      enumValues: json['enum'] as List?,
      required: json['required'] as bool? ?? false,
    );
  }

  @override
  List<Object?> get props => [
        name,
        type,
        title,
        description,
        defaultValue,
        minimum,
        maximum,
        enumValues,
        required,
      ];
}

/// Event from a streaming generation request.
/// Can be either a text token or a complete response (for images/3D).
class GenerationStreamEvent {
  final String? textToken;
  final GenerationResponse? response;
  final String? modelId;
  final String? modelName;

  /// Whether the server transparently switched to a different model.
  final bool fallbackUsed;

  /// Why the fallback happened: 'rate_limited_tier', 'rate_limited_local',
  /// 'quota_exceeded', 'provider_overloaded', etc.
  final String? fallbackReason;

  const GenerationStreamEvent._({
    this.textToken,
    this.response,
    this.modelId,
    this.modelName,
    this.fallbackUsed = false,
    this.fallbackReason,
  });

  /// Create a text token event.
  factory GenerationStreamEvent.text(String token) =>
      GenerationStreamEvent._(textToken: token);

  /// Create a complete response event (for images/3D).
  factory GenerationStreamEvent.complete(GenerationResponse response) =>
      GenerationStreamEvent._(response: response);

  /// Create a model-selected event (early metadata).
  factory GenerationStreamEvent.modelSelected({
    String? modelId,
    String? modelName,
    bool fallbackUsed = false,
    String? fallbackReason,
  }) =>
      GenerationStreamEvent._(
        modelId: modelId,
        modelName: modelName,
        fallbackUsed: fallbackUsed,
        fallbackReason: fallbackReason,
      );

  /// True if this is a text token.
  bool get isText => textToken != null;

  /// True if this is a complete response.
  bool get isComplete => response != null;

  /// True if this is a model-selected metadata event.
  bool get isModelSelected => modelId != null || modelName != null;
}

/// Response from a generation request.
class GenerationResponse extends Equatable {
  final String id;
  final String modality;
  final String? text;
  final List<String>? images;
  final String? mesh;
  final List<Artifact>? artifacts;
  final String? finishReason;
  final int? promptTokens;
  final int? completionTokens;
  final SelectionInfo? selection;
  final CreditsStatus? creditsStatus;

  const GenerationResponse({
    required this.id,
    required this.modality,
    this.text,
    this.images,
    this.mesh,
    this.artifacts,
    this.finishReason,
    this.promptTokens,
    this.completionTokens,
    this.selection,
    this.creditsStatus,
  });

  /// Convenience getter for text content (for backwards compatibility)
  String get content => text ?? '';

  /// Get image artifact URLs (for large images stored as artifacts)
  List<String> get imageArtifactUrls {
    if (artifacts == null) return [];
    return artifacts!
        .where((a) => a.type == 'image')
        .map((a) => a.url)
        .toList();
  }

  /// Get mesh artifact URLs (for 3D outputs stored as artifacts)
  List<String> get meshArtifactUrls {
    if (artifacts == null) return [];
    return artifacts!.where((a) => a.type == 'mesh').map((a) => a.url).toList();
  }

  factory GenerationResponse.fromJson(Map<String, dynamic> json) {
    // Handle our backend format: output.text, output.images, output.mesh, output.artifacts
    final output = json['output'] as Map<String, dynamic>?;
    String? text;
    List<String>? images;
    String? mesh;
    List<Artifact>? artifacts;

    String? finishReason;

    if (output != null) {
      text = output['text'] as String?;
      final imageList = output['images'] as List?;
      if (imageList != null) {
        images = imageList.cast<String>();
      }
      mesh = output['mesh'] as String?;

      // Parse artifacts (for large images/meshes stored separately)
      final artifactList = output['artifacts'] as List?;
      if (artifactList != null && artifactList.isNotEmpty) {
        artifacts = artifactList
            .map((a) => Artifact.fromJson(a as Map<String, dynamic>))
            .toList();
      }
    } else {
      // Fall back to OpenAI-style choices format
      final choices = json['choices'] as List?;
      if (choices?.isNotEmpty == true) {
        text = choices![0]['message']?['content'] as String? ??
            choices[0]['text'] as String? ??
            choices[0]['delta']?['content'] as String?;
        finishReason = choices[0]['finish_reason'] as String?;
      }
    }

    return GenerationResponse(
      id: json['request_id'] as String? ?? json['id'] as String? ?? '',
      modality: json['modality'] as String? ?? 'text',
      text: text,
      images: images,
      mesh: mesh,
      artifacts: artifacts,
      finishReason: finishReason,
      promptTokens: json['usage']?['prompt_tokens'] as int?,
      completionTokens: json['usage']?['completion_tokens'] as int?,
      selection: json['selection'] != null
          ? SelectionInfo.fromJson(json['selection'] as Map<String, dynamic>)
          : null,
      creditsStatus: json['credits_status'] != null
          ? CreditsStatus.fromJson(
              json['credits_status'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  @override
  List<Object?> get props => [
        id,
        modality,
        text,
        images,
        mesh,
        artifacts,
        finishReason,
        promptTokens,
        completionTokens,
        selection,
        creditsStatus,
      ];
}

/// A chat session.
class Session extends Equatable {
  final String id;
  final String? title;
  final String? modelId;
  final List<Message> messages;
  final int messageCount;
  final DateTime createdAt;
  final DateTime? lastUsedAt;

  const Session({
    required this.id,
    this.title,
    this.modelId,
    this.messages = const [],
    this.messageCount = 0,
    required this.createdAt,
    this.lastUsedAt,
  });

  factory Session.fromJson(Map<String, dynamic> json) {
    final messageList = json['messages'] as List? ?? [];
    return Session(
      id: json['id'] as String,
      title: json['title'] as String?,
      modelId: json['model_id'] as String?,
      messages: messageList.map((e) => Message.fromJson(e)).toList(),
      messageCount: json['message_count'] as int? ?? 0,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastUsedAt: json['last_used_at'] != null
          ? DateTime.parse(json['last_used_at'] as String)
          : null,
    );
  }

  @override
  List<Object?> get props => [
        id,
        title,
        modelId,
        messages,
        messageCount,
        createdAt,
        lastUsedAt,
      ];
}

/// Summary of a session for listing.
class SessionSummary extends Equatable {
  final String id;
  final String? title;
  final int messageCount;
  final DateTime createdAt;
  final DateTime? lastUsedAt;

  const SessionSummary({
    required this.id,
    this.title,
    this.messageCount = 0,
    required this.createdAt,
    this.lastUsedAt,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    return SessionSummary(
      id: json['id'] as String,
      title: json['title'] as String?,
      messageCount: json['message_count'] as int? ?? 0,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastUsedAt: json['last_used_at'] != null
          ? DateTime.parse(json['last_used_at'] as String)
          : null,
    );
  }

  @override
  List<Object?> get props => [id, title, messageCount, createdAt, lastUsedAt];
}

/// A message in a chat session.
class Message extends Equatable {
  final String id;
  final String role;
  final String content;
  final List<String>? images;
  final List<String>? artifactUrls;
  final List<String>? meshArtifactUrls;
  final String? mesh;
  final String? modelName;
  final DateTime createdAt;

  const Message({
    required this.id,
    required this.role,
    required this.content,
    this.images,
    this.artifactUrls,
    this.meshArtifactUrls,
    this.mesh,
    this.modelName,
    required this.createdAt,
  });

  /// Check if message has any images (inline or artifacts)
  bool get hasImages =>
      (images != null && images!.isNotEmpty) ||
      (artifactUrls != null && artifactUrls!.isNotEmpty);

  bool get hasMeshArtifacts =>
      (meshArtifactUrls != null && meshArtifactUrls!.isNotEmpty);

  /// Create a copy with updated content (for streaming)
  Message copyWith({
    String? id,
    String? role,
    String? content,
    List<String>? images,
    List<String>? artifactUrls,
    List<String>? meshArtifactUrls,
    String? mesh,
    String? modelName,
    DateTime? createdAt,
  }) {
    return Message(
      id: id ?? this.id,
      role: role ?? this.role,
      content: content ?? this.content,
      images: images ?? this.images,
      artifactUrls: artifactUrls ?? this.artifactUrls,
      meshArtifactUrls: meshArtifactUrls ?? this.meshArtifactUrls,
      mesh: mesh ?? this.mesh,
      modelName: modelName ?? this.modelName,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  factory Message.fromJson(Map<String, dynamic> json) {
    final imageList = json['images'] as List?;
    final artifactUrlList = json['artifact_urls'] as List?;
    final meshArtifactUrlList = json['mesh_artifact_urls'] as List?;
    return Message(
      id: json['id'] as String? ?? '',
      role: json['role'] as String,
      content: json['content'] as String? ?? '',
      images: imageList?.cast<String>(),
      artifactUrls: artifactUrlList?.cast<String>(),
      meshArtifactUrls: meshArtifactUrlList?.cast<String>(),
      mesh: json['mesh'] as String?,
      modelName: json['model_name'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'role': role,
        'content': content,
        if (images != null) 'images': images,
        if (artifactUrls != null) 'artifact_urls': artifactUrls,
        if (meshArtifactUrls != null) 'mesh_artifact_urls': meshArtifactUrls,
        if (mesh != null) 'mesh': mesh,
        if (modelName != null) 'model_name': modelName,
        'created_at': createdAt.toIso8601String(),
      };

  @override
  List<Object?> get props => [
        id,
        role,
        content,
        images,
        artifactUrls,
        meshArtifactUrls,
        mesh,
        modelName,
        createdAt,
      ];
}

/// Model lifecycle status (per-model runtime status).
class LifecycleStatus extends Equatable {
  final String modelId;
  final String runtimeStatus;
  final int queueDepth;

  const LifecycleStatus({
    required this.modelId,
    required this.runtimeStatus,
    this.queueDepth = 0,
  });

  factory LifecycleStatus.fromJson(Map<String, dynamic> json) {
    return LifecycleStatus(
      modelId: json['model_id'] as String,
      runtimeStatus: json['runtime_status'] as String,
      queueDepth: json['queue_depth'] as int? ?? 0,
    );
  }

  @override
  List<Object?> get props => [modelId, runtimeStatus, queueDepth];
}

/// Response from loading a model.
class LoadResponse extends Equatable {
  final String modelId;
  final String status;
  final String? message;

  const LoadResponse({
    required this.modelId,
    required this.status,
    this.message,
  });

  factory LoadResponse.fromJson(Map<String, dynamic> json) {
    return LoadResponse(
      modelId: json['model_id'] as String? ?? '',
      status: json['status'] as String? ?? 'loading',
      message: json['message'] as String?,
    );
  }

  @override
  List<Object?> get props => [modelId, status, message];
}

/// A loaded model.
class LoadedModel extends Equatable {
  final String modelId;
  final String status;
  final DateTime? loadedAt;

  const LoadedModel({
    required this.modelId,
    required this.status,
    this.loadedAt,
  });

  factory LoadedModel.fromJson(Map<String, dynamic> json) {
    return LoadedModel(
      modelId: json['model_id'] as String,
      status: json['status'] as String? ?? 'loaded',
      loadedAt: json['loaded_at'] != null
          ? DateTime.parse(json['loaded_at'] as String)
          : null,
    );
  }

  @override
  List<Object?> get props => [modelId, status, loadedAt];
}

/// Status of a request.
class RequestStatus extends Equatable {
  final String requestId;
  final String status;
  final int? queuePosition;
  final int? estimatedWaitSeconds;

  const RequestStatus({
    required this.requestId,
    required this.status,
    this.queuePosition,
    this.estimatedWaitSeconds,
  });

  factory RequestStatus.fromJson(Map<String, dynamic> json) {
    return RequestStatus(
      requestId: json['request_id'] as String,
      status: json['status'] as String,
      queuePosition: json['queue_position'] as int?,
      estimatedWaitSeconds: json['estimated_wait_seconds'] as int?,
    );
  }

  @override
  List<Object?> get props => [
        requestId,
        status,
        queuePosition,
        estimatedWaitSeconds,
      ];
}

/// Authentication response.
class AuthResponse extends Equatable {
  final String accessToken;
  final String tokenType;
  final int? expiresIn;
  final UserProfile? user;

  const AuthResponse({
    required this.accessToken,
    this.tokenType = 'bearer',
    this.expiresIn,
    this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    final token = json['access_token'] ?? json['token'];
    return AuthResponse(
      accessToken: token as String? ?? '',
      tokenType: json['token_type'] as String? ?? 'bearer',
      expiresIn: json['expires_in'] as int?,
      user: json['user'] != null ? UserProfile.fromJson(json['user']) : null,
    );
  }

  @override
  List<Object?> get props => [accessToken, tokenType, expiresIn, user];
}

/// User profile.
class UserProfile extends Equatable {
  final String id;
  final String username;
  final String? email;
  final Map<String, dynamic> preferences;
  final DateTime? createdAt;

  const UserProfile({
    required this.id,
    required this.username,
    this.email,
    this.preferences = const {},
    this.createdAt,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    final createdAt = json['created_at'] as String?;
    final identifier =
        (json['username'] as String?) ?? (json['email'] as String?) ?? '';
    return UserProfile(
      id: json['id'] as String,
      username: identifier,
      email: (json['email'] as String?) ?? identifier,
      preferences: json['preferences'] as Map<String, dynamic>? ?? {},
      createdAt: createdAt != null ? DateTime.parse(createdAt) : null,
    );
  }

  @override
  List<Object?> get props => [id, username, email, preferences, createdAt];
}

/// User API token (without secret).
class UserToken extends Equatable {
  final String id;
  final String? name;
  final DateTime createdAt;
  final DateTime? lastUsedAt;

  const UserToken({
    required this.id,
    this.name,
    required this.createdAt,
    this.lastUsedAt,
  });

  factory UserToken.fromJson(Map<String, dynamic> json) {
    return UserToken(
      id: json['id'] as String,
      name: json['name'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastUsedAt: json['last_used_at'] != null
          ? DateTime.parse(json['last_used_at'] as String)
          : null,
    );
  }

  @override
  List<Object?> get props => [id, name, createdAt, lastUsedAt];
}

/// User API token with secret (returned only on creation).
class UserTokenWithSecret extends UserToken {
  final String token;

  const UserTokenWithSecret({
    required super.id,
    super.name,
    required super.createdAt,
    super.lastUsedAt,
    required this.token,
  });

  factory UserTokenWithSecret.fromJson(Map<String, dynamic> json) {
    return UserTokenWithSecret(
      id: json['id'] as String,
      name: json['name'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastUsedAt: json['last_used_at'] != null
          ? DateTime.parse(json['last_used_at'] as String)
          : null,
      token: json['token'] as String,
    );
  }

  @override
  List<Object?> get props => [...super.props, token];
}

/// Provider API key (stored for user).
class ProviderKey extends Equatable {
  final String id;
  final String provider;
  final String credentialType;
  final String maskedKey;
  final DateTime createdAt;

  const ProviderKey({
    required this.id,
    required this.provider,
    this.credentialType = 'api_key',
    required this.maskedKey,
    required this.createdAt,
  });

  factory ProviderKey.fromJson(Map<String, dynamic> json) {
    return ProviderKey(
      id: json['id'] as String,
      provider: json['provider'] as String,
      credentialType: json['credential_type'] as String? ?? 'api_key',
      maskedKey: json['masked_key'] as String? ?? '****',
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  @override
  List<Object?> get props =>
      [id, provider, credentialType, maskedKey, createdAt];
}
