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
  String? _currentActivity;
  String? _activityEmoji;
  String? _currentProductivity;
  String? _productivityEmoji;
  String? _currentAppName;
  String _status = 'Idle';
  DateTime? _lastSession;
  Map<String, dynamic>? _sessionSummary;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();

    // Refresh every 3 seconds - balanced between responsiveness and server load
    _refreshTimer = Timer.periodic(const Duration(seconds: 3), (_) {
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
      // Ensure we have the token from AuthProvider
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final token = authProvider.user?.token;
      if (token != null) {
        _apiService.setToken(token);
      } else {
        print('⚠️ Dashboard: No token available!');
      }
      
      print('📡 Dashboard: Fetching status...');
      final response = await _apiService.get('/api/dashboard/status');
      
      // Debug: print received data
      print('📊 Dashboard received: emotion=${response['current_emotion']}, content=${response['current_content']}, status=${response['status']}');

      if (mounted) {
        setState(() {
          _currentEmotion = response['current_emotion'];
          _emotionIntensity = response['current_emotion_intensity']?.toDouble();
          _currentContent = response['current_content'];
          _status = response['status'] ?? 'Idle';
          _sessionSummary = response['session_summary'];

          // Parse content details (activity, productivity, app info)
          final details = response['content_details'];
          if (details != null && details is Map) {
            _currentActivity = details['activity'];
            _activityEmoji = details['activity_emoji'];
            _currentProductivity = details['productivity'];
            _productivityEmoji = details['productivity_emoji'];
            _currentAppName = details['app_name'];
          } else {
            _currentActivity = null;
            _activityEmoji = null;
            _currentProductivity = null;
            _productivityEmoji = null;
            _currentAppName = null;
          }

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
                    _status == 'Recording' ? 'Current Emotion' : 'Last Emotion',
                    _currentEmotion?.toUpperCase() ?? 'No data yet',
                    Icons.emoji_emotions,
                    _getEmotionColor(_currentEmotion),
                    subtitle: _emotionIntensity != null
                        ? '${(_emotionIntensity! * 100).toStringAsFixed(0)}% intensity'
                        : _currentEmotion == null ? 'Start recording to track' : null,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildInfoCard(
                    context,
                    _status == 'Recording' ? 'Current Activity' : 'Last Activity',
                    _currentActivity != null
                        ? '${_activityEmoji ?? ''} ${_currentActivity}'
                        : (_currentContent ?? 'No data yet'),
                    Icons.school,
                    _getProductivityColor(_currentProductivity),
                    subtitle: _currentContent != null && _currentActivity != null
                        ? '${_currentContent}${_currentAppName != null && _currentAppName!.isNotEmpty ? ' • $_currentAppName' : ''}'
                        : (_currentContent == null ? 'Start recording to track' : null),
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
                        : 'No sessions yet',
                    Icons.access_time,
                    Colors.blue,
                    subtitle: _lastSession == null ? 'Start your first session' : null,
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
                    subtitle: _status == 'Recording' ? 'Live monitoring active' : 'Ready to start',
                  ),
                ),
              ],
            ),
            
            // Session Summary Card (if available)
            if (_sessionSummary != null) ...[
              const SizedBox(height: 24),
              _buildSessionSummaryCard(),
            ],

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
                  _status == 'Recording' ? 'Stop Recording' : 'Start Recording',
                  _status == 'Recording' ? Icons.stop : Icons.videocam,
                  _status == 'Recording' ? Colors.red : Colors.teal,
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

  Color _getProductivityColor(String? productivity) {
    if (productivity == null) return Colors.amber;
    switch (productivity.toUpperCase()) {
      case 'PRODUCTIVE':
        return Colors.green;
      case 'UNPRODUCTIVE':
        return Colors.red;
      case 'NEUTRAL':
      default:
        return Colors.amber;
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
  
  Widget _buildSessionSummaryCard() {
    final totalReadings = _sessionSummary!['total_readings'] ?? 0;
    final dominantEmotion = _sessionSummary!['dominant_emotion'];
    final avgIntensity = _sessionSummary!['average_intensity'] ?? 0;
    final emotionBreakdown = _sessionSummary!['emotion_breakdown'] as Map<String, dynamic>?;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.insights, color: Colors.teal, size: 24),
                const SizedBox(width: 8),
                Text(
                  "Today's Summary",
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildSummaryItem(
                  Icons.analytics,
                  '$totalReadings',
                  'Readings',
                  Colors.blue,
                ),
                _buildSummaryItem(
                  Icons.emoji_emotions,
                  dominantEmotion?.toString().toUpperCase() ?? 'N/A',
                  'Dominant',
                  _getEmotionColor(dominantEmotion),
                ),
                _buildSummaryItem(
                  Icons.speed,
                  '$avgIntensity%',
                  'Avg Intensity',
                  Colors.orange,
                ),
              ],
            ),
            if (emotionBreakdown != null && emotionBreakdown.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 12),
              Text(
                'Emotion Breakdown',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: emotionBreakdown.entries.map((entry) {
                  return Chip(
                    avatar: CircleAvatar(
                      backgroundColor: _getEmotionColor(entry.key),
                      child: Text(
                        '${entry.value}',
                        style: const TextStyle(color: Colors.white, fontSize: 10),
                      ),
                    ),
                    label: Text(entry.key),
                    backgroundColor: _getEmotionColor(entry.key).withOpacity(0.1),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildSummaryItem(IconData icon, String value, String label, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}