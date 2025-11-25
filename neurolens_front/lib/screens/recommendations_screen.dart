import 'package:flutter/material.dart';
import '../widgets/app_shell.dart';
import '../utils/constants.dart';

class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({Key? key}) : super(key: key);

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  final List<Map<String, dynamic>> _recommendations = [
    {
      'title': 'Take a 5-minute break',
      'description': 'Your stress levels have been elevated. A short break can help.',
      'priority': 'High',
      'done': false,
      'icon': Icons.self_improvement,
    },
    {
      'title': 'Practice deep breathing',
      'description': 'Try 4-7-8 breathing technique to reduce anxiety.',
      'priority': 'High',
      'done': false,
      'icon': Icons.air,
    },
    {
      'title': 'Adjust screen brightness',
      'description': 'Reduce eye strain by lowering brightness or using blue light filter.',
      'priority': 'Medium',
      'done': false,
      'icon': Icons.brightness_6,
    },
    {
      'title': 'Hydrate',
      'description': 'Drink a glass of water to stay hydrated.',
      'priority': 'Medium',
      'done': false,
      'icon': Icons.local_drink,
    },
    {
      'title': 'Stretch exercises',
      'description': 'Do some neck and shoulder stretches to relieve tension.',
      'priority': 'Low',
      'done': false,
      'icon': Icons.accessibility_new,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return AppShell(
      currentRoute: 'Recommendations',
      body: SingleChildScrollView(
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
              'Based on your recent activity and stress patterns',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),

            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _recommendations.length,
              itemBuilder: (context, index) {
                final rec = _recommendations[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(16),
                    leading: CircleAvatar(
                      backgroundColor: _getPriorityColor(rec['priority']),
                      child: Icon(rec['icon'], color: Colors.white),
                    ),
                    title: Text(
                      rec['title'],
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        decoration: rec['done'] ? TextDecoration.lineThrough : null,
                      ),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 8),
                        Text(rec['description']),
                        const SizedBox(height: 8),
                        Chip(
                          label: Text(
                            rec['priority'],
                            style: const TextStyle(fontSize: 12),
                          ),
                          backgroundColor: _getPriorityColor(rec['priority']).withOpacity(0.2),
                          padding: EdgeInsets.zero,
                        ),
                      ],
                    ),
                    trailing: Checkbox(
                      value: rec['done'],
                      onChanged: (value) {
                        setState(() {
                          _recommendations[index]['done'] = value ?? false;
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
    );
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
