import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/dashboard_screen.dart';
import '../screens/camera_screen.dart';
import '../screens/analysis_screen.dart';
import '../screens/reports_screen.dart';
import '../screens/recommendations_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/login_screen.dart';
import '../utils/constants.dart';

class AppShell extends StatelessWidget {
  final Widget body;
  final String currentRoute;

  const AppShell({
    Key? key,
    required this.body,
    required this.currentRoute,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(currentRoute),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('No new notifications')),
              );
            },
            tooltip: 'Notifications',
          ),
        ],
      ),
      drawer: _buildDrawer(context),
      body: body,
    );
  }

  Widget _buildDrawer(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          UserAccountsDrawerHeader(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [AppConstants.primaryTeal, Color(0xFF3D9B93)],
              ),
            ),
            accountName: Text(authProvider.user?.name ?? 'User'),
            accountEmail: Text(authProvider.user?.email ?? ''),
            currentAccountPicture: CircleAvatar(
              backgroundColor: Colors.white,
              child: Text(
                authProvider.user?.name.substring(0, 1).toUpperCase() ?? 'U',
                style: const TextStyle(
                  fontSize: 24,
                  color: AppConstants.primaryTeal,
                ),
              ),
            ),
          ),
          _buildDrawerItem(
            context,
            'Dashboard',
            Icons.dashboard,
                () => _navigateToScreen(context, const DashboardScreen()),
          ),
          _buildDrawerItem(
            context,
            'Camera',
            Icons.videocam,
                () => _navigateToScreen(context, const CameraScreen()),
          ),
          _buildDrawerItem(
            context,
            'Analysis',
            Icons.analytics,
                () => _navigateToScreen(context, const AnalysisScreen()),
          ),
          _buildDrawerItem(
            context,
            'Reports',
            Icons.assessment,
                () => _navigateToScreen(context, const ReportsScreen()),
          ),
          _buildDrawerItem(
            context,
            'Recommendations',
            Icons.lightbulb_outline,
                () => _navigateToScreen(context, const RecommendationsScreen()),
          ),
          const Divider(),
          _buildDrawerItem(
            context,
            'Profile',
            Icons.person,
                () => _navigateToScreen(context, const ProfileScreen()),
          ),
          _buildDrawerItem(
            context,
            'Settings',
            Icons.settings,
                () => _navigateToScreen(context, const SettingsScreen()),
          ),
          const Divider(),
          _buildDrawerItem(
            context,
            'Logout',
            Icons.logout,
                () async {
              // Close drawer first
              Navigator.pop(context);

              // Show confirmation dialog
              final confirmed = await showDialog<bool>(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('Logout'),
                  content: const Text('Are you sure you want to logout?'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Cancel'),
                    ),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(context, true),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppConstants.errorRed,
                      ),
                      child: const Text('Logout'),
                    ),
                  ],
                ),
              );

              if (confirmed == true && context.mounted) {
                final authProvider = Provider.of<AuthProvider>(context, listen: false);
                await authProvider.logout();

                if (context.mounted) {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                        (route) => false,
                  );
                }
              }
            },
            color: AppConstants.errorRed,
          ),
        ],
      ),
    );
  }

  Widget _buildDrawerItem(
      BuildContext context,
      String title,
      IconData icon,
      VoidCallback onTap, {
        Color? color,
      }) {
    final isSelected = currentRoute == title;
    return ListTile(
      leading: Icon(icon, color: color ?? (isSelected ? AppConstants.primaryTeal : null)),
      title: Text(
        title,
        style: TextStyle(
          color: color,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      selected: isSelected,
      selectedTileColor: AppConstants.primaryTeal.withOpacity(0.1),
      onTap: onTap,
    );
  }

  void _navigateToScreen(BuildContext context, Widget screen) {
    // Close drawer
    Navigator.pop(context);

    // Don't navigate if already on the same screen
    if (screen.runtimeType.toString().contains(currentRoute)) {
      return;
    }

    // Use pushReplacement to avoid stacking screens
    Navigator.pushReplacement(
      context,
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => screen,
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(
            opacity: animation,
            child: child,
          );
        },
        transitionDuration: const Duration(milliseconds: 200),
      ),
    );
  }
}