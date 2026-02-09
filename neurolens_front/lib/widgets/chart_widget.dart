import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/report_model.dart';
import '../utils/constants.dart';

class ChartWidget extends StatelessWidget {
  final List<ReportModel> reports;

  const ChartWidget({Key? key, required this.reports}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Legend
        Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildLegendItem('Stress Level', AppConstants.errorRed),
              const SizedBox(width: 32),
              _buildLegendItem('Focus Level', AppConstants.primaryTeal),
            ],
          ),
        ),
        // Chart
        Expanded(
          child: LineChart(
            LineChartData(
              gridData: FlGridData(
                show: true,
                drawVerticalLine: true,
                verticalInterval: 1,
                horizontalInterval: 0.2,
                getDrawingHorizontalLine: (value) {
                  return FlLine(
                    color: Colors.grey.withOpacity(0.2),
                    strokeWidth: 1,
                    dashArray: [5, 5],
                  );
                },
                getDrawingVerticalLine: (value) {
                  return FlLine(
                    color: Colors.grey.withOpacity(0.1),
                    strokeWidth: 1,
                  );
                },
              ),
              titlesData: FlTitlesData(
                show: true,
                bottomTitles: AxisTitles(
                  axisNameWidget: const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text(
                      'Date',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                  ),
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 35,
                    interval: 1,
                    getTitlesWidget: (value, meta) {
                      if (value.toInt() >= 0 && value.toInt() < reports.length) {
                        final date = reports[value.toInt()].date.split('-');
                        return Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            '${date[2]}/${date[1]}',
                            style: const TextStyle(
                              fontSize: 10,
                              color: Colors.grey,
                            ),
                          ),
                        );
                      }
                      return const Text('');
                    },
                  ),
                ),
                leftTitles: AxisTitles(
                  axisNameWidget: const RotatedBox(
                    quarterTurns: -1,
                    child: Text(
                      'Percentage',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                  ),
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 45,
                    interval: 0.2,
                    getTitlesWidget: (value, meta) {
                      return Text(
                        '${(value * 100).toInt()}%',
                        style: const TextStyle(
                          fontSize: 11,
                          color: Colors.grey,
                        ),
                      );
                    },
                  ),
                ),
                topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              ),
              borderData: FlBorderData(
                show: true,
                border: Border(
                  left: BorderSide(color: Colors.grey.withOpacity(0.3)),
                  bottom: BorderSide(color: Colors.grey.withOpacity(0.3)),
                ),
              ),
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
                  curveSmoothness: 0.3,
                  color: AppConstants.errorRed,
                  barWidth: 3,
                  isStrokeCapRound: true,
                  dotData: FlDotData(
                    show: true,
                    getDotPainter: (spot, percent, barData, index) {
                      return FlDotCirclePainter(
                        radius: 5,
                        color: Colors.white,
                        strokeWidth: 2.5,
                        strokeColor: AppConstants.errorRed,
                      );
                    },
                  ),
                  belowBarData: BarAreaData(
                    show: true,
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        AppConstants.errorRed.withOpacity(0.3),
                        AppConstants.errorRed.withOpacity(0.0),
                      ],
                    ),
                  ),
                ),
                // Focus Line
                LineChartBarData(
                  spots: reports.asMap().entries.map((entry) {
                    return FlSpot(entry.key.toDouble(), entry.value.avgFocus);
                  }).toList(),
                  isCurved: true,
                  curveSmoothness: 0.3,
                  color: AppConstants.primaryTeal,
                  barWidth: 3,
                  isStrokeCapRound: true,
                  dotData: FlDotData(
                    show: true,
                    getDotPainter: (spot, percent, barData, index) {
                      return FlDotCirclePainter(
                        radius: 5,
                        color: Colors.white,
                        strokeWidth: 2.5,
                        strokeColor: AppConstants.primaryTeal,
                      );
                    },
                  ),
                  belowBarData: BarAreaData(
                    show: true,
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        AppConstants.primaryTeal.withOpacity(0.3),
                        AppConstants.primaryTeal.withOpacity(0.0),
                      ],
                    ),
                  ),
                ),
              ],
              lineTouchData: LineTouchData(
                enabled: true,
                touchTooltipData: LineTouchTooltipData(
                  tooltipRoundedRadius: 8,
                  tooltipPadding: const EdgeInsets.all(12),
                  tooltipMargin: 10,
                  getTooltipItems: (touchedSpots) {
                    return touchedSpots.map((spot) {
                      final isStress = spot.barIndex == 0;
                      final label = isStress ? '😰 Stress' : '🎯 Focus';
                      final color = isStress ? AppConstants.errorRed : AppConstants.primaryTeal;
                      return LineTooltipItem(
                        '$label: ${(spot.y * 100).toStringAsFixed(1)}%',
                        TextStyle(
                          color: color,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      );
                    }).toList();
                  },
                ),
                handleBuiltInTouches: true,
                getTouchedSpotIndicator: (barData, spotIndexes) {
                  return spotIndexes.map((index) {
                    return TouchedSpotIndicatorData(
                      FlLine(
                        color: Colors.grey.withOpacity(0.4),
                        strokeWidth: 1,
                        dashArray: [5, 5],
                      ),
                      FlDotData(
                        show: true,
                        getDotPainter: (spot, percent, bar, index) {
                          return FlDotCirclePainter(
                            radius: 8,
                            color: bar.color ?? Colors.white,
                            strokeWidth: 2,
                            strokeColor: Colors.white,
                          );
                        },
                      ),
                    );
                  }).toList();
                },
              ),
            ),
          ),
        ),
        // Insight text
        Padding(
          padding: const EdgeInsets.only(top: 16),
          child: _buildInsightText(),
        ),
      ],
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 4,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.white,
            border: Border.all(color: color, width: 2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 13,
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildInsightText() {
    if (reports.isEmpty) return const SizedBox.shrink();

    final latestStress = reports.last.avgStress;
    final latestFocus = reports.last.avgFocus;
    final avgStress = reports.map((e) => e.avgStress).reduce((a, b) => a + b) / reports.length;
    final avgFocus = reports.map((e) => e.avgFocus).reduce((a, b) => a + b) / reports.length;

    String insight;
    IconData icon;
    Color color;

    if (latestStress > avgStress && latestFocus < avgFocus) {
      insight = '⚠️ Your stress is higher and focus is lower than average. Consider taking a break!';
      icon = Icons.warning_amber;
      color = AppConstants.errorRed;
    } else if (latestStress < avgStress && latestFocus > avgFocus) {
      insight = '🎉 Great job! Your stress is lower and focus is higher than average!';
      icon = Icons.celebration;
      color = Colors.green;
    } else if (latestFocus > 0.6) {
      insight = '🎯 You\'re maintaining good focus levels. Keep it up!';
      icon = Icons.thumb_up;
      color = AppConstants.primaryTeal;
    } else {
      insight = '💡 Tip: Regular breaks can help improve both focus and reduce stress.';
      icon = Icons.lightbulb_outline;
      color = AppConstants.secondaryAmber;
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              insight,
              style: TextStyle(
                fontSize: 13,
                color: color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}