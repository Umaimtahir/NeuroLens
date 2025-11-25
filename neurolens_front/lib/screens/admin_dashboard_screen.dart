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

      if (statsResponse.statusCode == 200 && auditResponse.statusCode == 200) {
        setState(() {
          _stats = jsonDecode(statsResponse.body);
          _audit = jsonDecode(auditResponse.body);
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

  Future<void> _exportDataset() async {
    // Implementation for dataset export
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Dataset export feature coming soon!')),
    );
  }

  Future<void> _viewUsers() async {
    // Implementation for viewing users
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('User management feature coming soon!')),
    );
  }
}