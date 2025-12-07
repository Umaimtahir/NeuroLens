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

  // ✅ ADD THIS GET METHOD
  Future<Map<String, dynamic>> get(String endpoint) async {
    try {
      print('📡 GET request to: $baseUrl$endpoint');

      final response = await http.get(
        Uri.parse('$baseUrl$endpoint'),
        headers: headers,
      ).timeout(const Duration(seconds: 10));

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Request failed');
      }
    } catch (e) {
      print('❌ GET request error: $e');
      rethrow;
    }
  }

  /// Get current user profile
  Future<Map<String, dynamic>> getCurrentUser() async {
    try {
      print('👤 Fetching current user...');
      return await get('/api/auth/me');
    } catch (e) {
      print('❌ Get current user error: $e');
      rethrow;
    }
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

  /// Signup - Initiates signup and sends verification code
  Future<Map<String, dynamic>> signup({
    required String name,
    required String email,
    required String username,
    required String password,
    required String confirmPassword,
  }) async {
    try {
      print('📝 Initiating signup: $username');
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

  /// Verify signup - Completes signup after email verification
  Future<Map<String, dynamic>> verifySignup({
    required String email,
    required String code,
  }) async {
    try {
      print('📧 Verifying signup for: $email');
      print('📡 API URL: $baseUrl/api/auth/verify-signup');

      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/verify-signup'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email.toLowerCase().trim(),
          'code': code.trim(),
        }),
      ).timeout(const Duration(seconds: 10));

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 201 || response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Verification failed');
      }
    } catch (e) {
      print('❌ Verify signup error: $e');
      rethrow;
    }
  }

  /// Resend signup verification code
  Future<bool> resendSignupCode(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/resend-signup-code?email=${Uri.encodeComponent(email.toLowerCase().trim())}'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      print('❌ Resend code error: $e');
      return false;
    }
  }

  /// Get weekly reports
  Future<List<Map<String, dynamic>>> getWeeklyReports() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/reports/weekly'),
        headers: headers,
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
        headers: headers,
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

  // ✅ ADD THESE OPTIONAL METHODS FOR VERIFICATION & PASSWORD RESET

  /// Verify email with code
  Future<Map<String, dynamic>> verifyEmail(String email, String code) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/verify-email'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'code': code,
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Verification failed');
      }
    } catch (e) {
      print('❌ Verification error: $e');
      rethrow;
    }
  }

  /// Resend verification code
  Future<Map<String, dynamic>> resendVerification(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/resend-verification'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to resend code');
      }
    } catch (e) {
      print('❌ Resend verification error: $e');
      rethrow;
    }
  }

  /// Forgot password - request reset code
  Future<Map<String, dynamic>> forgotPassword(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/forgot-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to send reset code');
      }
    } catch (e) {
      print('❌ Forgot password error: $e');
      rethrow;
    }
  }

  /// Reset password with code
  Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String code,
    required String newPassword,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/reset-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'code': code,
          'new_password': newPassword,
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Password reset failed');
      }
    } catch (e) {
      print('❌ Reset password error: $e');
      rethrow;
    }
  }
}