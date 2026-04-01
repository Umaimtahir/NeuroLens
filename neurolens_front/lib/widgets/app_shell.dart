import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/analysis_provider.dart';
import '../screens/dashboard_screen.dart';
import '../screens/camera_screen.dart';
import '../screens/analysis_screen.dart';
import '../screens/reports_screen.dart';
import '../screens/recommendations_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/login_screen.dart';
import '../widgets/notification_widgets.dart';
import '../utils/constants.dart';

class AppShell extends StatefulWidget {
  final Widget body;
  final String currentRoute;

  const AppShell({
    Key? key,
    required this.body,
    required this.currentRoute,
  }) : super(key: key);

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  AnalysisProvider? _analysisProvider;
  bool _isRecommendationDialogVisible = false;
  String? _lastShownRecommendationSignature;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final provider = Provider.of<AnalysisProvider>(context, listen: false);

    if (_analysisProvider != provider) {
      _analysisProvider = provider;
      _analysisProvider?.onRecommendationReceived = _showGlobalRecommendationDialog;
    }
  }

  @override
  void dispose() {
    if (_analysisProvider != null) {
      _analysisProvider!.onRecommendationReceived = null;
    }
    super.dispose();
  }

  void _showGlobalRecommendationDialog(Map<String, dynamic> payload) {
    if (!mounted || _isRecommendationDialogVisible) return;

    final recommendations = List<Map<String, dynamic>>.from(
      payload['recommendations'] ?? [],
    );

    if (recommendations.isEmpty) return;

    final triggerEmotion = (payload['trigger_emotion'] ?? 'neutral').toString();
    final triggerReason = (payload['trigger_reason'] ?? '').toString();
    final firstTitle = (recommendations.first['title'] ?? '').toString();
    final signature = '$triggerEmotion|$triggerReason|$firstTitle';

    if (_lastShownRecommendationSignature == signature) return;

    _lastShownRecommendationSignature = signature;
    _isRecommendationDialogVisible = true;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        _isRecommendationDialogVisible = false;
        return;
      }

      showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Wellness Recommendation'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Detected state: ${triggerEmotion.toUpperCase()}',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              if (triggerReason.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(triggerReason),
              ],
              const SizedBox(height: 12),
              ...recommendations.take(2).map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('• ${item['title'] ?? 'Recommendation available'}'),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      ).whenComplete(() {
        _isRecommendationDialogVisible = false;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AnalysisProvider>(
      builder: (context, analysisProvider, _) {
        return Scaffold(
          appBar: AppBar(
            title: Text(widget.currentRoute),
            actions: [
              NotificationBell(
                unreadCount: analysisProvider.unreadNotificationCount,
                onTap: () => _showNotificationPanel(context, analysisProvider),
              ),
            ],
          ),
          drawer: _buildDrawer(context),
          body: widget.body,
        );
      },
    );
  }
  
  void _showNotificationPanel(BuildContext context, AnalysisProvider analysisProvider) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Theme.of(context).cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          child: NotificationPanel(
            notifications: analysisProvider.notifications,
            onClearAll: () {
              analysisProvider.clearAllNotifications();
              Navigator.pop(context);
            },
            onMarkAsRead: (id) {
              analysisProvider.markNotificationAsRead(id);
            },
          ),
        ),
      ),
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
    final isSelected = widget.currentRoute == title;
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
    if (screen.runtimeType.toString().contains(widget.currentRoute)) {
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