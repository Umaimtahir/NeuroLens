import 'package:flutter/material.dart';

class AppConstants {
  // Colors
  static const Color primaryTeal = Color(0xFF4DB6AC);
  static const Color secondaryAmber = Color(0xFFFFD166);
  static const Color backgroundLight = Color(0xFFF5F7FA);
  static const Color backgroundDark = Color(0xFF0A0E21);
  static const Color cardBackground = Color(0xFFFFFFFF);
  static const Color errorRed = Color(0xFFE57373);

  // Typography
  static const double baseFontSize = 16.0;
  static const double headingFontSize = 24.0;
  static const double subheadingFontSize = 20.0;

  // Border Radius
  static const double borderRadius = 16.0;
  static const double cardBorderRadius = 12.0;

  // API Endpoints (mock - replace with real backend)
  static const String baseUrl = 'http://localhost:8000';
  static const String loginEndpoint = '/api/auth/login';
  static const String analyzeFrameEndpoint = '/api/analyze/frame';
  static const String weeklyReportsEndpoint = '/api/reports/weekly';
  static const String uploadRecordingEndpoint = '/api/upload/recording';

  // Storage
  static const String recordingsFolder = 'recordings';
  static const String tokenKey = 'auth_token';

  // Demo Settings
  static const int demoAutoStopSeconds = 15;
  static const int mockEmotionUpdateIntervalMs = 1000;
}