import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:pluggably_llm_client/pluggably_client.dart';
import 'package:test/test.dart';

Future<bool> serverAvailable(String baseUrl) async {
  try {
    final response = await http.get(Uri.parse('$baseUrl/health'));
    return response.statusCode == 200;
  } catch (_) {
    return false;
  }
}

void main() {
  test('Dart client end-to-end flow', () async {
    final baseUrl = Platform.environment['LLM_API_BASE_URL'] ?? 'http://127.0.0.1:8080';
    final apiKey = Platform.environment['LLM_API_API_KEY'] ?? 'test-local-key';

    if (!await serverAvailable(baseUrl)) {
      markTestSkipped('Local server not reachable for Dart client E2E tests');
    }

    final client = PluggablyClient(baseUrl: baseUrl, apiKey: apiKey);

    final session = await client.createSession();
    final response = await client.generateWithSession(
      session.id,
      GenerateRequest(modality: 'text', input: GenerateInput(prompt: 'Hello')),
    );

    expect(response.sessionId, session.id);

    final models = await client.listModels();
    expect(models.models.isNotEmpty, true);

    final providers = await client.listProviders();
    expect(providers.providers.isNotEmpty, true);

    final closed = await client.closeSession(session.id);
    expect(closed.status, 'closed');
  });
}
