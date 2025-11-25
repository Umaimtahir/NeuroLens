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
                    Text(
                      'Stress & Focus Trends',
                      style: Theme.of(context).textTheme.displayMedium?.copyWith(
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      height: 300,
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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Weekly Summary',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    'Avg Stress',
                    '${(avgStress * 100).toStringAsFixed(1)}%',
                    Icons.trending_up,
                    AppConstants.errorRed,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    'Avg Focus',
                    '${(avgFocus * 100).toStringAsFixed(1)}%',
                    Icons.psychology,
                    AppConstants.primaryTeal,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
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
