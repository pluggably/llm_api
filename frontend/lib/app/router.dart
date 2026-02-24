import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/models/models_page.dart';
import '../features/chat/chat_page.dart';
import '../features/auth/login_page.dart';
import '../features/auth/register_page.dart';
import '../features/profile/profile_page.dart';
import '../features/settings/settings_page.dart';
import '../features/tokens/tokens_page.dart';
import '../features/keys/keys_page.dart';
import '../state/state.dart';
import 'shell.dart';

/// App router configuration.
final routerProvider = Provider<GoRouter>((ref) {
  final isLoggedIn = ref.watch(isLoggedInProvider);

  return GoRouter(
    initialLocation: '/chat',
    redirect: (context, state) {
      final location = state.uri.path;
      final isAuthRoute = location == '/login' || location == '/register';

      if (!isLoggedIn && !isAuthRoute) {
        return '/login';
      }

      if (isLoggedIn && isAuthRoute) {
        return '/chat';
      }

      return null;
    },
    routes: [
      // Auth routes (no shell)
      GoRoute(path: '/login', builder: (context, state) => const LoginPage()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterPage(),
      ),

      // Main app routes (with shell)
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/models',
            builder: (context, state) => const ModelsPage(),
          ),
          GoRoute(path: '/chat', builder: (context, state) => const ChatPage()),
          GoRoute(
            path: '/settings',
            builder: (context, state) => const SettingsPage(),
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfilePage(),
          ),
          GoRoute(
            path: '/tokens',
            builder: (context, state) => const TokensPage(),
          ),
          GoRoute(path: '/keys', builder: (context, state) => const KeysPage()),
        ],
      ),
    ],
  );
});
