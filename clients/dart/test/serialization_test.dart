import 'package:pluggably_llm_client/pluggably_client.dart';
import 'package:test/test.dart';

void main() {
  test('GenerateRequest serializes session fields', () {
    final request = GenerateRequest(
      modality: 'text',
      input: GenerateInput(prompt: 'hello'),
      sessionId: 'session-123',
      stateTokens: {'seed': '42'},
    );

    final json = request.toJson();

    expect(json['session_id'], 'session-123');
    expect(json['state_tokens'], {'seed': '42'});
    expect((json['input'] as Map<String, dynamic>)['prompt'], 'hello');
  });
}
