import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/state.dart';
import '../features/sessions/sessions_rail.dart';

/// Main app shell with navigation.
class AppShell extends ConsumerStatefulWidget {
  final Widget child;

  const AppShell({super.key, required this.child});

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  int _selectedIndex = 0;

  final List<_NavDestination> _destinations = const [
    _NavDestination(
      icon: Icons.auto_awesome_outlined,
      selectedIcon: Icons.auto_awesome,
      label: 'Models',
      path: '/models',
    ),
    _NavDestination(
      icon: Icons.chat_bubble_outline,
      selectedIcon: Icons.chat_bubble,
      label: 'Chat',
      path: '/chat',
    ),
    _NavDestination(
      icon: Icons.settings_outlined,
      selectedIcon: Icons.settings,
      label: 'Settings',
      path: '/settings',
    ),
  ];

  void _onDestinationSelected(int index) {
    setState(() => _selectedIndex = index);
    context.go(_destinations[index].path);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Update selected index based on current location
    final location = GoRouterState.of(context).matchedLocation;
    for (int i = 0; i < _destinations.length; i++) {
      if (location.startsWith(_destinations[i].path)) {
        if (_selectedIndex != i) {
          setState(() => _selectedIndex = i);
        }
        break;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth >= 1024;
    final isTablet = screenWidth >= 600 && screenWidth < 1024;

    return Scaffold(
      body: Row(
        children: [
          // Navigation rail for tablet/desktop
          if (isDesktop || isTablet)
            _SideNavigation(
              isExtended: isDesktop,
              destinations: _destinations,
              selectedIndex: _selectedIndex,
              onDestinationSelected: _onDestinationSelected,
            ),
          // Main content
          Expanded(child: widget.child),
        ],
      ),
      // Bottom navigation for mobile
      bottomNavigationBar: (!isDesktop && !isTablet)
          ? NavigationBar(
              selectedIndex: _selectedIndex,
              onDestinationSelected: _onDestinationSelected,
              destinations: [
                for (final dest in _destinations)
                  NavigationDestination(
                    icon: Icon(dest.icon),
                    selectedIcon: Icon(dest.selectedIcon),
                    label: dest.label,
                  ),
              ],
            )
          : null,
    );
  }
}

class _NavDestination {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final String path;

  const _NavDestination({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.path,
  });
}

class _SideNavigation extends ConsumerWidget {
  final bool isExtended;
  final List<_NavDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  const _SideNavigation({
    required this.isExtended,
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isLoggedIn = ref.watch(isLoggedInProvider);
    final theme = Theme.of(context);
    final width = isExtended ? 256.0 : 72.0;

    return Container(
      width: width,
      decoration: BoxDecoration(
        color: theme.navigationRailTheme.backgroundColor ??
            theme.colorScheme.surface,
        border: Border(
          right: BorderSide(
            color: theme.dividerColor.withValues(alpha: 0.1),
          ),
        ),
      ),
      child: Column(
        children: [
          const SizedBox(height: 16),
          // Destinations
          for (var i = 0; i < destinations.length; i++)
            _SideNavItem(
              destination: destinations[i],
              isSelected: i == selectedIndex,
              isExtended: isExtended,
              onTap: () => onDestinationSelected(i),
            ),
          const SizedBox(height: 16),
          // Sessions List (fills remaining space)
          const Expanded(child: SessionsRail()),
          // Bottom Actions
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (isLoggedIn)
                  IconButton(
                    icon: const Icon(Icons.person_outline),
                    tooltip: 'Profile',
                    onPressed: () => context.go('/profile'),
                  ),
                if (isLoggedIn) const SizedBox(height: 8),
                IconButton(
                  icon: Icon(isLoggedIn ? Icons.logout : Icons.login),
                  tooltip: isLoggedIn ? 'Logout' : 'Login',
                  onPressed: () {
                    if (isLoggedIn) {
                      ref.read(authTokenProvider.notifier).state = null;
                      final prefs = ref.read(sharedPreferencesProvider);
                      prefs.remove('auth_token');
                    } else {
                      context.go('/login');
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SideNavItem extends StatelessWidget {
  final _NavDestination destination;
  final bool isSelected;
  final bool isExtended;
  final VoidCallback onTap;

  const _SideNavItem({
    required this.destination,
    required this.isSelected,
    required this.isExtended,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final iconColor = isSelected
        ? theme.navigationRailTheme.selectedIconTheme?.color ??
            colorScheme.primary
        : theme.navigationRailTheme.unselectedIconTheme?.color ??
            colorScheme.onSurfaceVariant;

    if (!isExtended) {
      return SizedBox(
        height: 72,
        child: InkWell(
          onTap: onTap,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                isSelected ? destination.selectedIcon : destination.icon,
                color: iconColor,
              ),
              const SizedBox(height: 4),
              Text(
                destination.label,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: iconColor,
                  fontWeight: isSelected ? FontWeight.w600 : null,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      );
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Container(
          height: 56,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              Icon(
                isSelected ? destination.selectedIcon : destination.icon,
                color: iconColor,
                size: 24,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  destination.label,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color:
                        isSelected ? colorScheme.primary : colorScheme.onSurface,
                    fontWeight: isSelected ? FontWeight.w600 : null,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
