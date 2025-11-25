import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:provider/provider.dart';
import 'package:camera/camera.dart';

import '../providers/camera_provider.dart';
import '../providers/analysis_provider.dart';
import '../widgets/app_shell.dart';
import '../widgets/recording_control.dart';
import '../utils/constants.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({Key? key}) : super(key: key);

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen>
    with WidgetsBindingObserver {
  bool _permissionRequested = false;
  bool _permissionDenied = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeCamera();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final cameraProvider =
    Provider.of<CameraProvider>(context, listen: false);

    if (state == AppLifecycleState.paused) {
      cameraProvider.pauseCamera();
    } else if (state == AppLifecycleState.resumed) {
      cameraProvider.resumeCamera();
    }
  }

  Future<void> _initializeCamera() async {
    final cameraProvider =
    Provider.of<CameraProvider>(context, listen: false);

    if (cameraProvider.cameraPermissionGranted) {
      print('✅ Camera already has permission');
      return;
    }

    if (_permissionRequested) return;

    _permissionRequested = true;

    final shouldRequest = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Camera Permission'),
        content: const Text(
          'Allow NeuroLens to use your CAMERA only — audio will not be recorded.\n\n'
              'This is required for real-time emotion and content analysis.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Deny'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Allow'),
          ),
        ],
      ),
    );

    if (shouldRequest == true && mounted) {
      final success = await cameraProvider.initializeCamera();

      if (!success && mounted) {
        setState(() => _permissionDenied = true);
      }
    } else if (mounted) {
      setState(() => _permissionDenied = true);
    }
  }

  void _retryPermission() {
    setState(() {
      _permissionRequested = false;
      _permissionDenied = false;
    });
    _initializeCamera();
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: () async {
        final cameraProvider =
        Provider.of<CameraProvider>(context, listen: false);

        final analysisProvider =
        Provider.of<AnalysisProvider>(context, listen: false);

        cameraProvider.pauseCamera();
        analysisProvider.stopAnalysis();

        return true;
      },
      child: AppShell(
        currentRoute: 'Camera',
        body:
        Consumer2<CameraProvider, AnalysisProvider>(builder:
            (context, cameraProvider, analysisProvider, _) {
          if (_permissionDenied &&
              !cameraProvider.cameraPermissionGranted) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.videocam_off,
                      size: 80,
                      color: AppConstants.errorRed,
                    ),
                    const SizedBox(height: 24),
                    Text(
                      'Camera Access Denied',
                      style: Theme.of(context)
                          .textTheme
                          .displayMedium,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Camera permission is required.\n'
                          'Please enable camera access to continue.',
                      style:
                      Theme.of(context).textTheme.bodyLarge,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 32),
                    Wrap(
                      spacing: 16,
                      alignment: WrapAlignment.center,
                      children: [
                        ElevatedButton.icon(
                          onPressed: _retryPermission,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                          style: ElevatedButton.styleFrom(
                            padding:
                            const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 16,
                            ),
                          ),
                        ),
                        OutlinedButton.icon(
                          onPressed: () => Navigator.pop(context),
                          icon: const Icon(Icons.arrow_back),
                          label: const Text('Go Back'),
                          style: OutlinedButton.styleFrom(
                            padding:
                            const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 16,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }

          if (cameraProvider.controller == null ||
              !cameraProvider.controller!.value.isInitialized) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Initializing camera...'),
                ],
              ),
            );
          }

          return Column(
            children: [
              Expanded(
                child: Container(
                  color: Colors.black,
                  child: Center(
                    child: AspectRatio(
                      aspectRatio: cameraProvider
                          .controller!.value.aspectRatio,
                      child: CameraPreview(
                          cameraProvider.controller!),
                    ),
                  ),
                ),
              ),
              RecordingControl(
                isRecording: cameraProvider.isRecording,
                duration: cameraProvider.recordingDuration,
                onStartRecording: () async {
                  await cameraProvider.startRecording();
                  analysisProvider.startAnalysis();
                },
                onStopRecording: () async {
                  final path =
                  await cameraProvider.stopRecording();

                  analysisProvider.stopAnalysis();

                  if (path != null && mounted) {
                    final name = path.split('/').last;
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Recording saved: $name'),
                        backgroundColor:
                        AppConstants.primaryTeal,
                        duration:
                        const Duration(seconds: 3),
                      ),
                    );
                  }
                },
              ),
            ],
          );
        }),
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);

    final cameraProvider =
    Provider.of<CameraProvider>(context, listen: false);

    final analysisProvider =
    Provider.of<AnalysisProvider>(context, listen: false);

    cameraProvider.pauseCamera();
    analysisProvider.stopAnalysis();

    super.dispose();
  }
}
