// Unit tests for the API client.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:pluggably_llm_client/api_client.dart';

void main() {
  group('LlmApiClient', () {
    late LlmApiClient client;

    group('listModels', () {
      test('returns list of models on success', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/models');
          return http.Response(
            jsonEncode({
              'data': [
                {
                  'id': 'gpt-4',
                  'name': 'GPT-4',
                  'provider': 'openai',
                  'modality': 'text',
                },
                {
                  'id': 'llama-3',
                  'name': 'Llama 3',
                  'provider': 'meta',
                  'modality': 'text',
                },
              ],
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final models = await client.listModels();

        expect(models.length, 2);
        expect(models[0].id, 'gpt-4');
        expect(models[1].id, 'llama-3');
      });

      test('throws ApiException on error', () async {
        final mockClient = MockClient((request) async {
          return http.Response(jsonEncode({'detail': 'Unauthorized'}), 401);
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );

        expect(
          () => client.listModels(),
          throwsA(
            isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401),
          ),
        );
      });
    });

    group('getModel', () {
      test('returns single model on success', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/models/gpt-4');
          return http.Response(
            jsonEncode({
              'id': 'gpt-4',
              'name': 'GPT-4',
              'provider': 'openai',
              'modality': 'text',
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final model = await client.getModel('gpt-4');

        expect(model.id, 'gpt-4');
        expect(model.name, 'GPT-4');
      });
    });

    group('getSchema', () {
      test('returns schema for model', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.queryParameters['model'], 'gpt-4');
          return http.Response(
            jsonEncode({
              'model_id': 'gpt-4',
              'properties': {
                'temperature': {'type': 'number', 'default': 0.7},
              },
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final schema = await client.getSchema('gpt-4');

        expect(schema.modelId, 'gpt-4');
        expect(schema.parameters.containsKey('temperature'), true);
      });
    });

    group('loadModel', () {
      test('sends load request correctly', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/models/llama-3/load');
          // model_id is now in path, not body
          return http.Response(
            jsonEncode({'model_id': 'llama-3', 'status': 'loading'}),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final response = await client.loadModel('llama-3');

        expect(response.modelId, 'llama-3');
        expect(response.status, 'loading');
      });
    });

    group('unloadModel', () {
      test('sends unload request correctly', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/models/llama-3/unload');
          // model_id is now in path, not body
          // Body contains only force flag
          return http.Response('{}', 200);
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        await client.unloadModel('llama-3');
        // No exception means success
      });
    });

    group('downloadModel', () {
      test('sends install_local and provider in payload', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/models/download');
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          expect(body['model']['id'], 'meta-llama/Llama-3.2-1B-Instruct');
          expect(body['model']['provider'], 'huggingface');
          expect(body['source']['type'], 'huggingface');
          expect(body['source']['id'], 'meta-llama/Llama-3.2-1B-Instruct');
          expect(body['options']['install_local'], false);
          return http.Response(
            jsonEncode({'job_id': 'job-1', 'status': 'completed'}),
            202,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );

        await client.downloadModel(
          modelId: 'meta-llama/Llama-3.2-1B-Instruct',
          name: 'meta-llama/Llama-3.2-1B-Instruct',
          modality: 'text',
          sourceType: 'huggingface',
          sourceId: 'meta-llama/Llama-3.2-1B-Instruct',
          installLocal: false,
          provider: 'huggingface',
        );
      });
    });

    group('sessions', () {
      test('listSessions returns sessions', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/sessions');
          return http.Response(
            jsonEncode({
              'sessions': [
                {
                  'id': 'session-1',
                  'title': 'Chat 1',
                  'created_at': '2026-01-26T10:00:00Z',
                },
                {
                  'id': 'session-2',
                  'title': 'Chat 2',
                  'created_at': '2026-01-26T10:05:00Z',
                },
              ],
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final sessions = await client.listSessions();

        expect(sessions.length, 2);
        expect(sessions[0].id, 'session-1');
      });

      test('createSession creates new session', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/sessions');
          return http.Response(
            jsonEncode({
              'id': 'new-session',
              'title': 'New Chat',
              'created_at': '2026-01-26T10:00:00Z',
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final session = await client.createSession();

        expect(session.id, 'new-session');
      });

      test('deleteSession calls correct endpoint', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'DELETE');
          expect(request.url.path, '/v1/sessions/session-1');
          return http.Response('', 204);
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        await client.deleteSession('session-1');
        // No exception means success
      });
    });

    group('generate', () {
      test('sends generation request correctly', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/generate');
          final body = jsonDecode(request.body);
          expect(body['model'], 'gpt-4');
          expect(body['modality'], 'text');
          expect(body['input']['prompt'], 'Hello');
          return http.Response(
            jsonEncode({
              'id': 'gen-1',
              'choices': [
                {
                  'message': {'content': 'Hi there!'},
                  'finish_reason': 'stop',
                },
              ],
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final response = await client.generate(
          modelId: 'gpt-4',
          prompt: 'Hello',
        );

        expect(response.content, 'Hi there!');
      });
    });

    group('auth', () {
      test('login returns auth response', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/users/login');
          return http.Response(
            jsonEncode({'access_token': 'jwt-token', 'token_type': 'bearer'}),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final auth = await client.login(
          username: 'testuser',
          password: 'password',
        );

        expect(auth.accessToken, 'jwt-token');
      });

      test('register with invite token', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/users/register');
          final body = jsonDecode(request.body);
          expect(body['invite_token'], 'invite-123');
          return http.Response(
            jsonEncode({'access_token': 'new-token', 'token_type': 'bearer'}),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final auth = await client.register(
          username: 'newuser',
          password: 'password',
          inviteToken: 'invite-123',
        );

        expect(auth.accessToken, 'new-token');
      });
    });

    group('auth token', () {
      test('setAuthToken adds Authorization header', () async {
        String? capturedAuthHeader;
        final mockClient = MockClient((request) async {
          capturedAuthHeader = request.headers['Authorization'];
          return http.Response(jsonEncode({'data': []}), 200);
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        client.setAuthToken('my-token');
        await client.listModels();

        expect(capturedAuthHeader, 'Bearer my-token');
      });
    });

    group('user tokens', () {
      test('listUserTokens returns tokens', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/users/tokens');
          return http.Response(
            jsonEncode([
              {
                'id': 'token-1',
                'name': 'Token 1',
                'created_at': '2026-01-26T10:00:00Z',
              },
            ]),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final tokens = await client.listUserTokens();

        expect(tokens.length, 1);
        expect(tokens[0].id, 'token-1');
      });

      test('createUserToken returns token with secret', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          return http.Response(
            jsonEncode({
              'id': 'new-token',
              'name': 'API Token',
              'token': 'secret-value',
              'created_at': '2026-01-26T10:00:00Z',
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final token = await client.createUserToken(name: 'API Token');

        expect(token.token, 'secret-value');
      });
    });

    group('provider keys', () {
      test('listProviderKeys returns keys', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/users/provider-keys');
          return http.Response(
            jsonEncode([
              {
                'id': 'key-1',
                'provider': 'openai',
                'credential_type': 'api_key',
                'masked_key': 'sk-****',
                'created_at': '2026-01-26T10:00:00Z',
              },
            ]),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final keys = await client.listProviderKeys();

        expect(keys.length, 1);
        expect(keys[0].provider, 'openai');
      });

      test('addProviderKey sends correct data', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          final body = jsonDecode(request.body);
          expect(body['provider'], 'anthropic');
          expect(body['credential_type'], 'api_key');
          expect(body['api_key'], 'sk-ant-123');
          return http.Response(
            jsonEncode({
              'id': 'key-2',
              'provider': 'anthropic',
              'credential_type': 'api_key',
              'masked_key': 'sk-****',
              'created_at': '2026-01-26T10:00:00Z',
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final key = await client.addProviderKey(
          provider: 'anthropic',
          apiKey: 'sk-ant-123',
        );

        expect(key.provider, 'anthropic');
      });
    });

    group('lifecycle', () {
      test('getModelStatus returns status', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/models/gpt-4/status');
          return http.Response(
            jsonEncode({
              'model_id': 'gpt-4',
              'runtime_status': 'loaded',
              'queue_depth': 0,
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final status = await client.getModelStatus('gpt-4');

        expect(status.modelId, 'gpt-4');
        expect(status.runtimeStatus, 'loaded');
      });

      test('getLoadedModels returns list', () async {
        final mockClient = MockClient((request) async {
          expect(request.url.path, '/v1/models/loaded');
          return http.Response(
            jsonEncode({
              'models': [
                {'model_id': 'gpt-4', 'status': 'loaded'},
              ],
            }),
            200,
          );
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        final models = await client.getLoadedModels();

        expect(models.length, 1);
        expect(models[0].modelId, 'gpt-4');
      });

      test('cancelRequest calls correct endpoint', () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/v1/requests/req-123/cancel');
          return http.Response('{}', 200);
        });

        client = LlmApiClient(
          baseUrl: 'http://localhost:8000',
          httpClient: mockClient,
        );
        await client.cancelRequest('req-123');
        // No exception means success
      });
    });
  });

  group('generate with images', () {
    test('includes images in input payload', () async {
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final input = body['input'] as Map<String, dynamic>;
        expect(input['images'], isNotNull);
        expect((input['images'] as List).length, 1);
        return http.Response(
          jsonEncode({
            'id': 'gen-1',
            'modality': 'text',
            'output': {'text': 'ok'},
          }),
          200,
        );
      });

      final client = LlmApiClient(
        baseUrl: 'http://localhost:8000',
        httpClient: mockClient,
      );

      await client.generate(
        modelId: 'gpt-4',
        prompt: 'hello',
        images: ['data:image/png;base64,AAA'],
      );
    });
  });

  group('ApiException', () {
    test('toString includes status code and message', () {
      final exception = ApiException(
        404,
        'Not found',
        detail: 'Model not found',
      );

      expect(exception.toString(), contains('404'));
      expect(exception.toString(), contains('Model not found'));
    });

    test('toString works without detail', () {
      final exception = ApiException(500, 'Server error');

      expect(exception.toString(), contains('500'));
      expect(exception.toString(), contains('Server error'));
    });
  });
}
