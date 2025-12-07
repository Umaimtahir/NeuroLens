import 'dart:async';
import 'package:flutter/material.dart';

/// Notification types for the app
enum NotificationType {
  stressAlert,      // High stress detected
  breakReminder,    // Suggest taking a break
  wellnessTip,      // Contextual wellness recommendation
  sessionInfo,      // Session started/stopped
  achievement,      // Positive feedback
}

/// Notification model
class AppNotification {
  final String id;
  final NotificationType type;
  final String title;
  final String message;
  final DateTime timestamp;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool isRead;

  AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    DateTime? timestamp,
    this.actionLabel,
    this.onAction,
    this.isRead = false,
  }) : timestamp = timestamp ?? DateTime.now();

  AppNotification copyWith({bool? isRead}) {
    return AppNotification(
      id: id,
      type: type,
      title: title,
      message: message,
      timestamp: timestamp,
      actionLabel: actionLabel,
      onAction: onAction,
      isRead: isRead ?? this.isRead,
    );
  }

  IconData get icon {
    switch (type) {
      case NotificationType.stressAlert:
        return Icons.warning_amber_rounded;
      case NotificationType.breakReminder:
        return Icons.free_breakfast;
      case NotificationType.wellnessTip:
        return Icons.lightbulb_outline;
      case NotificationType.sessionInfo:
        return Icons.info_outline;
      case NotificationType.achievement:
        return Icons.emoji_events;
    }
  }

  Color get color {
    switch (type) {
      case NotificationType.stressAlert:
        return Colors.orange;
      case NotificationType.breakReminder:
        return Colors.blue;
      case NotificationType.wellnessTip:
        return Colors.teal;
      case NotificationType.sessionInfo:
        return Colors.grey;
      case NotificationType.achievement:
        return Colors.green;
    }
  }
}

/// Notification service to manage alerts and recommendations
class NotificationService extends ChangeNotifier {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final List<AppNotification> _notifications = [];
  final StreamController<AppNotification> _notificationStream = StreamController<AppNotification>.broadcast();

  // Thresholds for triggering alerts
  static const double stressThreshold = 0.7;  // 70% intensity
  static const int stressDurationSeconds = 180;  // 3 minutes of continuous stress
  static const int breakReminderMinutes = 45;  // Suggest break after 45 mins

  // Tracking state
  DateTime? _sessionStartTime;
  DateTime? _lastBreakReminder;
  int _consecutiveStressCount = 0;
  String? _lastNotifiedEmotion;
  DateTime? _lastStressAlert;

  // Getters
  List<AppNotification> get notifications => List.unmodifiable(_notifications);
  Stream<AppNotification> get notificationStream => _notificationStream.stream;
  int get unreadCount => _notifications.where((n) => !n.isRead).length;

  /// Start tracking a new session
  void startSession() {
    _sessionStartTime = DateTime.now();
    _consecutiveStressCount = 0;
    _lastNotifiedEmotion = null;
    
    addNotification(AppNotification(
      id: 'session_start_${DateTime.now().millisecondsSinceEpoch}',
      type: NotificationType.sessionInfo,
      title: 'Session Started',
      message: 'Emotion monitoring is now active. Stay focused!',
    ));
  }

  /// End the current session
  void endSession({String? summary}) {
    final duration = _sessionStartTime != null 
        ? DateTime.now().difference(_sessionStartTime!)
        : Duration.zero;
    
    addNotification(AppNotification(
      id: 'session_end_${DateTime.now().millisecondsSinceEpoch}',
      type: NotificationType.sessionInfo,
      title: 'Session Ended',
      message: summary ?? 'Session duration: ${_formatDuration(duration)}',
    ));
    
    _sessionStartTime = null;
    _consecutiveStressCount = 0;
  }

  /// Process emotion data and trigger notifications if needed
  void processEmotion(String emotion, double intensity) {
    final emotionLower = emotion.toLowerCase();
    
    // Check for stress/negative emotions
    if (_isNegativeEmotion(emotionLower) && intensity >= stressThreshold) {
      _consecutiveStressCount++;
      
      // Trigger stress alert after consecutive high-stress readings
      // (3 readings at 3-second intervals = 9 seconds of stress)
      if (_consecutiveStressCount >= 3 && _canShowStressAlert()) {
        _triggerStressAlert(emotionLower, intensity);
      }
    } else {
      // Reset stress counter on positive/neutral emotions
      if (_consecutiveStressCount > 0 && !_isNegativeEmotion(emotionLower)) {
        _consecutiveStressCount = 0;
        
        // Show positive feedback if transitioning from stress
        if (_lastNotifiedEmotion != null && _isNegativeEmotion(_lastNotifiedEmotion!)) {
          _triggerWellnessTip(emotionLower, isRecovery: true);
        }
      }
    }

    // Check for break reminder
    _checkBreakReminder();
    
    // Show achievement for sustained focus
    if (emotionLower == 'focused' && intensity >= 0.8) {
      _triggerAchievement('Great Focus!', 'You\'re maintaining excellent concentration.');
    }
    
    _lastNotifiedEmotion = emotionLower;
  }

  bool _isNegativeEmotion(String emotion) {
    return ['stressed', 'angry', 'sad', 'fear', 'fearful', 'disgust'].contains(emotion);
  }

  bool _canShowStressAlert() {
    if (_lastStressAlert == null) return true;
    // Don't spam alerts - wait at least 2 minutes between stress alerts
    return DateTime.now().difference(_lastStressAlert!).inMinutes >= 2;
  }

  void _triggerStressAlert(String emotion, double intensity) {
    _lastStressAlert = DateTime.now();
    
    final tips = _getWellnessTips(emotion);
    final tip = tips.isNotEmpty ? tips.first : 'Consider taking a short break.';
    
    addNotification(AppNotification(
      id: 'stress_${DateTime.now().millisecondsSinceEpoch}',
      type: NotificationType.stressAlert,
      title: 'High ${_capitalize(emotion)} Detected',
      message: 'You seem $emotion (${(intensity * 100).toInt()}% intensity). $tip',
      actionLabel: 'Breathing Exercise',
    ));
  }

  void _triggerWellnessTip(String emotion, {bool isRecovery = false}) {
    String message;
    String title;
    
    if (isRecovery) {
      title = 'Great Recovery! 🎉';
      message = 'Your stress levels have decreased. Keep up the good work!';
    } else {
      title = 'Wellness Tip';
      final tips = _getWellnessTips(emotion);
      message = tips.isNotEmpty ? tips.first : 'Remember to take regular breaks.';
    }
    
    addNotification(AppNotification(
      id: 'wellness_${DateTime.now().millisecondsSinceEpoch}',
      type: NotificationType.wellnessTip,
      title: title,
      message: message,
    ));
  }

  void _triggerAchievement(String title, String message) {
    // Don't spam achievements - check if we already showed this recently
    final recentAchievements = _notifications
        .where((n) => n.type == NotificationType.achievement)
        .where((n) => DateTime.now().difference(n.timestamp).inMinutes < 5)
        .toList();
    
    if (recentAchievements.isNotEmpty) return;
    
    addNotification(AppNotification(
      id: 'achievement_${DateTime.now().millisecondsSinceEpoch}',
      type: NotificationType.achievement,
      title: title,
      message: message,
    ));
  }

  void _checkBreakReminder() {
    if (_sessionStartTime == null) return;
    
    final sessionDuration = DateTime.now().difference(_sessionStartTime!);
    
    // Check if we should show break reminder
    if (sessionDuration.inMinutes >= breakReminderMinutes) {
      // Only show once per break period
      if (_lastBreakReminder == null || 
          DateTime.now().difference(_lastBreakReminder!).inMinutes >= breakReminderMinutes) {
        _lastBreakReminder = DateTime.now();
        
        addNotification(AppNotification(
          id: 'break_${DateTime.now().millisecondsSinceEpoch}',
          type: NotificationType.breakReminder,
          title: 'Time for a Break? ☕',
          message: 'You\'ve been working for ${sessionDuration.inMinutes} minutes. '
              'A short break can boost productivity!',
          actionLabel: 'Take 5 min break',
        ));
      }
    }
  }

  List<String> _getWellnessTips(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'stressed':
        return [
          'Try deep breathing: inhale for 4 counts, hold for 4, exhale for 4.',
          'Step away from the screen for a 2-minute stretch.',
          'Focus on something positive for a moment.',
        ];
      case 'angry':
        return [
          'Take a few deep breaths before continuing.',
          'Consider stepping away briefly to reset.',
          'Try counting to 10 slowly.',
        ];
      case 'sad':
        return [
          'It\'s okay to feel this way. Consider taking a short break.',
          'Try listening to some uplifting music.',
          'Reach out to someone you trust if needed.',
        ];
      case 'fear':
      case 'fearful':
        return [
          'Take a moment to ground yourself with deep breaths.',
          'Remember: you\'re in a safe space.',
          'Focus on what you can control right now.',
        ];
      case 'tired':
        return [
          'Consider taking a power nap or a coffee break.',
          'Try some light stretching to energize yourself.',
          'Maybe it\'s time to wrap up for today?',
        ];
      default:
        return ['Remember to take regular breaks and stay hydrated!'];
    }
  }

  /// Add a notification
  void addNotification(AppNotification notification) {
    _notifications.insert(0, notification);
    
    // Keep only last 50 notifications
    if (_notifications.length > 50) {
      _notifications.removeLast();
    }
    
    _notificationStream.add(notification);
    notifyListeners();
    
    print('🔔 Notification: ${notification.title} - ${notification.message}');
  }

  /// Mark notification as read
  void markAsRead(String id) {
    final index = _notifications.indexWhere((n) => n.id == id);
    if (index != -1) {
      _notifications[index] = _notifications[index].copyWith(isRead: true);
      notifyListeners();
    }
  }

  /// Mark all as read
  void markAllAsRead() {
    for (int i = 0; i < _notifications.length; i++) {
      _notifications[i] = _notifications[i].copyWith(isRead: true);
    }
    notifyListeners();
  }

  /// Clear all notifications
  void clearAll() {
    _notifications.clear();
    notifyListeners();
  }

  String _formatDuration(Duration duration) {
    if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes.remainder(60)}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds.remainder(60)}s';
    } else {
      return '${duration.inSeconds}s';
    }
  }

  String _capitalize(String s) {
    if (s.isEmpty) return s;
    return s[0].toUpperCase() + s.substring(1);
  }

  @override
  void dispose() {
    _notificationStream.close();
    super.dispose();
  }
}
