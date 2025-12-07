import 'package:flutter/material.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import '../models/report_model.dart';
import '../providers/auth_provider.dart';
import '../utils/constants.dart';
import 'package:intl/intl.dart';

class ReportExportButton extends StatelessWidget {
  final List<ReportModel> reports;

  const ReportExportButton({Key? key, required this.reports}) : super(key: key);

  Future<void> _exportToCSV(BuildContext context) async {
    // ✅ DECLARE PATH VARIABLES AT THE TOP
    String fullPath = '';
    String fileName = '';

    try {
      // Create detailed CSV content
      final buffer = StringBuffer();

      // Header with metadata
      buffer.writeln('NeuroLens Weekly Report');
      buffer.writeln('Generated: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(DateTime.now())}');
      buffer.writeln('Report Period: ${reports.isNotEmpty ? reports.first.date : 'N/A'} to ${reports.isNotEmpty ? reports.last.date : 'N/A'}');
      buffer.writeln('');

      // Summary statistics
      if (reports.isNotEmpty) {
        final avgStress = reports.map((e) => e.avgStress).reduce((a, b) => a + b) / reports.length;
        final avgFocus = reports.map((e) => e.avgFocus).reduce((a, b) => a + b) / reports.length;
        final maxStress = reports.map((e) => e.avgStress).reduce((a, b) => a > b ? a : b);
        final maxFocus = reports.map((e) => e.avgFocus).reduce((a, b) => a > b ? a : b);

        buffer.writeln('SUMMARY STATISTICS');
        buffer.writeln('Average Stress Level,${(avgStress * 100).toStringAsFixed(1)}%');
        buffer.writeln('Average Focus Level,${(avgFocus * 100).toStringAsFixed(1)}%');
        buffer.writeln('Peak Stress Day,${reports.firstWhere((e) => e.avgStress == maxStress).date}');
        buffer.writeln('Peak Focus Day,${reports.firstWhere((e) => e.avgFocus == maxFocus).date}');
        buffer.writeln('');
      }

      // Detailed daily data
      buffer.writeln('DAILY BREAKDOWN');
      buffer.writeln('Date,Stress Level (%),Focus Level (%),Stress-Focus Balance');

      for (final report in reports) {
        final balance = ((report.avgFocus - report.avgStress) * 100).toStringAsFixed(1);
        buffer.writeln(
            '${report.date},'
                '${(report.avgStress * 100).toStringAsFixed(1)},'
                '${(report.avgFocus * 100).toStringAsFixed(1)},'
                '$balance'
        );
      }

      // Recommendations section
      buffer.writeln('');
      buffer.writeln('RECOMMENDATIONS');
      if (reports.isNotEmpty) {
        final avgStress = reports.map((e) => e.avgStress).reduce((a, b) => a + b) / reports.length;
        final avgFocus = reports.map((e) => e.avgFocus).reduce((a, b) => a + b) / reports.length;

        if (avgStress > 0.6) {
          buffer.writeln('- High stress levels detected. Consider taking regular breaks.');
        }
        if (avgFocus < 0.5) {
          buffer.writeln('- Focus levels below optimal. Try reducing distractions.');
        }
        if (avgStress < 0.4 && avgFocus > 0.6) {
          buffer.writeln('- Great balance! Keep up the good work.');
        }
      }

      // ✅ GET DIRECTORY AND BUILD PATH
      final directory = await getApplicationDocumentsDirectory();
      print('📁 Directory path: ${directory.path}');

      final timestamp = DateFormat('yyyyMMdd_HHmmss').format(DateTime.now());
      fileName = 'neurolens_report_$timestamp.csv';

      // ✅ BUILD FULL PATH EXPLICITLY
      fullPath = '${directory.path}${Platform.pathSeparator}$fileName';
      print('📄 Full path: $fullPath');

      // Save to file
      final file = File(fullPath);
      await file.writeAsString(buffer.toString());

      // ✅ VERIFY FILE EXISTS
      final exists = await file.exists();
      print('✅ File exists: $exists');
      print('✅ File path: ${file.path}');

      if (context.mounted) {
        showDialog(
          context: context,
          builder: (dialogContext) => AlertDialog(  // ✅ Use different context name
            title: const Row(
              children: [
                Icon(Icons.check_circle, color: AppConstants.primaryTeal),
                SizedBox(width: 8),
                Text('Report Exported'),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Your detailed report has been saved successfully!'),
                  const SizedBox(height: 16),

                  // ✅ FILE LOCATION SECTION
                  const Text(
                    'File Location:',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey[300],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey[400]!),
                    ),
                    child: SelectableText(
                      fullPath.isNotEmpty ? fullPath : 'Path unavailable',  // ✅ SHOW PATH OR FALLBACK
                      style: const TextStyle(
                        fontSize: 10,
                        fontFamily: 'Courier',
                        color: Colors.black87,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ✅ FILE NAME SECTION
                  Text(
                    'File Name:',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: AppConstants.primaryTeal,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    fileName.isNotEmpty ? fileName : 'Unknown',  // ✅ SHOW FILENAME OR FALLBACK
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ✅ REPORT INCLUDES SECTION
                  Text(
                    'Report includes:',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppConstants.primaryTeal,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text('• Summary statistics'),
                  const Text('• Daily stress & focus levels'),
                  const Text('• Personalized recommendations'),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    } catch (e, stackTrace) {
      print('❌ Export error: $e');
      print('❌ Stack trace: $stackTrace');

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Export failed: $e'),
            backgroundColor: AppConstants.errorRed,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    // Disable for guests
    if (authProvider.isGuest) {
      return ElevatedButton.icon(
        onPressed: () {
          showDialog(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Sign Up Required'),
              content: const Text(
                'Report export is only available for registered users. '
                    'Please sign up or log in to download detailed reports.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('OK'),
                ),
              ],
            ),
          );
        },
        icon: const Icon(Icons.lock),
        label: const Text('Export (Sign Up Required)'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.grey,
        ),
      );
    }

    // Full export button for registered users
    return ElevatedButton.icon(
      onPressed: () => _exportToCSV(context),
      icon: const Icon(Icons.download),
      label: const Text('Export Detailed Report'),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      ),
    );
  }
}