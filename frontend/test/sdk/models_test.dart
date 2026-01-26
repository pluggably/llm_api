// Unit tests for the SDK models.

import 'package:flutter_test/flutter_test.dart';
import 'package:pluggably_llm_client/models.dart';

void main() {
  group('Model', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'gpt-4',
        'name': 'GPT-4',
        'provider': 'openai',
        'modality': 'text',
        'version': '1.0',
        'description': 'A large language model',
      };

      final model = Model.fromJson(json);

      expect(model.id, 'gpt-4');
      expect(model.name, 'GPT-4');
      expect(model.provider, 'openai');
      expect(model.modality, 'text');
      expect(model.version, '1.0');
      expect(model.description, 'A large language model');
      expect(model.status, ModelStatus.ready);
    });

    test('fromJson handles missing optional fields', () {
      final json = {
        'id': 'llama-3',
      };

      final model = Model.fromJson(json);

      expect(model.id, 'llama-3');
      expect(model.name, 'llama-3'); // Falls back to id
      expect(model.provider, 'unknown');
      expect(model.modality, 'text');
      expect(model.version, isNull);
    });

    test('fromJson parses status correctly', () {
      final json = {
        'id': 'model-1',
        'status': 'loading',
      };

      final model = Model.fromJson(json);
      expect(model.status, ModelStatus.loading);
    });

    test('equality works correctly', () {
      final model1 = Model(
        id: 'gpt-4',
        name: 'GPT-4',
        provider: 'openai',
        modality: 'text',
      );
      final model2 = Model(
        id: 'gpt-4',
        name: 'GPT-4',
        provider: 'openai',
        modality: 'text',
      );

      expect(model1, equals(model2));
    });
  });

  group('ModelSchema', () {
    test('fromJson parses parameters correctly', () {
      final json = {
        'model_id': 'gpt-4',
        'version': '1.0',
        'properties': {
          'temperature': {
            'type': 'number',
            'title': 'Temperature',
            'description': 'Sampling temperature',
            'default': 0.7,
            'minimum': 0.0,
            'maximum': 2.0,
          },
          'max_tokens': {
            'type': 'integer',
            'title': 'Max Tokens',
            'default': 1024,
          },
        },
      };

      final schema = ModelSchema.fromJson(json);

      expect(schema.modelId, 'gpt-4');
      expect(schema.version, '1.0');
      expect(schema.parameters.length, 2);
      expect(schema.parameters['temperature']?.type, 'number');
      expect(schema.parameters['temperature']?.minimum, 0.0);
      expect(schema.parameters['temperature']?.maximum, 2.0);
      expect(schema.parameters['max_tokens']?.type, 'integer');
    });

    test('fromJson handles empty properties', () {
      final json = {
        'model_id': 'simple-model',
      };

      final schema = ModelSchema.fromJson(json);

      expect(schema.parameters, isEmpty);
    });
  });

  group('SchemaParameter', () {
    test('fromJson parses all fields', () {
      final json = {
        'type': 'string',
        'title': 'System Prompt',
        'description': 'The system prompt to use',
        'default': 'You are a helpful assistant',
        'enum': ['option1', 'option2'],
        'required': true,
      };

      final param = SchemaParameter.fromJson('system_prompt', json);

      expect(param.name, 'system_prompt');
      expect(param.type, 'string');
      expect(param.title, 'System Prompt');
      expect(param.description, 'The system prompt to use');
      expect(param.defaultValue, 'You are a helpful assistant');
      expect(param.enumValues, ['option1', 'option2']);
      expect(param.required, true);
    });
  });

  group('Message', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'msg-123',
        'role': 'user',
        'content': 'Hello, world!',
        'created_at': '2026-01-26T10:00:00Z',
      };

      final message = Message.fromJson(json);

      expect(message.id, 'msg-123');
      expect(message.role, 'user');
      expect(message.content, 'Hello, world!');
      expect(message.createdAt.year, 2026);
    });

    test('toJson serializes correctly', () {
      final message = Message(
        id: 'msg-456',
        role: 'assistant',
        content: 'Hi there!',
        createdAt: DateTime(2026, 1, 26, 12, 0, 0),
      );

      final json = message.toJson();

      expect(json['id'], 'msg-456');
      expect(json['role'], 'assistant');
      expect(json['content'], 'Hi there!');
      expect(json['created_at'], contains('2026'));
    });
  });

  group('Session', () {
    test('fromJson parses with messages', () {
      final json = {
        'id': 'session-1',
        'title': 'Test Session',
        'model_id': 'gpt-4',
        'created_at': '2026-01-26T10:00:00Z',
        'last_used_at': '2026-01-26T11:00:00Z',
        'messages': [
          {
            'id': 'msg-1',
            'role': 'user',
            'content': 'Hello',
            'created_at': '2026-01-26T10:00:00Z',
          },
          {
            'id': 'msg-2',
            'role': 'assistant',
            'content': 'Hi!',
            'created_at': '2026-01-26T10:00:01Z',
          },
        ],
      };

      final session = Session.fromJson(json);

      expect(session.id, 'session-1');
      expect(session.title, 'Test Session');
      expect(session.modelId, 'gpt-4');
      expect(session.messages.length, 2);
      expect(session.messages[0].role, 'user');
      expect(session.messages[1].role, 'assistant');
    });

    test('fromJson handles empty messages', () {
      final json = {
        'id': 'session-2',
        'created_at': '2026-01-26T10:00:00Z',
      };

      final session = Session.fromJson(json);

      expect(session.messages, isEmpty);
    });
  });

  group('SessionSummary', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'session-1',
        'title': 'My Chat',
        'last_used_at': '2026-01-26T10:00:00Z',
      };

      final summary = SessionSummary.fromJson(json);

      expect(summary.id, 'session-1');
      expect(summary.title, 'My Chat');
      expect(summary.lastUsedAt, isNotNull);
    });
  });

  group('GenerationResponse', () {
    test('fromJson parses chat completion format', () {
      final json = {
        'id': 'gen-123',
        'choices': [
          {
            'message': {'content': 'Generated text'},
            'finish_reason': 'stop',
          },
        ],
        'usage': {
          'prompt_tokens': 10,
          'completion_tokens': 20,
        },
      };

      final response = GenerationResponse.fromJson(json);

      expect(response.id, 'gen-123');
      expect(response.content, 'Generated text');
      expect(response.finishReason, 'stop');
      expect(response.promptTokens, 10);
      expect(response.completionTokens, 20);
    });

    test('fromJson parses legacy text format', () {
      final json = {
        'id': 'gen-456',
        'choices': [
          {
            'text': 'Legacy text',
            'finish_reason': 'length',
          },
        ],
      };

      final response = GenerationResponse.fromJson(json);

      expect(response.content, 'Legacy text');
    });
  });

  group('LifecycleStatus', () {
    test('fromJson parses correctly', () {
      final json = {
        'model_id': 'gpt-4',
        'runtime_status': 'loaded',
        'queue_depth': 5,
      };

      final status = LifecycleStatus.fromJson(json);

      expect(status.modelId, 'gpt-4');
      expect(status.runtimeStatus, 'loaded');
      expect(status.queueDepth, 5);
    });
  });

  group('LoadedModel', () {
    test('fromJson parses correctly', () {
      final json = {
        'model_id': 'llama-3',
        'status': 'loaded',
        'loaded_at': '2026-01-26T10:00:00Z',
      };

      final loaded = LoadedModel.fromJson(json);

      expect(loaded.modelId, 'llama-3');
      expect(loaded.status, 'loaded');
      expect(loaded.loadedAt, isNotNull);
    });
  });

  group('RequestStatus', () {
    test('fromJson parses with queue info', () {
      final json = {
        'request_id': 'req-123',
        'status': 'queued',
        'queue_position': 3,
        'estimated_wait_seconds': 45,
      };

      final status = RequestStatus.fromJson(json);

      expect(status.requestId, 'req-123');
      expect(status.status, 'queued');
      expect(status.queuePosition, 3);
      expect(status.estimatedWaitSeconds, 45);
    });
  });

  group('AuthResponse', () {
    test('fromJson parses correctly', () {
      final json = {
        'access_token': 'token-abc',
        'token_type': 'bearer',
        'expires_in': 3600,
      };

      final auth = AuthResponse.fromJson(json);

      expect(auth.accessToken, 'token-abc');
      expect(auth.tokenType, 'bearer');
      expect(auth.expiresIn, 3600);
    });

    test('fromJson parses with user', () {
      final json = <String, dynamic>{
        'access_token': 'token-abc',
        'token_type': 'bearer',
        'user': <String, dynamic>{
          'id': 'user-1',
          'email': 'test@example.com',
          'preferences': <String, dynamic>{},
          'created_at': '2026-01-26T10:00:00Z',
        },
      };

      final auth = AuthResponse.fromJson(json);

      expect(auth.user?.email, 'test@example.com');
    });
  });

  group('UserProfile', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'user-1',
        'email': 'test@example.com',
        'preferences': {'theme': 'dark'},
        'created_at': '2026-01-26T10:00:00Z',
      };

      final profile = UserProfile.fromJson(json);

      expect(profile.id, 'user-1');
      expect(profile.email, 'test@example.com');
      expect(profile.preferences['theme'], 'dark');
    });
  });

  group('UserToken', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'token-1',
        'name': 'My Token',
        'created_at': '2026-01-26T10:00:00Z',
        'last_used_at': '2026-01-26T11:00:00Z',
      };

      final token = UserToken.fromJson(json);

      expect(token.id, 'token-1');
      expect(token.name, 'My Token');
      expect(token.lastUsedAt, isNotNull);
    });
  });

  group('UserTokenWithSecret', () {
    test('fromJson includes token secret', () {
      final json = {
        'id': 'token-2',
        'name': 'API Token',
        'token': 'secret-token-value',
        'created_at': '2026-01-26T10:00:00Z',
      };

      final token = UserTokenWithSecret.fromJson(json);

      expect(token.id, 'token-2');
      expect(token.token, 'secret-token-value');
    });
  });

  group('ProviderKey', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'key-1',
        'provider': 'openai',
        'masked_key': 'sk-****',
        'created_at': '2026-01-26T10:00:00Z',
      };

      final key = ProviderKey.fromJson(json);

      expect(key.id, 'key-1');
      expect(key.provider, 'openai');
      expect(key.maskedKey, 'sk-****');
    });
  });
}
