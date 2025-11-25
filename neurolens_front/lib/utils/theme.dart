import 'package:flutter/material.dart';
import 'constants.dart';

class AppTheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      primaryColor: AppConstants.primaryTeal,
      scaffoldBackgroundColor: AppConstants.backgroundLight,
      colorScheme: ColorScheme.light(
        primary: AppConstants.primaryTeal,
        secondary: AppConstants.secondaryAmber,
        error: AppConstants.errorRed,
        surface: AppConstants.cardBackground,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppConstants.primaryTeal,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: const TextStyle(
          fontSize: AppConstants.headingFontSize,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppConstants.cardBackground.withOpacity(0.9),
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppConstants.cardBorderRadius),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppConstants.primaryTeal,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppConstants.primaryTeal, width: 2),
        ),
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
        displayMedium: TextStyle(fontSize: AppConstants.headingFontSize, fontWeight: FontWeight.w600),
        bodyLarge: TextStyle(fontSize: AppConstants.baseFontSize),
        bodyMedium: TextStyle(fontSize: 14),
      ),
    );
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      primaryColor: AppConstants.primaryTeal,
      scaffoldBackgroundColor: AppConstants.backgroundDark,
      colorScheme: ColorScheme.dark(
        primary: AppConstants.primaryTeal,
        secondary: AppConstants.secondaryAmber,
        error: AppConstants.errorRed,
        surface: const Color(0xFF1A1F3A),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppConstants.backgroundDark,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: const TextStyle(
          fontSize: AppConstants.headingFontSize,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
      ),
      cardTheme: CardThemeData(
        color: const Color(0xFF1A1F3A),
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppConstants.cardBorderRadius),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppConstants.primaryTeal,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppConstants.primaryTeal, width: 2),
        ),
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
        displayMedium: TextStyle(fontSize: AppConstants.headingFontSize, fontWeight: FontWeight.w600, color: Colors.white),
        bodyLarge: TextStyle(fontSize: AppConstants.baseFontSize, color: Colors.white),
        bodyMedium: TextStyle(fontSize: 14, color: Colors.white70),
      ),
    );
  }
}
