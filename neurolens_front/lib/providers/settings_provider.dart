import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsProvider with ChangeNotifier {
  bool _autoStopEnabled = false;
  int _autoStopSeconds = 15;

  bool get autoStopEnabled => _autoStopEnabled;
  int get autoStopSeconds => _autoStopSeconds;

  SettingsProvider() {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _autoStopEnabled = prefs.getBool('autoStopEnabled') ?? false;
    _autoStopSeconds = prefs.getInt('autoStopSeconds') ?? 15;
    notifyListeners();
  }

  Future<void> setAutoStopEnabled(bool value) async {
    _autoStopEnabled = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('autoStopEnabled', value);
    notifyListeners();
  }

  Future<void> setAutoStopSeconds(int seconds) async {
    _autoStopSeconds = seconds;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('autoStopSeconds', seconds);
    notifyListeners();
  }
}
