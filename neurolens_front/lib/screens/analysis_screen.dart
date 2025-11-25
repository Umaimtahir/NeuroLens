import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/analysis_provider.dart';
import '../widgets/app_shell.dart';
import '../widgets/emotion_card.dart';
import '../widgets/content_card.dart';

class AnalysisScreen extends StatelessWidget {
  const AnalysisScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AppShell(
      currentRoute: 'Analysis',
      body: Consumer<AnalysisProvider>(
        builder: (context, provider, _) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Real-time Analysis',
                  style: Theme.of(context).textTheme.displayMedium,
                ),
                const SizedBox(height: 24),

                // Current State
                Row(
                  children: [
                    Expanded(
                      child: provider.currentEmotion != null
                          ? EmotionCard(emotion: provider.currentEmotion!)
                          : const Card(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(
                            child: Text('Start recording to see emotions'),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: provider.currentContent != null
                          ? ContentCard(content: provider.currentContent!)
                          : const Card(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(
                            child: Text('Start recording to detect content'),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 32),

                // History Timeline
                Text(
                  'Session Timeline',
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                    fontSize: 20,
                  ),
                ),
                const SizedBox(height: 16),

                if (provider.emotionHistory.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(
                        child: Text('No session data yet'),
                      ),
                    ),
                  )
                else
                  Card(
                    child: ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: provider.emotionHistory.length.clamp(0, 10),
                      separatorBuilder: (_, __) => const Divider(),
                      itemBuilder: (context, index) {
                        final emotion = provider.emotionHistory[
                        provider.emotionHistory.length - 1 - index
                        ];
                        final timeStr = DateFormat('HH:mm:ss').format(emotion.timestamp);

                        return ListTile(
                          leading: Icon(
                            Icons.emoji_emotions,
                            color: _getEmotionColor(emotion.emotion),
                          ),
                          title: Text(emotion.emotion.toUpperCase()),
                          subtitle: Text(timeStr),
                          trailing: Text(
                            '${(emotion.intensity * 100).toStringAsFixed(0)}%',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        );
                      },
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  Color _getEmotionColor(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy':
      case 'excited':
        return Colors.green;
      case 'stressed':
        return Colors.red;
      case 'focused':
        return Colors.blue;
      case 'tired':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }
}