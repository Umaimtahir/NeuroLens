import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../utils/constants.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({Key? key}) : super(key: key);

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  Map<String, dynamic>? _stats;
  Map<String, dynamic>? _audit;
  Map<String, dynamic>? _activeUsers;
  bool _isLoading = true;
  final String _adminApiKey = "neurolens-admin-key-2025"; // Matches backend

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      final headers = {
        'X-API-Key': _adminApiKey,
        'Content-Type': 'application/json',
      };

      final statsResponse = await http.get(
        Uri.parse('${AppConstants.baseUrl}/api/admin/stats'),
        headers: headers,
      );

      final auditResponse = await http.get(
        Uri.parse('${AppConstants.baseUrl}/api/admin/audit'),
        headers: headers,
      );

      final activeUsersResponse = await http.get(
        Uri.parse('${AppConstants.baseUrl}/api/admin/active-users'),
        headers: headers,
      );

      if (statsResponse.statusCode == 200 && auditResponse.statusCode == 200) {
        setState(() {
          _stats = jsonDecode(statsResponse.body);
          _audit = jsonDecode(auditResponse.body);
          if (activeUsersResponse.statusCode == 200) {
            _activeUsers = jsonDecode(activeUsersResponse.body);
          }
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading admin data: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'System Statistics',
              style: Theme.of(context).textTheme.displayMedium,
            ),
            const SizedBox(height: 16),

            if (_audit != null && _audit!['statistics'] != null)
              GridView.count(
                crossAxisCount: 4,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                childAspectRatio: 1.5,
                children: [
                  _buildStatCard(
                    'Total Users',
                    _audit!['statistics']['total_users'].toString(),
                    Icons.people,
                    Colors.blue,
                  ),
                  _buildStatCard(
                    'Active Users',
                    _audit!['statistics']['active_users'].toString(),
                    Icons.check_circle,
                    Colors.green,
                  ),
                  _buildStatCard(
                    'Verified',
                    _audit!['statistics']['verified_users'].toString(),
                    Icons.verified_user,
                    AppConstants.primaryTeal,
                  ),
                  _buildStatCard(
                    'Emotion Logs',
                    _audit!['statistics']['total_emotion_logs'].toString(),
                    Icons.analytics,
                    Colors.orange,
                  ),
                ],
              ),

            const SizedBox(height: 32),

            Text(
              'Emotion Distribution',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 20,
              ),
            ),
            const SizedBox(height: 16),

            if (_stats != null && _stats!['emotion_distribution'] != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: (_stats!['emotion_distribution'] as Map<String, dynamic>)
                        .entries
                        .map((entry) => ListTile(
                      leading: _getEmotionIcon(entry.key),
                      title: Text(entry.key.toUpperCase()),
                      trailing: Text(
                        entry.value.toString(),
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ))
                        .toList(),
                  ),
                ),
              ),

            const SizedBox(height: 32),

            // Currently Active Users Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Currently Active Users',
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                    fontSize: 20,
                  ),
                ),
                if (_activeUsers != null)
                  Chip(
                    label: Text('${_activeUsers!['active_count']} online'),
                    backgroundColor: Colors.green.withOpacity(0.2),
                    avatar: const Icon(Icons.circle, color: Colors.green, size: 12),
                  ),
              ],
            ),
            const SizedBox(height: 16),

            if (_activeUsers != null && _activeUsers!['users'] != null)
              _activeUsers!['users'].isEmpty
                  ? Card(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Center(
                          child: Column(
                            children: [
                              Icon(Icons.person_off, size: 48, color: Colors.grey[400]),
                              const SizedBox(height: 8),
                              Text(
                                'No users currently active',
                                style: TextStyle(color: Colors.grey[600]),
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                  : Card(
                      child: ListView.separated(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: (_activeUsers!['users'] as List).length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final user = _activeUsers!['users'][index];
                          return ListTile(
                            leading: CircleAvatar(
                              backgroundColor: _getEmotionColor(user['current_emotion']),
                              child: Text(
                                user['name']?.substring(0, 1).toUpperCase() ?? '?',
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                              ),
                            ),
                            title: Text(user['name'] ?? 'Unknown'),
                            subtitle: Text('@${user['username'] ?? 'unknown'}'),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        _getEmotionIcon(user['current_emotion'] ?? 'neutral'),
                                        const SizedBox(width: 4),
                                        Text(
                                          (user['current_emotion'] ?? 'N/A').toUpperCase(),
                                          style: TextStyle(
                                            fontWeight: FontWeight.bold,
                                            color: _getEmotionColor(user['current_emotion']),
                                          ),
                                        ),
                                      ],
                                    ),
                                    Text(
                                      'Intensity: ${((user['current_emotion_intensity'] ?? 0) * 100).toInt()}%',
                                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                    ),
                                  ],
                                ),
                                const SizedBox(width: 12),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: user['status'] == 'Recording' 
                                        ? Colors.green.withOpacity(0.2)
                                        : Colors.grey.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        user['status'] == 'Recording' ? Icons.fiber_manual_record : Icons.pause,
                                        size: 12,
                                        color: user['status'] == 'Recording' ? Colors.green : Colors.grey,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        user['status'] ?? 'Idle',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: user['status'] == 'Recording' ? Colors.green : Colors.grey,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),

            const SizedBox(height: 32),

            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _exportDataset,
                    icon: const Icon(Icons.download),
                    label: const Text('Export Dataset'),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _viewUsers,
                    icon: const Icon(Icons.people),
                    label: const Text('View All Users'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              label,
              style: const TextStyle(fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Icon _getEmotionIcon(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy':
        return const Icon(Icons.sentiment_very_satisfied, color: Colors.green);
      case 'sad':
        return const Icon(Icons.sentiment_dissatisfied, color: Colors.blue);
      case 'angry':
        return const Icon(Icons.sentiment_very_dissatisfied, color: Colors.red);
      case 'stressed':
        return Icon(Icons.health_and_safety, color: Colors.orange);
      case 'focused':
        return const Icon(Icons.center_focus_strong, color: Colors.purple);
      default:
        return const Icon(Icons.sentiment_neutral, color: Colors.grey);
    }
  }

  Color _getEmotionColor(String? emotion) {
    if (emotion == null) return Colors.grey;
    switch (emotion.toLowerCase()) {
      case 'happy':
        return Colors.green;
      case 'sad':
        return Colors.blue;
      case 'angry':
        return Colors.red;
      case 'stressed':
        return Colors.orange;
      case 'focused':
        return Colors.purple;
      case 'fear':
      case 'fearful':
        return Colors.deepPurple;
      case 'surprise':
      case 'surprised':
        return Colors.amber;
      case 'disgust':
        return Colors.brown;
      default:
        return Colors.grey;
    }
  }

  Future<void> _exportDataset() async {
    // Implementation for dataset export
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Dataset export feature coming soon!')),
    );
  }

  Future<void> _viewUsers() async {
    // Show loading dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}/api/admin/users'),
        headers: {
          'X-API-Key': _adminApiKey,
          'Content-Type': 'application/json',
        },
      );

      Navigator.pop(context); // Close loading dialog

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final users = data['users'] as List;

        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('All Users'),
                Chip(
                  label: Text('${data['total']} total'),
                  backgroundColor: AppConstants.primaryTeal.withOpacity(0.2),
                ),
              ],
            ),
            content: SizedBox(
              width: double.maxFinite,
              height: 400,
              child: users.isEmpty
                  ? const Center(child: Text('No users found'))
                  : ListView.separated(
                      itemCount: users.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final user = users[index];
                        final isActive = user['is_active'] == true;
                        final isVerified = user['email_verified'] == true;
                        
                        return ListTile(
                          leading: CircleAvatar(
                            backgroundColor: isActive ? AppConstants.primaryTeal : Colors.grey,
                            child: Text(
                              (user['name'] ?? '?').substring(0, 1).toUpperCase(),
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                            ),
                          ),
                          title: Row(
                            children: [
                              Text(user['name'] ?? 'Unknown'),
                              const SizedBox(width: 8),
                              if (isVerified)
                                const Icon(Icons.verified, color: Colors.blue, size: 16),
                            ],
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('@${user['username'] ?? 'unknown'}'),
                              Text(
                                user['email'] ?? '',
                                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                              ),
                            ],
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isActive ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  isActive ? 'Active' : 'Inactive',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: isActive ? Colors.green : Colors.red,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'ID: ${user['id']}',
                                style: TextStyle(fontSize: 11, color: Colors.grey[500]),
                              ),
                            ],
                          ),
                          isThreeLine: true,
                        );
                      },
                    ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Close'),
              ),
            ],
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load users: ${response.statusCode}')),
        );
      }
    } catch (e) {
      Navigator.pop(context); // Close loading dialog
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading users: $e')),
      );
    }
  }
}