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

  /// Signup - Initiates signup (sends verification code, doesn't create account yet)
  Future<bool> signup({
    required String name,
    required String email,
    required String username,
    required String password,
    required String confirmPassword,
  }) async {
    try {
      // This now only initiates signup and sends verification code
      // Account is created after email verification
      await _apiService.signup(
        name: name,
        email: email,
        username: username,
        password: password,
        confirmPassword: confirmPassword,
      );

      // Success means verification code was sent
      // User needs to verify email before account is created
      return true;
    } catch (e) {
      print('Signup error: $e');
      return false;
    }
  }

  /// Complete signup after email verification
  Future<bool> completeSignup(String email, String code) async {
    try {
      final response = await _apiService.verifySignup(
        email: email,
        code: code,
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
      print('Complete signup error: $e');
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
      _apiService.setToken(token);
      
      // Try to fetch user data from API
      try {
        final userData = await _apiService.getCurrentUser();
        _user = UserModel.fromJson(userData).copyWith(token: token);
        _isAuthenticated = true;
        print('✅ User authenticated: ${_user?.name} (@${_user?.username})');
      } catch (e) {
        print('⚠️ Failed to fetch user data: $e');
        // Token might be expired, clear it
        await _secureStorage.delete(key: AppConstants.tokenKey);
        _isAuthenticated = false;
        _user = null;
      }
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
  /// Store verified token and user data after signup/verification
  Future<void> storeVerifiedToken(String token, {Map<String, dynamic>? userData}) async {
    await _secureStorage.write(key: AppConstants.tokenKey, value: token);
    _apiService.setToken(token);
    
    if (userData != null) {
      _user = UserModel.fromJson(userData).copyWith(token: token);
    } else {
      // Fetch user data from API if not provided
      try {
        final data = await _apiService.getCurrentUser();
        _user = UserModel.fromJson(data).copyWith(token: token);
      } catch (e) {
        print('⚠️ Failed to fetch user data: $e');
      }
    }
    
    _isAuthenticated = true;
    notifyListeners();
  }
  /// Check if current user is guest
  bool get isGuest => _user?.id == 0;
}