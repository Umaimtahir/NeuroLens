import 'dart:async';
import 'dart:math';
import '../models/user_model.dart';
import '../models/emotion_model.dart';
import '../models/content_model.dart';
import '../models/report_model.dart';

class MockService {
  static final MockService _instance = MockService._internal();
  factory MockService() => _instance;
  MockService._internal();

  final Random _random = Random();

  // Mock emotions list
  final List<String> _emotions = ['happy', 'neutral', 'focused', 'stressed', 'tired', 'excited'];
  final List<String> _contentTypes = ['Studying', 'Coding', 'Video', 'Reading'];

  /// Mock login - accepts admin/admin
  Future<Map<String, dynamic>> login(String username, String password) async {
    await Future.delayed(const Duration(milliseconds: 500));

    if (username == 'admin' && password == 'admin') {
      return {
        'token': 'mock-jwt-123',
        'user': {
          'id': 1,
          'name': 'Admin',
          'email': 'admin@example.com',
        }
      };
    }

    throw Exception('Invalid credentials');
  }

  /// Mock analyze frame - returns random emotion and content
  Future<Map<String, dynamic>> analyzeFrame() async {
    await Future.delayed(const Duration(milliseconds: 100));

    return {
      'emotion': _emotions[_random.nextInt(_emotions.length)],
      'intensity': 0.5 + _random.nextDouble() * 0.5,
      'content': _contentTypes[_random.nextInt(_contentTypes.length)],
      'content_conf': 0.7 + _random.nextDouble() * 0.3,
      'timestamp': DateTime.now().toIso8601String(),
    };
  }

  /// Mock stream of emotions (for real-time analysis)
  Stream<EmotionModel> emotionStream() async* {
    while (true) {
      await Future.delayed(const Duration(milliseconds: 1000));
      yield EmotionModel(
        timestamp: DateTime.now(),
        emotion: _emotions[_random.nextInt(_emotions.length)],
        intensity: 0.5 + _random.nextDouble() * 0.5,
      );
    }
  }

  /// Mock stream of content detection
  Stream<ContentModel> contentStream() async* {
    while (true) {
      await Future.delayed(const Duration(milliseconds: 1500));
      yield ContentModel(
        timestamp: DateTime.now(),
        category: _contentTypes[_random.nextInt(_contentTypes.length)],
        confidence: 0.7 + _random.nextDouble() * 0.3,
      );
    }
  }

  /// Mock weekly reports
  Future<List<Map<String, dynamic>>> getWeeklyReports() async {
    await Future.delayed(const Duration(milliseconds: 500));

    final List<Map<String, dynamic>> reports = [];
    final now = DateTime.now();

    for (int i = 6; i >= 0; i--) {
      final date = now.subtract(Duration(days: i));
      reports.add({
        'date': '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}',
        'avgStress': 0.3 + _random.nextDouble() * 0.4,
        'avgFocus': 0.4 + _random.nextDouble() * 0.4,
      });
    }

    return reports;
  }

  /// Mock upload recording
  Future<Map<String, dynamic>> uploadRecording(String filePath) async {
    await Future.delayed(const Duration(milliseconds: 800));

    return {
      'status': 'ok',
      'path': 'server/recordings/${filePath.split('/').last}',
    };
  }
}