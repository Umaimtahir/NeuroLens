class EmotionModel {
  final DateTime timestamp;
  final String emotion;
  final double intensity;

  EmotionModel({
    required this.timestamp,
    required this.emotion,
    required this.intensity,
  });

  factory EmotionModel.fromJson(Map<String, dynamic> json) {
    return EmotionModel(
      timestamp: DateTime.parse(json['timestamp'] as String),
      emotion: json['emotion'] as String,
      intensity: (json['intensity'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'emotion': emotion,
      'intensity': intensity,
    };
  }
}
