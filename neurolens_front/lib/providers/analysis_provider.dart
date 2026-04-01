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
  static const Duration _analysisInterval = Duration(seconds: 1);

  EmotionModel? _currentEmotion;
  ContentModel? _currentContent;
  List<EmotionModel> _emotionHistory = [];
  List<ContentModel> _contentHistory = [];

  Timer? _analysisTimer;
  bool _isAnalyzing = false;
  bool _isProcessingFrame = false;  // Prevent overlapping requests
  CameraController? _cameraController;  // Reference to shared camera
  
  // Multiple faces detection
  bool _multipleFacesDetected = false;
  int _detectedFaceCount = 0;
  String? _multipleFacesError;
  DateTime? _lastRecommendationFetchAt;
  String? _lastRecommendationSignature;
  
  // Callback for showing error popup (set by UI)
  Function(String message, int faceCount)? onMultipleFacesDetected;
  Function(Map<String, dynamic> payload)? onRecommendationReceived;

  EmotionModel? get currentEmotion => _currentEmotion;
  ContentModel? get currentContent => _currentContent;
  List<EmotionModel> get emotionHistory => _emotionHistory;
  List<ContentModel> get contentHistory => _contentHistory;
  bool get isAnalyzing => _isAnalyzing;
  CameraController? get cameraController => _cameraController;
  bool get multipleFacesDetected => _multipleFacesDetected;
  int get detectedFaceCount => _detectedFaceCount;
  String? get multipleFacesError => _multipleFacesError;
  
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

    // Faster capture cadence improves perceived real-time emotion changes.
    _analysisTimer = Timer.periodic(_analysisInterval, (timer) async {
      // Skip if previous request is still processing
      if (_isProcessingFrame) {
        print('⏳ Skipping frame - previous request still processing');
        return;
      }
      
      if (_cameraController == null || !_cameraController!.value.isInitialized) {
        print('⚠️ Camera no longer available');
        return;
      }

      _isProcessingFrame = true;  // Lock
      try {
        print('📸 Capturing frame for analysis...');

        // Capture image
        final image = await _cameraController!.takePicture();
        final bytes = await image.readAsBytes();

        print('📤 Sending ${bytes.length} bytes to backend...');

        // Send frame to backend
        final result = await _sendFrameToAPI(bytes);
        
        // ✅ Debug: Print full response
        print('📥 Full API response: $result');
        
        // ✅ Check for multiple faces error - check multiple conditions
        final errorType = result['error']?.toString();
        final stopDetection = result['stop_detection'];
        final emotionType = result['emotion']?.toString();
        
        print('🔍 Checking: error=$errorType, emotion=$emotionType, stop_detection=$stopDetection');
        
        // Check if multiple faces detected (any of these conditions)
        final isMultipleFaces = errorType == 'multiple_faces' || 
                                stopDetection == true || 
                                emotionType == 'error';
        
        if (isMultipleFaces) {
          final faceCount = result['face_count'] ?? 2;
          final errorMessage = result['error_message']?.toString() ?? 
              'Multiple people detected ($faceCount). Please ensure only one person is in the frame.';
          
          print('🚨 MULTIPLE FACES DETECTED: $faceCount people - STOPPING!');
          
          _multipleFacesDetected = true;
          _detectedFaceCount = faceCount is int ? faceCount : 2;
          _multipleFacesError = errorMessage;
          
          // Stop analysis FIRST
          _analysisTimer?.cancel();
          _analysisTimer = null;
          _isAnalyzing = false;
          
          // Trigger the callback to show popup in UI
          if (onMultipleFacesDetected != null) {
            print('📢 Triggering popup callback...');
            onMultipleFacesDetected!(errorMessage, _detectedFaceCount);
          } else {
            print('⚠️ WARNING: onMultipleFacesDetected callback is NULL!');
          }
          
          notifyListeners();
          
          // Now do async cleanup
          try {
            await _apiService.post('/api/recording/stop');
            print('✅ Backend notified: recording stopped');
          } catch (e) {
            print('⚠️ Failed to notify backend: $e');
          }
          _notificationService.endSession();
          
          return; // Exit the timer callback
        }

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

        // Keep recommendations async so emotion updates are not delayed.
        unawaited(_fetchRecommendationsIfDue());
      } catch (e) {
        print('❌ Error analyzing frame: $e');
      } finally {
        _isProcessingFrame = false;  // Unlock - allow next frame
      }
    });
  }

  Future<void> _fetchRecommendationsIfDue() async {
    final now = DateTime.now();

    if (_lastRecommendationFetchAt != null &&
        now.difference(_lastRecommendationFetchAt!) < const Duration(seconds: 30)) {
      return;
    }

    _lastRecommendationFetchAt = now;

    try {
      final response = await _apiService.get('/api/recommendations');
      final recommendations = List<Map<String, dynamic>>.from(
        response['recommendations'] ?? [],
      );

      if (recommendations.isEmpty) {
        return;
      }

      final triggerEmotion = (response['trigger_emotion'] ?? 'neutral').toString();
      final triggerReason = (response['trigger_reason'] ?? '').toString();
      final firstTitle = (recommendations.first['title'] ?? '').toString();
      final signature = '$triggerEmotion|$triggerReason|$firstTitle';

      if (signature == _lastRecommendationSignature) {
        return;
      }

      _lastRecommendationSignature = signature;

      if (onRecommendationReceived != null) {
        onRecommendationReceived!({
          'recommendations': recommendations,
          'trigger_emotion': response['trigger_emotion'],
          'trigger_reason': response['trigger_reason'],
        });
      }
    } catch (e) {
      print('⚠️ Failed to fetch recommendations for global popup: $e');
    }
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
    _lastRecommendationFetchAt = null;
    
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
  
  /// Reset multiple faces error state
  void resetMultipleFacesError() {
    _multipleFacesDetected = false;
    _detectedFaceCount = 0;
    _multipleFacesError = null;
    notifyListeners();
  }

  /// Clear history
  void clearHistory() {
    _emotionHistory.clear();
    _contentHistory.clear();
    _currentEmotion = null;
    _currentContent = null;
    _lastRecommendationSignature = null;
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