import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/analysis_provider.dart';
import '../widgets/app_shell.dart';
import '../widgets/emotion_card.dart';
import '../widgets/content_card.dart';
import '../utils/constants.dart';
import 'camera_screen.dart';
import 'reports_screen.dart';
import 'recommendations_screen.dart';
import '../utils/responsive.dart';
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final analysisProvider = Provider.of<AnalysisProvider>(context);

    return AppShell(
      currentRoute: 'Dashboard',
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome back, ${authProvider.user?.name ?? "User"}!',
              style: Theme.of(context).textTheme.displayMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Monitor your mental well-being in real-time',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 32),

            // Summary Cards
           // ADD THIS at top

// ... inside build method, replace GridView section:

          // Summary Cards
          LayoutBuilder(
          builder: (context, constraints) {
    return GridView.count(
    crossAxisCount: Responsive.getGridCrossAxisCount(context),
    shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(),
    mainAxisSpacing: 16,
    crossAxisSpacing: 16,
    childAspectRatio: Responsive.isMobile(context) ? 2.5 : 1.5,
    children: [
    _buildSummaryCard(
    context,
    'Current Emotion',
    analysisProvider.currentEmotion?.emotion.toUpperCase() ?? 'N/A',
    Icons.emoji_emotions,
    AppConstants.primaryTeal,
    ),
    _buildSummaryCard(
    context,
    'Current Content',
    analysisProvider.currentContent?.category ?? 'N/A',
    Icons.article,
    AppConstants.secondaryAmber,
    ),
    _buildSummaryCard(
    context,
    'Last Session',
    '15 min ago',
    Icons.schedule,
    Colors.blue,
    ),
    _buildSummaryCard(
    context,
    'Status',
    analysisProvider.isAnalyzing ? 'Recording' : 'Idle',
    Icons.fiber_manual_record,
    analysisProvider.isAnalyzing ? Colors.red : Colors.grey,
    ),
    ],
    );
    },
    ),

            const SizedBox(height: 32),

            // Real-time Analysis Cards
            // Real-time Analysis Cards
            if (analysisProvider.isAnalyzing) ...[
            Text(
            'Real-time Analysis',
            style: Theme.of(context).textTheme.displayMedium?.copyWith(
            fontSize: 20,
            ),
            ),
            const SizedBox(height: 16),
            Responsive.isMobile(context)
            ? Column(
            children: [
            analysisProvider.currentEmotion != null
            ? EmotionCard(emotion: analysisProvider.currentEmotion!)
                : const Card(
            child: Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: Text('Waiting for data...')),
    ),
    ),
    const SizedBox(height: 16),
    analysisProvider.currentContent != null
    ? ContentCard(content: analysisProvider.currentContent!)
        : const Card(
    child: Padding(
    padding: EdgeInsets.all(24),
    child: Center(child: Text('Waiting for data...')),
    ),
    ),
    ],
    )
        : Row(
    children: [
    Expanded(
    child: analysisProvider.currentEmotion != null
    ? EmotionCard(emotion: analysisProvider.currentEmotion!)
        : const Card(
    child: Padding(
    padding: EdgeInsets.all(24),
    child: Center(child: Text('Waiting for data...')),
    ),
    ),
    ),
    const SizedBox(width: 16),
    Expanded(
    child: analysisProvider.currentContent != null
    ? ContentCard(content: analysisProvider.currentContent!)
        : const Card(
    child: Padding(
    padding: EdgeInsets.all(24),
    child: Center(child: Text('Waiting for data...')),
    ),
    ),
    ),
    ],
    ),
    const SizedBox(height: 32),
    ],

            // Quick Actions
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 20,
              ),
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
                      () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const CameraScreen()),
                    );
                  },
                ),
                _buildActionButton(
                  context,
                  'View Reports',
                  Icons.assessment,
                      () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const ReportsScreen()),
                    );
                  },
                ),
                _buildActionButton(
                  context,
                  'Recommendations',
                  Icons.lightbulb,
                      () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const RecommendationsScreen()),
                    );
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(
      BuildContext context,
      String title,
      String value,
      IconData icon,
      Color color,
      ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                Icon(icon, color: color, size: 24),
              ],
            ),
            Text(
              value,
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(
      BuildContext context,
      String label,
      IconData icon,
      VoidCallback onPressed,
      ) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      ),
    );
  }
}
