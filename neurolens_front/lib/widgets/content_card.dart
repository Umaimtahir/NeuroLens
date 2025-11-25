import 'package:flutter/material.dart';
import '../models/content_model.dart';
import '../utils/constants.dart';

class ContentCard extends StatelessWidget {
  final ContentModel content;

  const ContentCard({Key? key, required this.content}) : super(key: key);

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
                  _getContentIcon(content.category),
                  color: AppConstants.secondaryAmber,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Content Type',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      Text(
                        content.category,
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
              'Confidence: ${(content.confidence * 100).toStringAsFixed(0)}%',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: content.confidence,
              backgroundColor: Colors.grey[300],
              valueColor: const AlwaysStoppedAnimation<Color>(
                AppConstants.secondaryAmber,
              ),
              minHeight: 8,
            ),
          ],
        ),
      ),
    );
  }

  IconData _getContentIcon(String category) {
    switch (category.toLowerCase()) {
      case 'studying':
        return Icons.school;
      case 'coding':
        return Icons.code;
      case 'video':
        return Icons.play_circle;
      case 'reading':
        return Icons.book;
      default:
        return Icons.article;
    }
  }
}
