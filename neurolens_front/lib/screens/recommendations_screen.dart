import 'package:flutter/material.dart';
import '../widgets/app_shell.dart';
import '../utils/constants.dart';
import '../services/api_service.dart';

class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({Key? key}) : super(key: key);

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  final ApiService _apiService = ApiService();
  
  List<Map<String, dynamic>> _recommendations = [];
  Map<String, bool> _completedItems = {};
  bool _hasShownInitialRecommendationPopup = false;
  String? _triggerEmotion;
  String? _triggerReason;
  Map<String, dynamic>? _emotionSummary;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadRecommendations();
  }
  
  Future<void> _loadRecommendations() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    
    try {
      final response = await _apiService.get('/api/recommendations');
      
      if (mounted) {
        setState(() {
          _recommendations = List<Map<String, dynamic>>.from(
            response['recommendations'] ?? []
          );
          _triggerEmotion = response['trigger_emotion'];
          _triggerReason = response['trigger_reason'];
          _emotionSummary = response['emotion_summary'];
          _isLoading = false;
        });

        if (!_hasShownInitialRecommendationPopup && _recommendations.isNotEmpty) {
          _hasShownInitialRecommendationPopup = true;
          _showRecommendationsPopup();
        }
      }
    } catch (e) {
      print('❌ Failed to load recommendations: $e');
      if (mounted) {
        setState(() {
          _error = 'Failed to load recommendations';
          _isLoading = false;
          // Fallback to default recommendations
          _recommendations = _getDefaultRecommendations();
        });
      }
    }
  }
  
  List<Map<String, dynamic>> _getDefaultRecommendations() {
    return [
      {
        'title': 'Take a 5-minute break',
        'description': 'Regular breaks help maintain focus and reduce stress.',
        'priority': 'Medium',
        'icon': 'self_improvement',
      },
      {
        'title': 'Stay hydrated',
        'description': 'Drink a glass of water to maintain energy levels.',
        'priority': 'Low',
        'icon': 'local_drink',
      },
      {
        'title': 'Stretch your body',
        'description': 'Do some neck and shoulder stretches to relieve tension.',
        'priority': 'Low',
        'icon': 'accessibility_new',
      },
    ];
  }
  
  Future<void> _triggerRecommendation(String? emotion) async {
    try {
      final response = await _apiService.post(
        '/api/recommendations/trigger',
        queryParams: emotion != null ? {'emotion': emotion} : null,
      );
      
      if (mounted) {
        setState(() {
          _recommendations = List<Map<String, dynamic>>.from(
            response['recommendations'] ?? []
          );
          _triggerEmotion = response['trigger_emotion'];
          _triggerReason = response['trigger_reason'];
        });

        if (_recommendations.isNotEmpty) {
          _showRecommendationsPopup();
        }
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Recommendations updated for ${response['trigger_emotion']} state'),
            backgroundColor: AppConstants.primaryTeal,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to trigger recommendations: $e'),
          backgroundColor: AppConstants.errorRed,
        ),
      );
    }
  }

  void _showRecommendationsPopup() {
    if (!mounted) return;

    final topRecommendations = _recommendations.take(2).toList();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;

      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('New Recommendations'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_triggerEmotion != null)
                Text(
                  'Detected state: ${_triggerEmotion!.toUpperCase()}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              if (_triggerReason != null) ...[
                const SizedBox(height: 8),
                Text(_triggerReason!),
              ],
              const SizedBox(height: 12),
              ...topRecommendations.map(
                (rec) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('• ${rec['title'] ?? 'Recommendation available'}'),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppShell(
      currentRoute: 'Recommendations',
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: _loadRecommendations,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Personalized Recommendations',
                    style: Theme.of(context).textTheme.displayMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _triggerReason ?? 'Based on your recent activity and stress patterns',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  
                  // Trigger emotion badge
                  if (_triggerEmotion != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: _getEmotionColor(_triggerEmotion!).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _getEmotionColor(_triggerEmotion!).withOpacity(0.3),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _getEmotionIcon(_triggerEmotion!),
                            color: _getEmotionColor(_triggerEmotion!),
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Based on: ${_triggerEmotion!.toUpperCase()}',
                            style: TextStyle(
                              color: _getEmotionColor(_triggerEmotion!),
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  
                  // Emotion summary
                  if (_emotionSummary != null && _emotionSummary!.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    _buildEmotionSummaryCard(),
                  ],
                  
                  // Quick trigger buttons
                  const SizedBox(height: 16),
                  Text(
                    'Quick Actions',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildQuickTriggerButton('Stressed', Colors.red),
                        const SizedBox(width: 8),
                        _buildQuickTriggerButton('Anxious', Colors.orange),
                        const SizedBox(width: 8),
                        _buildQuickTriggerButton('Tired', Colors.purple),
                        const SizedBox(width: 8),
                        _buildQuickTriggerButton('Sad', Colors.blue),
                        const SizedBox(width: 8),
                        _buildQuickTriggerButton('Refresh', AppConstants.primaryTeal, isRefresh: true),
                      ],
                    ),
                  ),
                  
                  const SizedBox(height: 24),

                  if (_error != null)
                    Container(
                      padding: const EdgeInsets.all(16),
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: AppConstants.errorRed.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.warning_amber, color: AppConstants.errorRed),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              _error!,
                              style: const TextStyle(color: AppConstants.errorRed),
                            ),
                          ),
                          TextButton(
                            onPressed: _loadRecommendations,
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),

                  ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _recommendations.length,
                    itemBuilder: (context, index) {
                      final rec = _recommendations[index];
                      final itemKey = '${rec['title']}_$index';
                      final isDone = _completedItems[itemKey] ?? false;
                      
                      return Card(
                        margin: const EdgeInsets.only(bottom: 16),
                        child: ListTile(
                          contentPadding: const EdgeInsets.all(16),
                          leading: CircleAvatar(
                            backgroundColor: _getPriorityColor(rec['priority'] ?? 'Low'),
                            child: Icon(_getIconFromString(rec['icon']), color: Colors.white),
                          ),
                          title: Text(
                            rec['title'] ?? '',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              decoration: isDone ? TextDecoration.lineThrough : null,
                            ),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: 8),
                              Text(rec['description'] ?? ''),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Chip(
                                    label: Text(
                                      rec['priority'] ?? 'Low',
                                      style: const TextStyle(fontSize: 12),
                                    ),
                                    backgroundColor: _getPriorityColor(rec['priority'] ?? 'Low').withOpacity(0.2),
                                    padding: EdgeInsets.zero,
                                  ),
                                  if (rec['action'] != null) ...[
                                    const SizedBox(width: 8),
                                    TextButton.icon(
                                      onPressed: () {
                                        // Mark as in-progress
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text('Starting: ${rec['action']}'),
                                            backgroundColor: AppConstants.primaryTeal,
                                          ),
                                        );
                                      },
                                      icon: const Icon(Icons.play_arrow, size: 16),
                                      label: Text(
                                        rec['action'],
                                        style: const TextStyle(fontSize: 12),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ],
                          ),
                          trailing: Checkbox(
                            value: isDone,
                            onChanged: (value) {
                              setState(() {
                                _completedItems[itemKey] = value ?? false;
                              });
                            },
                            activeColor: AppConstants.primaryTeal,
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
    );
  }
  
  Widget _buildQuickTriggerButton(String label, Color color, {bool isRefresh = false}) {
    return ElevatedButton(
      onPressed: () {
        if (isRefresh) {
          _loadRecommendations();
        } else {
          _triggerRecommendation(label.toLowerCase());
        }
      },
      style: ElevatedButton.styleFrom(
        backgroundColor: color.withOpacity(0.1),
        foregroundColor: color,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: color.withOpacity(0.3)),
        ),
      ),
      child: Text(label),
    );
  }
  
  Widget _buildEmotionSummaryCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recent Emotional Pattern',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _emotionSummary!.entries.map((entry) {
                final emotion = entry.key;
                final data = entry.value as Map<String, dynamic>;
                final count = data['count'] ?? 0;
                final intensity = data['avg_intensity'] ?? 0;
                
                return Chip(
                  avatar: CircleAvatar(
                    backgroundColor: _getEmotionColor(emotion),
                    child: Text(
                      count.toString(),
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ),
                  label: Text('$emotion (${intensity.toStringAsFixed(0)}%)'),
                  backgroundColor: _getEmotionColor(emotion).withOpacity(0.1),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }
  
  IconData _getIconFromString(String? iconName) {
    switch (iconName) {
      case 'self_improvement':
        return Icons.self_improvement;
      case 'air':
        return Icons.air;
      case 'accessibility_new':
        return Icons.accessibility_new;
      case 'local_drink':
        return Icons.local_drink;
      case 'hotel':
        return Icons.hotel;
      case 'nature':
        return Icons.nature;
      case 'directions_walk':
        return Icons.directions_walk;
      case 'fitness_center':
        return Icons.fitness_center;
      case 'people':
        return Icons.people;
      case 'music_note':
        return Icons.music_note;
      case 'timer':
        return Icons.timer;
      case 'edit_note':
        return Icons.edit_note;
      default:
        return Icons.lightbulb_outline;
    }
  }
  
  Color _getEmotionColor(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'stressed':
        return Colors.red;
      case 'anxious':
        return Colors.orange;
      case 'angry':
        return Colors.red.shade700;
      case 'sad':
        return Colors.blue;
      case 'tired':
        return Colors.purple;
      case 'focused':
        return AppConstants.primaryTeal;
      case 'happy':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
  
  IconData _getEmotionIcon(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'stressed':
        return Icons.psychology;
      case 'anxious':
        return Icons.warning_amber;
      case 'angry':
        return Icons.flash_on;
      case 'sad':
        return Icons.sentiment_dissatisfied;
      case 'tired':
        return Icons.bedtime;
      case 'focused':
        return Icons.center_focus_strong;
      case 'happy':
        return Icons.sentiment_very_satisfied;
      default:
        return Icons.emoji_emotions;
    }
  }

  Color _getPriorityColor(String priority) {
    switch (priority) {
      case 'High':
        return AppConstants.errorRed;
      case 'Medium':
        return AppConstants.secondaryAmber;
      case 'Low':
        return AppConstants.primaryTeal;
      default:
        return Colors.grey;
    }
  }
}
