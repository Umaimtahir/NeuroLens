import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/report_model.dart';
import '../utils/constants.dart';

class ChartWidget extends StatelessWidget {
  final List<ReportModel> reports;

  const ChartWidget({Key? key, required this.reports}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: 0.2,
        ),
        titlesData: FlTitlesData(
          show: true,
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                if (value.toInt() >= 0 && value.toInt() < reports.length) {
                  final date = reports[value.toInt()].date.split('-');
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '${date[2]}/${date[1]}',
                      style: const TextStyle(fontSize: 10),
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
                return Text('${(value * 100).toInt()}%');
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: (reports.length - 1).toDouble(),
        minY: 0,
        maxY: 1,
        lineBarsData: [
          // Stress Line
          LineChartBarData(
            spots: reports.asMap().entries.map((entry) {
              return FlSpot(entry.key.toDouble(), entry.value.avgStress);
            }).toList(),
            isCurved: true,
            color: AppConstants.errorRed,
            barWidth: 3,
            dotData: const FlDotData(show: true),
            belowBarData: BarAreaData(
              show: true,
              color: AppConstants.errorRed.withOpacity(0.1),
            ),
          ),
          // Focus Line
          LineChartBarData(
            spots: reports.asMap().entries.map((entry) {
              return FlSpot(entry.key.toDouble(), entry.value.avgFocus);
            }).toList(),
            isCurved: true,
            color: AppConstants.primaryTeal,
            barWidth: 3,
            dotData: const FlDotData(show: true),
            belowBarData: BarAreaData(
              show: true,
              color: AppConstants.primaryTeal.withOpacity(0.1),
            ),
          ),
        ],
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((spot) {
                final label = spot.barIndex == 0 ? 'Stress' : 'Focus';
                return LineTooltipItem(
                  '$label: ${(spot.y * 100).toStringAsFixed(0)}%',
                  const TextStyle(color: Colors.white),
                );
              }).toList();
            },
          ),
        ),
      ),
    );
  }
}