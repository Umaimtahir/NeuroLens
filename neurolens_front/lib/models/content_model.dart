class ContentModel {
  final DateTime timestamp;
  final String category;
  final double confidence;

  ContentModel({
    required this.timestamp,
    required this.category,
    required this.confidence,
  });

  factory ContentModel.fromJson(Map<String, dynamic> json) {
    return ContentModel(
      timestamp: DateTime.parse(json['timestamp'] as String),
      category: json['category'] as String,
      confidence: (json['confidence'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'category': category,
      'confidence': confidence,
    };
  }
}