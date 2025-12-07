import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';  // ✅ ADD THIS IMPORT
import '../widgets/app_shell.dart';
import 'dart:async';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _apiService = ApiService();  // ✅ ADD THIS
  Timer? _refreshTimer;

  // Dashboard data
  String? _currentEmotion;
  double? _emotionIntensity;
  String? _currentContent;
  String _status = 'Idle';
  DateTime? _lastSession;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();

    // Refresh every 5 seconds while on dashboard
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _loadDashboardData();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadDashboardData() async {
    try {
      final response = await _apiService.get('/api/dashboard/status');

      if (mounted) {
        setState(() {
          _currentEmotion = response['current_emotion'];
          _emotionIntensity = response['current_emotion_intensity']?.toDouble();
          _currentContent = response['current_content'];
          _status = response['status'] ?? 'Idle';

          if (response['last_session'] != null) {
            _lastSession = DateTime.parse(response['last_session']);
          }

          _isLoading = false;
        });
      }
    } catch (e) {
      print('❌ Failed to load dashboard data: $e');
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return AppShell(
      currentRoute: 'Dashboard',
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome back, ${authProvider.user?.name ?? 'User'}!',
              style: Theme.of(context).textTheme.displayLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Monitor your mental well-being in real-time',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 32),

            // Current State Cards
            Row(
              children: [
                Expanded(
                  child: _buildInfoCard(
                    context,
                    'Current Emotion',
                    _currentEmotion?.toUpperCase() ?? 'N/A',
                    Icons.emoji_emotions,
                    _getEmotionColor(_currentEmotion),
                    subtitle: _emotionIntensity != null
                        ? '${(_emotionIntensity! * 100).toStringAsFixed(0)}% intensity'
                        : null,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildInfoCard(
                    context,
                    'Current Content',
                    _currentContent ?? 'N/A',
                    Icons.school,
                    Colors.amber,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildInfoCard(
                    context,
                    'Last Session',
                    _lastSession != null
                        ? _formatTimeSince(_lastSession!)
                        : 'N/A',
                    Icons.access_time,
                    Colors.blue,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildInfoCard(
                    context,
                    'Status',
                    _status,
                    _status == 'Recording' ? Icons.fiber_manual_record : Icons.circle_outlined,
                    _status == 'Recording' ? Colors.red : Colors.grey,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 32),

            // Quick Actions
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.displayMedium,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                _buildActionButton(
                  context,
                  'Start Recording',
                  Icons.videocam,
                  Colors.teal,
                      () => Navigator.pushNamed(context, '/camera'),
                ),
                _buildActionButton(
                  context,
                  'View Reports',
                  Icons.bar_chart,
                  Colors.blue,
                      () => Navigator.pushNamed(context, '/reports'),
                ),
                _buildActionButton(
                  context,
                  'Recommendations',
                  Icons.lightbulb,
                  Colors.amber,
                      () => Navigator.pushNamed(context, '/recommendations'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard(
      BuildContext context,
      String title,
      String value,
      IconData icon,
      Color color, {
        String? subtitle,
      }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                Icon(icon, color: color, size: 24),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              value,
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(
      BuildContext context,
      String label,
      IconData icon,
      Color color,
      VoidCallback onPressed,
      ) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      ),
    );
  }

  Color _getEmotionColor(String? emotion) {
    if (emotion == null) return Colors.grey;

    switch (emotion.toLowerCase()) {
      case 'happy':
      case 'excited':
        return Colors.green;
      case 'stressed':
      case 'angry':
        return Colors.red;
      case 'focused':
        return Colors.blue;
      case 'tired':
        return Colors.orange;
      case 'sad':
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }

  String _formatTimeSince(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes} min ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours} hr ago';
    } else {
      return '${difference.inDays} days ago';
    }
  }
}