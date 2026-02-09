import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/mock_service.dart';
import '../models/report_model.dart';
import '../widgets/app_shell.dart';
import '../widgets/chart_widget.dart';
import '../widgets/report_export_button.dart';
import '../utils/constants.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({Key? key}) : super(key: key);

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  final MockService _mockService = MockService();
  List<ReportModel> _reports = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    setState(() => _isLoading = true);
    final data = await _mockService.getWeeklyReports();
    setState(() {
      _reports = data.map((e) => ReportModel.fromJson(e)).toList();
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppShell(
      currentRoute: 'Reports',
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Weekly Reports',
                  style: Theme.of(context).textTheme.displayMedium,
                ),
                ReportExportButton(reports: _reports),
              ],
            ),
            const SizedBox(height: 24),

            // Stress & Focus Trend Chart
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.show_chart, color: AppConstants.primaryTeal),
                        const SizedBox(width: 8),
                        Text(
                          'Stress & Focus Trends',
                          style: Theme.of(context).textTheme.displayMedium?.copyWith(
                            fontSize: 18,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Track how your stress and focus levels change over time. Tap on any point to see details.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      height: 380,
                      child: ChartWidget(reports: _reports),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Content Distribution
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Content Distribution (This Week)',
                      style: Theme.of(context).textTheme.displayMedium?.copyWith(
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      height: 300,
                      child: _buildContentDistributionChart(),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Summary Stats
            _buildSummaryStats(),
          ],
        ),
      ),
    );
  }

  Widget _buildContentDistributionChart() {
    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: 100,
        barTouchData: BarTouchData(enabled: true),
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                const labels = ['Studying', 'Coding', 'Video', 'Reading'];
                if (value.toInt() < labels.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      labels[value.toInt()],
                      style: const TextStyle(fontSize: 12),
                    ),
                  );
                }
                return const Text('');
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) {
                return Text('${value.toInt()}%');
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        barGroups: [
          BarChartGroupData(x: 0, barRods: [BarChartRodData(toY: 35, color: AppConstants.primaryTeal)]),
          BarChartGroupData(x: 1, barRods: [BarChartRodData(toY: 28, color: AppConstants.secondaryAmber)]),
          BarChartGroupData(x: 2, barRods: [BarChartRodData(toY: 22, color: Colors.blue)]),
          BarChartGroupData(x: 3, barRods: [BarChartRodData(toY: 15, color: Colors.green)]),
        ],
      ),
    );
  }

  Widget _buildSummaryStats() {
    final avgStress = _reports.isEmpty
        ? 0.0
        : _reports.map((e) => e.avgStress).reduce((a, b) => a + b) / _reports.length;
    final avgFocus = _reports.isEmpty
        ? 0.0
        : _reports.map((e) => e.avgFocus).reduce((a, b) => a + b) / _reports.length;
    
    // Calculate trends (compare last 3 days vs first 3 days)
    String stressTrend = '→';
    String focusTrend = '→';
    Color stressTrendColor = Colors.grey;
    Color focusTrendColor = Colors.grey;
    
    if (_reports.length >= 6) {
      final firstHalfStress = _reports.take(3).map((e) => e.avgStress).reduce((a, b) => a + b) / 3;
      final lastHalfStress = _reports.skip(_reports.length - 3).map((e) => e.avgStress).reduce((a, b) => a + b) / 3;
      final firstHalfFocus = _reports.take(3).map((e) => e.avgFocus).reduce((a, b) => a + b) / 3;
      final lastHalfFocus = _reports.skip(_reports.length - 3).map((e) => e.avgFocus).reduce((a, b) => a + b) / 3;
      
      if (lastHalfStress > firstHalfStress + 0.05) {
        stressTrend = '↑';
        stressTrendColor = AppConstants.errorRed;
      } else if (lastHalfStress < firstHalfStress - 0.05) {
        stressTrend = '↓';
        stressTrendColor = Colors.green;
      }
      
      if (lastHalfFocus > firstHalfFocus + 0.05) {
        focusTrend = '↑';
        focusTrendColor = Colors.green;
      } else if (lastHalfFocus < firstHalfFocus - 0.05) {
        focusTrend = '↓';
        focusTrendColor = AppConstants.errorRed;
      }
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.analytics, color: AppConstants.primaryTeal),
                const SizedBox(width: 8),
                Text(
                  'Weekly Summary',
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                    fontSize: 18,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Your average metrics for the past week',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: _buildEnhancedStatItem(
                    'Average Stress',
                    '${(avgStress * 100).toStringAsFixed(1)}%',
                    Icons.sentiment_dissatisfied,
                    AppConstants.errorRed,
                    stressTrend,
                    stressTrendColor,
                    _getStressLevel(avgStress),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildEnhancedStatItem(
                    'Average Focus',
                    '${(avgFocus * 100).toStringAsFixed(1)}%',
                    Icons.psychology,
                    AppConstants.primaryTeal,
                    focusTrend,
                    focusTrendColor,
                    _getFocusLevel(avgFocus),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            // Progress bars
            _buildProgressBar('Stress', avgStress, AppConstants.errorRed),
            const SizedBox(height: 12),
            _buildProgressBar('Focus', avgFocus, AppConstants.primaryTeal),
          ],
        ),
      ),
    );
  }

  String _getStressLevel(double value) {
    if (value < 0.3) return 'Low';
    if (value < 0.5) return 'Moderate';
    if (value < 0.7) return 'High';
    return 'Very High';
  }

  String _getFocusLevel(double value) {
    if (value < 0.3) return 'Poor';
    if (value < 0.5) return 'Fair';
    if (value < 0.7) return 'Good';
    return 'Excellent';
  }

  Widget _buildEnhancedStatItem(
    String label, 
    String value, 
    IconData icon, 
    Color color,
    String trend,
    Color trendColor,
    String levelText,
  ) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 28, color: color),
              const SizedBox(width: 8),
              Text(
                trend,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: trendColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.displayMedium?.copyWith(
              fontSize: 28,
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: color.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              levelText,
              style: TextStyle(
                fontSize: 11,
                color: color,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressBar(String label, double value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            Text(
              '${(value * 100).toStringAsFixed(1)}%',
              style: TextStyle(
                fontSize: 12,
                color: color,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: value,
            backgroundColor: color.withOpacity(0.2),
            valueColor: AlwaysStoppedAnimation<Color>(color),
            minHeight: 8,
          ),
        ),
      ],
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, size: 32, color: color),
        const SizedBox(height: 8),
        Text(
          value,
          style: Theme.of(context).textTheme.displayMedium?.copyWith(
            fontSize: 24,
            color: color,
          ),
        ),
        Text(label, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}
