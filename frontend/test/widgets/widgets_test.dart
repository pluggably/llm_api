// Widget tests for key UI components.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:pluggably_llm_client/models.dart';
import 'package:plugai/widgets/chat_bubble.dart';

void main() {
  group('ChatBubble', () {
    testWidgets('displays user message on the right', (tester) async {
      final message = Message(
        id: 'msg-1',
        role: 'user',
        content: 'Hello!',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ChatBubble(message: message),
        ),
      ));

      expect(find.text('Hello!'), findsOneWidget);

      // User messages should be aligned to the right
      final align = tester.widget<Align>(find.ancestor(
        of: find.byType(Container),
        matching: find.byType(Align),
      ).first);
      expect(align.alignment, Alignment.centerRight);
    });

    testWidgets('displays assistant message on the left', (tester) async {
      final message = Message(
        id: 'msg-2',
        role: 'assistant',
        content: 'Hi there!',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ChatBubble(message: message),
        ),
      ));

      expect(find.text('Hi there!'), findsOneWidget);

      // Assistant messages should be aligned to the left
      final align = tester.widget<Align>(find.ancestor(
        of: find.byType(Container),
        matching: find.byType(Align),
      ).first);
      expect(align.alignment, Alignment.centerLeft);
    });

    testWidgets('renders markdown content', (tester) async {
      final message = Message(
        id: 'msg-3',
        role: 'assistant',
        content: '**Bold text** and `code`',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ChatBubble(message: message),
          ),
        ),
      ));

      // The content should be present (markdown widget renders it)
      expect(find.textContaining('Bold text'), findsOneWidget);
    });

    testWidgets('displays role labels', (tester) async {
      final message = Message(
        id: 'msg-5',
        role: 'user',
        content: 'Test message',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ChatBubble(message: message),
        ),
      ));

      expect(find.text('You'), findsOneWidget);
    });

    testWidgets('assistant message shows Assistant label', (tester) async {
      final message = Message(
        id: 'msg-6',
        role: 'assistant',
        content: 'Response',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ChatBubble(message: message),
        ),
      ));

      expect(find.text('Assistant'), findsOneWidget);
    });

    testWidgets('shows loading indicator for empty assistant message', (tester) async {
      final message = Message(
        id: 'msg-7',
        role: 'assistant',
        content: '',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: ChatBubble(message: message),
        ),
      ));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}
