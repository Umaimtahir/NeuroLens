import 'package:flutter/material.dart';
import '../models/emotion_model.dart';
import '../utils/constants.dart';

class EmotionCard extends StatelessWidget {
  final EmotionModel emotion;

  const EmotionCard({Key? key, required this.emotion}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.emoji_emotions,
                  color: _getEmotionColor(emotion.emotion),
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Current Emotion',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      Text(
                        emotion.emotion.toUpperCase(),
                        style: Theme.of(context).textTheme.displayMedium?.copyWith(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              'Intensity: ${(emotion.intensity * 100).toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: emotion.intensity,
              backgroundColor: Colors.grey[300],
              valueColor: AlwaysStoppedAnimation<Color>(
                _getEmotionColor(emotion.emotion),
              ),
              minHeight: 8,
            ),
          ],
        ),
      ),
    );
  }

  Color _getEmotionColor(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy':
      case 'excited':
        return Colors.green;
      case 'stressed':
        return AppConstants.errorRed;
      case 'focused':
        return Colors.blue;
      case 'tired':
        return Colors.orange;
      case 'neutral':
        return Colors.grey;
      default:
        return AppConstants.primaryTeal;
    }
  }
}

// ==================== lib/widgets/content_card.dart ====================
