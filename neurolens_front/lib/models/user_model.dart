class UserModel {
  final int id;
  final String name;
  final String email;
  final String? username;
  final String? token;

  UserModel({
    required this.id,
    required this.name,
    required this.email,
    this.username,
    this.token,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      name: json['name'] as String,
      email: json['email'] as String,
      username: json['username'] as String?,
      token: json['token'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'username': username,
      'token': token,
    };
  }

  UserModel copyWith({
    int? id,
    String? name,
    String? email,
    String? username,
    String? token,
  }) {
    return UserModel(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
      username: username ?? this.username,
      token: token ?? this.token,
    );
  }

  bool get isAdmin => username?.toLowerCase() == 'admin';
}