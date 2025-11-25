import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
import '../services/camera_service.dart';

class CameraProvider with ChangeNotifier {
  CameraController? _controller;
  bool _isRecording = false;
  bool _cameraPermissionGranted = false;
  bool _isInitializing = false;  // NEW: Prevent multiple inits
  DateTime? _recordingStartTime;
  Timer? _recordingTimer;
  int _recordingSeconds = 0;
  final CameraService _cameraService = CameraService();

  CameraController? get controller => _controller;
  bool get isRecording => _isRecording;
  bool get cameraPermissionGranted => _cameraPermissionGranted;
  bool get isInitializing => _isInitializing;  // NEW
  int get recordingSeconds => _recordingSeconds;

  String get recordingDuration {
    final minutes = _recordingSeconds ~/ 60;
    final seconds = _recordingSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Initialize camera (only if not already initialized)
  Future<bool> initializeCamera() async {
    // Prevent re-initialization
    if (_controller != null && _controller!.value.isInitialized) {
      print('✅ Camera already initialized');
      _cameraPermissionGranted = true;
      notifyListeners();
      return true;
    }

    if (_isInitializing) {
      print('⏳ Camera initialization in progress...');
      return false;
    }

    _isInitializing = true;
    notifyListeners();

    try {
      print('🎥 CameraProvider: Initializing camera...');
      _controller = await _cameraService.getCameraController();

      if (_controller != null && _controller!.value.isInitialized) {
        _cameraPermissionGranted = true;
        print('✅ CameraProvider: Camera initialized successfully');
        _isInitializing = false;
        notifyListeners();
        return true;
      }

      print('❌ CameraProvider: Camera initialization failed');
      _cameraPermissionGranted = false;
      _isInitializing = false;
      notifyListeners();
      return false;
    } catch (e) {
      print('❌ CameraProvider error: $e');
      _cameraPermissionGranted = false;
      _isInitializing = false;
      notifyListeners();
      return false;
    }
  }

  /// Start recording
  Future<void> startRecording() async {
    if (_controller == null || !_controller!.value.isInitialized) {
      print('❌ Cannot start recording: Camera not initialized');
      return;
    }

    try {
      print('🎬 Starting recording...');
      await _controller!.startVideoRecording();
      _isRecording = true;
      _recordingStartTime = DateTime.now();
      _recordingSeconds = 0;

      _recordingTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        _recordingSeconds++;
        notifyListeners();
      });

      print('✅ Recording started');
      notifyListeners();
    } catch (e) {
      print('❌ Start recording error: $e');
      _isRecording = false;
      notifyListeners();
    }
  }

  /// Stop recording
  Future<String?> stopRecording() async {
    if (_controller == null || !_isRecording) {
      print('❌ Cannot stop recording: Not recording');
      return null;
    }

    try {
      print('⏹️ Stopping recording...');
      final file = await _controller!.stopVideoRecording();
      _isRecording = false;
      _recordingTimer?.cancel();
      _recordingTimer = null;

      print('✅ Recording stopped: ${file.path}');
      notifyListeners();
      return file.path;
    } catch (e) {
      print('❌ Stop recording error: $e');
      _isRecording = false;
      notifyListeners();
      return null;
    }
  }

  /// Pause camera (when leaving screen) - DON'T dispose
  void pauseCamera() {
    // Just stop recording if active
    if (_isRecording) {
      stopRecording();
    }
    print('⏸️ Camera paused (not disposed)');
  }

  /// Resume camera (when returning to screen)
  Future<void> resumeCamera() async {
    if (_controller != null && _controller!.value.isInitialized) {
      print('▶️ Camera resumed');
      notifyListeners();
      return;
    }

    // Reinitialize if needed
    await initializeCamera();
  }

  /// Dispose (only when app closes)
  @override
  void dispose() {
    print('🧹 Disposing camera provider...');
    _controller?.dispose();
    _recordingTimer?.cancel();
    super.dispose();
  }
}