import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../models/emotion_model.dart';
import '../models/content_model.dart';
import '../services/api_service.dart';
import '../services/notification_service.dart';
import 'package:http/http.dart' as http;

class AnalysisProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  final NotificationService _notificationService = NotificationService();

  EmotionModel? _currentEmotion;
  ContentModel? _currentContent;
  List<EmotionModel> _emotionHistory = [];
  List<ContentModel> _contentHistory = [];

  Timer? _analysisTimer;
  bool _isAnalyzing = false;
  CameraController? _cameraController;  // Reference to shared camera

  EmotionModel? get currentEmotion => _currentEmotion;
  ContentModel? get currentContent => _currentContent;
  List<EmotionModel> get emotionHistory => _emotionHistory;
  List<ContentModel> get contentHistory => _contentHistory;
  bool get isAnalyzing => _isAnalyzing;
  CameraController? get cameraController => _cameraController;
  
  /// Access notification service for UI binding
  NotificationService get notificationService => _notificationService;
  
  /// Get all notifications
  List<AppNotification> get notifications => _notificationService.notifications;
  
  /// Get unread notification count
  int get unreadNotificationCount => _notificationService.unreadCount;

  /// Start real-time analysis with SHARED camera controller
  /// Pass in the camera controller from CameraProvider
  Future<void> startAnalysis({CameraController? sharedCamera}) async {
    if (_isAnalyzing) {
      print('⚠️ Analysis already running');
      return;
    }

    // ✅ Use shared camera controller instead of creating new one
    _cameraController = sharedCamera;

    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      print('❌ Camera not available for analysis');
      return;
    }

    print('✅ Starting analysis with shared camera');
    _isAnalyzing = true;
    _emotionHistory.clear();
    _contentHistory.clear();
    
    // ✅ Notify backend that recording started
    try {
      await _apiService.post('/api/recording/start');
      print('✅ Backend notified: recording started');
    } catch (e) {
      print('⚠️ Failed to notify backend of recording start: $e');
    }
    
    // ✅ Start notification session
    _notificationService.startSession();
    
    notifyListeners();

    // ✅ Capture and send frames every 3 seconds
    _analysisTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      if (_cameraController == null || !_cameraController!.value.isInitialized) {
        print('⚠️ Camera no longer available');
        return;
      }

      try {
        print('📸 Capturing frame for analysis...');

        // Capture image
        final image = await _cameraController!.takePicture();
        final bytes = await image.readAsBytes();

        print('📤 Sending ${bytes.length} bytes to backend...');

        // Send frame to backend
        final result = await _sendFrameToAPI(bytes);

        print('✅ Backend response: ${result['emotion']} (${result['intensity']}) - Face: ${result['face_detected']}');

        // Create models from API response
        final emotion = EmotionModel(
          emotion: result['emotion'] ?? 'neutral',
          intensity: (result['intensity'] ?? 0.5).toDouble(),
          timestamp: DateTime.now(),
          faceDetected: result['face_detected'] ?? true,
        );

        final content = ContentModel(
          timestamp: DateTime.now(),
          category: result['content'] ?? 'Unknown',
          confidence: (result['content_conf'] ?? 0.5).toDouble(),
        );

        // Update state
        _currentEmotion = emotion;
        _currentContent = content;
        
        // ✅ Process emotion for notifications
        _notificationService.processEmotion(
          emotion.emotion, 
          emotion.intensity,
        );

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
  }

  /// Send frame to backend API with multipart form data
  Future<Map<String, dynamic>> _sendFrameToAPI(Uint8List frameBytes) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('${_apiService.baseUrl}/api/analyze/frame'),
      );

      // Add headers with auth token
      final headers = _apiService.headers;
      request.headers.addAll(headers);

      // Add image file
      request.files.add(http.MultipartFile.fromBytes(
        'file',  // ✅ Make sure this matches backend parameter name
        frameBytes,
        filename: 'frame.jpg',
      ));

      print('📡 Sending request to: ${request.url}');

      var response = await request.send();
      var responseData = await response.stream.bytesToString();

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: $responseData');

      if (response.statusCode == 200) {
        return json.decode(responseData);
      } else {
        throw Exception('Backend returned ${response.statusCode}: $responseData');
      }
    } catch (e) {
      print('❌ API error: $e');
      // Return fallback data with face_detected false
      return {
        'emotion': 'neutral',
        'intensity': 0.5,
        'content': 'Unknown',
        'content_conf': 0.5,
        'face_detected': false,
      };
    }
  }

  /// Stop analysis
  Future<void> stopAnalysis() async {
    print('⏹️ Stopping analysis...');
    _isAnalyzing = false;
    _analysisTimer?.cancel();
    _analysisTimer = null;
    _cameraController = null;  // Don't dispose, just clear reference
    
    // ✅ Notify backend that recording stopped
    try {
      await _apiService.post('/api/recording/stop');
      print('✅ Backend notified: recording stopped');
    } catch (e) {
      print('⚠️ Failed to notify backend of recording stop: $e');
    }
    
    // ✅ End notification session and generate session summary
    _notificationService.endSession();
    
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
  
  /// Mark notification as read
  void markNotificationAsRead(String notificationId) {
    _notificationService.markAsRead(notificationId);
    notifyListeners();
  }
  
  /// Clear all notifications
  void clearAllNotifications() {
    _notificationService.clearAll();
    notifyListeners();
  }

  @override
  void dispose() {
    stopAnalysis();
    _notificationService.dispose();
    super.dispose();
  }
}