import 'package:flutter/material.dart';
import '../utils/constants.dart';

class RecordingControl extends StatelessWidget {
  final bool isRecording;
  final String duration;
  final VoidCallback onStartRecording;
  final VoidCallback onStopRecording;

  const RecordingControl({
    Key? key,
    required this.isRecording,
    required this.duration,
    required this.onStartRecording,
    required this.onStopRecording,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isRecording) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: const BoxDecoration(
                    color: Colors.red,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  duration,
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                    fontSize: 20,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton.icon(
                onPressed: isRecording ? onStopRecording : onStartRecording,
                icon: Icon(isRecording ? Icons.stop : Icons.fiber_manual_record),
                label: Text(isRecording ? 'Stop Recording' : 'Start Recording'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isRecording ? AppConstants.errorRed : AppConstants.primaryTeal,
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                  textStyle: const TextStyle(fontSize: 16),
                ),
              ),
            ],
          ),
          if (isRecording) ...[
            const SizedBox(height: 12),
            Text(
              'Audio is disabled - Video only',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.grey,
              ),
            ),
          ],
        ],
      ),
    );
  }
}