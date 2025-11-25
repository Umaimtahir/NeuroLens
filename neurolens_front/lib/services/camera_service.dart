import 'dart:async';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

class CameraService {
  static final CameraService _instance = CameraService._internal();
  factory CameraService() => _instance;
  CameraService._internal();

  List<CameraDescription>? _cameras;
  CameraController? _controller;

  /// Initialize cameras with better error handling
  Future<List<CameraDescription>> initializeCameras() async {
    try {
      print('🎥 Attempting to initialize cameras...');

      if (kIsWeb) {
        print('🌐 Platform: Web');
      } else {
        print('💻 Platform: Desktop/Mobile');
      }

      _cameras = await availableCameras();
      print('✅ Found ${_cameras?.length ?? 0} cameras');

      if (_cameras != null && _cameras!.isNotEmpty) {
        for (var i = 0; i < _cameras!.length; i++) {
          print('Camera $i: ${_cameras![i].name}');
        }
      }

      return _cameras ?? [];
    } catch (e) {
      print('❌ Error initializing cameras: $e');
      return [];
    }
  }

  /// Get camera controller with platform-specific settings
  Future<CameraController?> getCameraController() async {
    if (_cameras == null || _cameras!.isEmpty) {
      await initializeCameras();
    }

    if (_cameras != null && _cameras!.isNotEmpty) {
      // Use medium resolution for all platforms
      final resolution = ResolutionPreset.medium;

      print('🎬 Creating camera controller with $resolution preset');

      _controller = CameraController(
        _cameras![0],
        resolution,
        enableAudio: false, // IMPORTANT: Audio disabled
      );

      try {
        await _controller!.initialize();
        print('✅ Camera controller initialized successfully');
        return _controller;
      } catch (e) {
        print('❌ Error initializing camera controller: $e');
        return null;
      }
    }

    print('❌ No cameras available');
    return null;
  }

  /// Dispose controller
  void dispose() {
    _controller?.dispose();
    _controller = null;
  }

  /// Check if camera is available
  bool get hasCameras => _cameras != null && _cameras!.isNotEmpty;
}