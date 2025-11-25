import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../models/emotion_model.dart';
import '../models/content_model.dart';
import '../services/api_service.dart';
import '../services/camera_service.dart';
import 'package:http/http.dart' as http;

class AnalysisProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  final CameraService _cameraService = CameraService();

  EmotionModel? _currentEmotion;
  ContentModel? _currentContent;
  List<EmotionModel> _emotionHistory = [];
  List<ContentModel> _contentHistory = [];

  Timer? _analysisTimer;
  bool _isAnalyzing = false;
  CameraController? _cameraController;

  EmotionModel? get currentEmotion => _currentEmotion;
  ContentModel? get currentContent => _currentContent;
  List<EmotionModel> get emotionHistory => _emotionHistory;
  List<ContentModel> get contentHistory => _contentHistory;
  bool get isAnalyzing => _isAnalyzing;
  CameraController? get cameraController => _cameraController;

  /// Start real-time analysis with camera
  Future<void> startAnalysis() async {
    if (_isAnalyzing) return;

    // Initialize camera
    _cameraController = await _cameraService.getCameraController();
    if (_cameraController == null) {
      print('❌ Camera not available');
      return;
    }

    _isAnalyzing = true;
    _emotionHistory.clear();
    _contentHistory.clear();

    // ✅ Capture and send frames every 3 seconds
    _analysisTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      if (_cameraController == null || !_cameraController!.value.isInitialized) {
        return;
      }

      try {
        print('📸 Capturing frame...');

        // Capture image from camera
        final image = await _cameraController!.takePicture();
        final bytes = await image.readAsBytes();

        print('📤 Sending frame to API...');

        // Send frame to backend
        final result = await _sendFrameToAPI(bytes);

        print('✅ API response: ${result['emotion']} (${result['intensity']})');

        // Create models from API response
        final emotion = EmotionModel(
          emotion: result['emotion'] ?? 'neutral',
          intensity: (result['intensity'] ?? 0.5).toDouble(),
          timestamp: DateTime.now(),
        );

        final content = ContentModel(
          timestamp: DateTime.now(),
          category: result['content'] ?? 'Unknown',
          confidence: (result['content_conf'] ?? 0.5).toDouble(),
        );

        // Update state
        _currentEmotion = emotion;
        _currentContent = content;

        _emotionHistory.add(emotion);
        if (_emotionHistory.length > 100) {
          _emotionHistory.removeAt(0);
        }

        _contentHistory.add(content);
        if (_contentHistory.length > 50) {
          _contentHistory.removeAt(0);
        }

        notifyListeners();
      } catch (e) {
        print('❌ Error analyzing frame: $e');
      }
    });

    notifyListeners();
  }

  /// Send frame to backend API with multipart form data
  Future<Map<String, dynamic>> _sendFrameToAPI(Uint8List frameBytes) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('${_apiService.baseUrl}/api/analyze/frame'),
      );

      // ✅ FIXED: Changed _headers to headers
      final headers = _apiService.headers;
      request.headers.addAll(headers);

      // Add image file
      request.files.add(http.MultipartFile.fromBytes(
        'file',
        frameBytes,
        filename: 'frame.jpg',
      ));

      var response = await request.send();
      var responseData = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        return json.decode(responseData);
      } else {
        throw Exception('Failed to analyze frame: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ API error: $e');
      return {
        'emotion': 'neutral',
        'intensity': 0.5,
        'content': 'Unknown',
        'content_conf': 0.5,
      };
    }
  }

  /// Stop analysis
  void stopAnalysis() {
    _isAnalyzing = false;
    _analysisTimer?.cancel();
    _analysisTimer = null;
    _cameraController?.dispose();
    _cameraController = null;
    notifyListeners();
  }

  /// Clear history
  void clearHistory() {
    _emotionHistory.clear();
    _contentHistory.clear();
    _currentEmotion = null;
    _currentContent = null;
    notifyListeners();
  }

  @override
  void dispose() {
    stopAnalysis();
    super.dispose();
  }
}