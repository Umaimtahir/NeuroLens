class ReportModel {
  final String date;
  final double avgStress;
  final double avgFocus;

  ReportModel({
    required this.date,
    required this.avgStress,
    required this.avgFocus,
  });

  factory ReportModel.fromJson(Map<String, dynamic> json) {
    return ReportModel(
      date: json['date'] as String,
      avgStress: (json['avgStress'] as num).toDouble(),
      avgFocus: (json['avgFocus'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'date': date,
      'avgStress': avgStress,
      'avgFocus': avgFocus,
    };
  }
}