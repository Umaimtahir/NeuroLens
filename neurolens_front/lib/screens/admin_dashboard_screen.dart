import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../utils/constants.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({Key? key}) : super(key: key);

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> with SingleTickerProviderStateMixin {
  Map<String, dynamic>? _stats;
  Map<String, dynamic>? _audit;
  Map<String, dynamic>? _activeUsers;
  Map<String, dynamic>? _auditLogs;
  Map<String, dynamic>? _auditSummary;
  bool _isLoading = true;
  final String _adminApiKey = "neurolens-admin-key-2025"; // Matches backend
  late TabController _tabController;
  String? _selectedAction;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      final headers = {
        'X-API-Key': _adminApiKey,
        'Content-Type': 'application/json',
      };

      // Load all data in parallel
      final responses = await Future.wait([
        http.get(Uri.parse('${AppConstants.baseUrl}/api/admin/stats'), headers: headers),
        http.get(Uri.parse('${AppConstants.baseUrl}/api/admin/audit'), headers: headers),
        http.get(Uri.parse('${AppConstants.baseUrl}/api/admin/active-users'), headers: headers),
        http.get(Uri.parse('${AppConstants.baseUrl}/api/admin/audit-logs?limit=50'), headers: headers),
        http.get(Uri.parse('${AppConstants.baseUrl}/api/admin/audit-logs/summary'), headers: headers),
      ]);

      setState(() {
        if (responses[0].statusCode == 200) _stats = jsonDecode(responses[0].body);
        if (responses[1].statusCode == 200) _audit = jsonDecode(responses[1].body);
        if (responses[2].statusCode == 200) _activeUsers = jsonDecode(responses[2].body);
        if (responses[3].statusCode == 200) _auditLogs = jsonDecode(responses[3].body);
        if (responses[4].statusCode == 200) _auditSummary = jsonDecode(responses[4].body);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading admin data: $e')),
        );
      }
    }
  }

  Future<void> _loadAuditLogs({String? action}) async {
    try {
      final headers = {
        'X-API-Key': _adminApiKey,
        'Content-Type': 'application/json',
      };
      
      String url = '${AppConstants.baseUrl}/api/admin/audit-logs?limit=100';
      if (action != null && action.isNotEmpty) {
        url += '&action=$action';
      }
      
      final response = await http.get(Uri.parse(url), headers: headers);
      
      if (response.statusCode == 200 && mounted) {
        setState(() {
          _auditLogs = jsonDecode(response.body);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading audit logs: $e')),
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
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard), text: 'Overview'),
            Tab(icon: Icon(Icons.people), text: 'Users'),
            Tab(icon: Icon(Icons.history), text: 'Audit Log'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildOverviewTab(),
                _buildUsersTab(),
                _buildAuditLogTab(),
              ],
            ),
    );
  }

  Widget _buildOverviewTab() {
    return SingleChildScrollView(
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
              ],
            ),
          ],
        ),
      );
  }

  Widget _buildUsersTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
                            ],
                          ),
                        );
                      },
                    ),
                  ),

          const SizedBox(height: 32),
          
          ElevatedButton.icon(
            onPressed: _viewUsers,
            icon: const Icon(Icons.people),
            label: const Text('View All Registered Users'),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 48),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAuditLogTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Audit Summary Cards
          if (_auditSummary != null) ...[
            Text(
              'Audit Summary',
              style: Theme.of(context).textTheme.displayMedium,
            ),
            const SizedBox(height: 16),
            
            GridView.count(
              crossAxisCount: 4,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 16,
              crossAxisSpacing: 16,
              childAspectRatio: 1.5,
              children: [
                _buildStatCard(
                  'Total Events',
                  (_auditSummary!['total_events'] ?? 0).toString(),
                  Icons.event_note,
                  Colors.blue,
                ),
                _buildStatCard(
                  'Logins',
                  (_auditSummary!['action_breakdown']?['LOGIN_SUCCESS'] ?? 0).toString(),
                  Icons.login,
                  Colors.green,
                ),
                _buildStatCard(
                  'Failed Logins',
                  (_auditSummary!['action_breakdown']?['LOGIN_FAILED'] ?? 0).toString(),
                  Icons.block,
                  Colors.red,
                ),
                _buildStatCard(
                  'Signups',
                  (_auditSummary!['action_breakdown']?['SIGNUP_SUCCESS'] ?? 0).toString(),
                  Icons.person_add,
                  AppConstants.primaryTeal,
                ),
              ],
            ),
            const SizedBox(height: 24),
          ],

          // Filter by Action
          Row(
            children: [
              Text(
                'Audit Logs',
                style: Theme.of(context).textTheme.displayMedium?.copyWith(fontSize: 20),
              ),
              const Spacer(),
              DropdownButton<String>(
                value: _selectedAction,
                hint: const Text('Filter by action'),
                items: [
                  const DropdownMenuItem(value: null, child: Text('All Actions')),
                  const DropdownMenuItem(value: 'LOGIN_SUCCESS', child: Text('Successful Logins')),
                  const DropdownMenuItem(value: 'LOGIN_FAILED', child: Text('Failed Logins')),
                  const DropdownMenuItem(value: 'SIGNUP_SUCCESS', child: Text('Signups')),
                  const DropdownMenuItem(value: 'PASSWORD_RESET', child: Text('Password Resets')),
                ],
                onChanged: (value) {
                  setState(() => _selectedAction = value);
                  _loadAuditLogs(action: value);
                },
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Audit Logs List
          if (_auditLogs != null && _auditLogs!['logs'] != null)
            Card(
              child: (_auditLogs!['logs'] as List).isEmpty
                  ? const Padding(
                      padding: EdgeInsets.all(32),
                      child: Center(child: Text('No audit logs found')),
                    )
                  : ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: (_auditLogs!['logs'] as List).length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final log = _auditLogs!['logs'][index];
                        final isSuccess = log['status'] == 'success';
                        
                        return ListTile(
                          leading: CircleAvatar(
                            backgroundColor: isSuccess ? Colors.green : Colors.red,
                            child: Icon(
                              _getActionIcon(log['action']),
                              color: Colors.white,
                              size: 20,
                            ),
                          ),
                          title: Row(
                            children: [
                              Text(
                                _formatAction(log['action'] ?? 'UNKNOWN'),
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isSuccess ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  log['status'] ?? 'unknown',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: isSuccess ? Colors.green : Colors.red,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                log['username'] != null ? '@${log['username']}' : 'Unknown user',
                              ),
                              Text(
                                _formatTimestamp(log['timestamp']),
                                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                              ),
                            ],
                          ),
                          trailing: log['ip_address'] != null
                              ? Text(
                                  log['ip_address'],
                                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                )
                              : null,
                          isThreeLine: true,
                        );
                      },
                    ),
            ),

          // Recent Failures Section
          if (_auditSummary != null && 
              _auditSummary!['recent_failures'] != null &&
              (_auditSummary!['recent_failures'] as List).isNotEmpty) ...[
            const SizedBox(height: 32),
            Text(
              'Recent Failures',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(fontSize: 20),
            ),
            const SizedBox(height: 16),
            Card(
              color: Colors.red.withOpacity(0.05),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: (_auditSummary!['recent_failures'] as List).length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final log = _auditSummary!['recent_failures'][index];
                  return ListTile(
                    leading: const CircleAvatar(
                      backgroundColor: Colors.red,
                      child: Icon(Icons.warning, color: Colors.white, size: 20),
                    ),
                    title: Text(_formatAction(log['action'] ?? 'UNKNOWN')),
                    subtitle: Text(log['username'] ?? 'Unknown user'),
                    trailing: Text(
                      _formatTimestamp(log['timestamp']),
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                  );
                },
              ),
            ),
          ],
        ],
      ),
    );
  }

  IconData _getActionIcon(String? action) {
    switch (action) {
      case 'LOGIN_SUCCESS':
        return Icons.login;
      case 'LOGIN_FAILED':
        return Icons.block;
      case 'SIGNUP_SUCCESS':
        return Icons.person_add;
      case 'PASSWORD_RESET':
        return Icons.lock_reset;
      case 'PASSWORD_RESET_FAILED':
        return Icons.lock_open;
      default:
        return Icons.event;
    }
  }

  String _formatAction(String action) {
    return action.replaceAll('_', ' ').split(' ').map((word) {
      if (word.isEmpty) return word;
      return word[0].toUpperCase() + word.substring(1).toLowerCase();
    }).join(' ');
  }

  String _formatTimestamp(String? timestamp) {
    if (timestamp == null) return 'Unknown time';
    try {
      final dt = DateTime.parse(timestamp);
      final now = DateTime.now();
      final diff = now.difference(dt);
      
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (e) {
      return timestamp;
    }
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