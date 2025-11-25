import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiService {
  // ✅ Singleton pattern - ensures only one instance exists
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  // ✅ Instance variables
  String? _token;

  // ✅ baseUrl getter
  String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000';
    } else if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000';
    } else {
      return 'http://localhost:8000';
    }
  }

  void setToken(String token) {
    _token = token;
    print('🔑 Token set: ${token.substring(0, 20)}...');
  }

  // ✅ Made public (removed underscore)
  Map<String, String> get headers {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    return headers;
  }

  /// Login
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      print('🔐 Logging in: $username');
      print('📡 API URL: $baseUrl/api/auth/login');

      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username.toLowerCase().trim(),
          'password': password,
        }),
      ).timeout(const Duration(seconds: 10));

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Login failed');
      }
    } catch (e) {
      print('❌ Login error: $e');
      rethrow;
    }
  }

  /// Signup
  Future<Map<String, dynamic>> signup({
    required String name,
    required String email,
    required String username,
    required String password,
    required String confirmPassword,
  }) async {
    try {
      print('📝 Signing up: $username');
      print('📡 API URL: $baseUrl/api/auth/signup');

      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/signup'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name.trim(),
          'email': email.toLowerCase().trim(),
          'username': username.toLowerCase().trim(),
          'password': password,
          'confirm_password': confirmPassword,
        }),
      ).timeout(const Duration(seconds: 10));

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 201 || response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Signup failed');
      }
    } catch (e) {
      print('❌ Signup error: $e');
      rethrow;
    }
  }

  /// Get weekly reports
  Future<List<Map<String, dynamic>>> getWeeklyReports() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/reports/weekly'),
        headers: headers,  // ✅ Changed from _headers
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(jsonDecode(response.body));
      } else {
        throw Exception('Failed to fetch reports');
      }
    } catch (e) {
      print('❌ Reports error: $e');
      return [];
    }
  }

  /// Analyze frame
  Future<Map<String, dynamic>> analyzeFrame() async {
    try {
      print('🔑 Token: ${_token ?? "NO TOKEN SET!"}');

      final response = await http.post(
        Uri.parse('$baseUrl/api/analyze/frame'),
        headers: headers,  // ✅ Changed from _headers
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      throw Exception('Analysis failed');
    } catch (e) {
      print('❌ Analysis error: $e');
      return {
        'emotion': 'neutral',
        'intensity': 0.5,
        'content': 'Unknown',
        'content_conf': 0.5,
        'timestamp': DateTime.now().toIso8601String(),
      };
    }
  }

  /// Guest login (no signup required)
  Future<Map<String, dynamic>> guestLogin() async {
    try {
      print('👤 Guest login...');
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/guest'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      throw Exception('Guest login failed');
    } catch (e) {
      print('❌ Guest login error: $e');
      rethrow;
    }
  }
}