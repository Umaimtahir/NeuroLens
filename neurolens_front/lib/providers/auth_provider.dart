import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';

class AuthProvider with ChangeNotifier {
  UserModel? _user;
  bool _isAuthenticated = false;
  final ApiService _apiService = ApiService();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  UserModel? get user => _user;
  bool get isAuthenticated => _isAuthenticated;

  /// Login
  Future<bool> login(String username, String password) async {
    try {
      final response = await _apiService.login(username, password);

      final user = UserModel.fromJson(response['user']);
      final token = response['token'] as String;

      _user = user.copyWith(token: token);
      _isAuthenticated = true;

      // Store token securely
      await _secureStorage.write(key: AppConstants.tokenKey, value: token);
      _apiService.setToken(token);

      notifyListeners();
      return true;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }

  /// Signup
  Future<bool> signup({
    required String name,
    required String email,
    required String username,
    required String password,
    required String confirmPassword,
  }) async {
    try {
      final response = await _apiService.signup(
        name: name,
        email: email,
        username: username,
        password: password,
        confirmPassword: confirmPassword,
      );

      final user = UserModel.fromJson(response['user']);
      final token = response['token'] as String;

      _user = user.copyWith(token: token);
      _isAuthenticated = true;

      // Store token securely
      await _secureStorage.write(key: AppConstants.tokenKey, value: token);
      _apiService.setToken(token);

      notifyListeners();
      return true;
    } catch (e) {
      print('Signup error: $e');
      return false;
    }
  }

  /// Logout
  Future<void> logout() async {
    _user = null;
    _isAuthenticated = false;
    await _secureStorage.delete(key: AppConstants.tokenKey);
    notifyListeners();
  }

  /// Check if user is logged in (on app start)
  Future<void> checkAuthStatus() async {
    final token = await _secureStorage.read(key: AppConstants.tokenKey);
    if (token != null && token.isNotEmpty) {
      _isAuthenticated = true;
      _apiService.setToken(token);

      // In production, fetch user data from API using token
      // For now, use stored token
      _user = UserModel(
        id: 1,
        name: 'User',
        email: 'user@example.com',
        token: token,
      );

      print('✅ User authenticated with token: ${token.substring(0, 10)}...');
    } else {
      print('❌ No authentication token found');
      _isAuthenticated = false;
    }
    notifyListeners();
  }
  /// Guest login
  Future<bool> guestLogin() async {
    try {
      final response = await _apiService.guestLogin();

      final user = UserModel.fromJson(response['user']);
      final token = response['token'] as String;

      _user = user.copyWith(token: token);
      _isAuthenticated = true;

      // Store token
      await _secureStorage.write(key: AppConstants.tokenKey, value: token);
      _apiService.setToken(token);

      notifyListeners();
      return true;
    } catch (e) {
      print('Guest login error: $e');
      return false;
    }
  }
  /// Store verified token
  Future<void> storeVerifiedToken(String token) async {
    await _secureStorage.write(key: AppConstants.tokenKey, value: token);
    _apiService.setToken(token);
    _isAuthenticated = true;
    notifyListeners();
  }
  /// Check if current user is guest
  bool get isGuest => _user?.id == 0;
}