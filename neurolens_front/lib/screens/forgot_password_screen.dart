import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../utils/constants.dart';
import 'reset_password_screen.dart';

class ForgotPasswordScreen extends StatefulWidget {
const ForgotPasswordScreen({Key? key}) : super(key: key);

@override
State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
final _formKey = GlobalKey<FormState>();
final _emailController = TextEditingController();
bool _isLoading = false;

@override
void dispose() {
_emailController.dispose();
super.dispose();
}

Future<void> _sendResetCode() async {
if (!_formKey.currentState!.validate()) return;

setState(() => _isLoading = true);

try {
final response = await http.post(
Uri.parse('${AppConstants.baseUrl}/api/auth/forgot-password'),
headers: {'Content-Type': 'application/json'},
body: jsonEncode({'email': _emailController.text.trim()}),
).timeout(const Duration(seconds: 10));

setState(() => _isLoading = false);

if (mounted) {
if (response.statusCode == 200) {
Navigator.push(
context,
MaterialPageRoute(
builder: (_) => ResetPasswordScreen(
email: _emailController.text.trim(),
),
),
);
} else {
ScaffoldMessenger.of(context).showSnackBar(
SnackBar(
content: Text('Failed to send reset code'),
backgroundColor: AppConstants.errorRed,
),
);
}
}
} catch (e) {
setState(() => _isLoading = false);
if (mounted) {
ScaffoldMessenger.of(context).showSnackBar(
SnackBar(
content: Text('Error: $e'),
backgroundColor: AppConstants.errorRed,
),
);
}
}
}

@override
Widget build(BuildContext context) {
return Scaffold(
appBar: AppBar(
title: const Text('Forgot Password'),
),
body: Center(
child: SingleChildScrollView(
padding: const EdgeInsets.all(24),
child: ConstrainedBox(
constraints: const BoxConstraints(maxWidth: 450),
child: Card(
elevation: 8,
child: Padding(
padding: const EdgeInsets.all(32),
child: Form(
key: _formKey,
child: Column(
mainAxisSize: MainAxisSize.min,
children: [
Icon(
Icons.lock_reset,
size: 64,
color: AppConstants.primaryTeal,
),
const SizedBox(height: 16),
Text(
'Reset Password',
style: Theme.of(context).textTheme.displayMedium,
),
const SizedBox(height: 8),
Text(
'Enter your email to receive a reset code',
style: Theme.of(context).textTheme.bodyMedium,
textAlign: TextAlign.center,
),
const SizedBox(height: 32),
TextFormField(
controller: _emailController,
keyboardType: TextInputType.emailAddress,
decoration: const InputDecoration(
labelText: 'Email',
prefixIcon: Icon(Icons.email),
),
validator: (value) {
if (value == null || value.isEmpty) {
return 'Please enter your email';
}
if (!value.contains('@') || !value.contains('.')) {
return 'Please enter a valid email';
}
return null;
},
),
const SizedBox(height: 24),
SizedBox(
width: double.infinity,
child: ElevatedButton(
onPressed: _isLoading ? null : _sendResetCode,
child: Padding(
padding: const EdgeInsets.symmetric(vertical: 16),
child: _isLoading
? const SizedBox(
height: 20,
width: 20,
child: CircularProgressIndicator(
strokeWidth: 2,
valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
),
)
    : const Text('Send Reset Code'),
),
),
),
const SizedBox(height: 16),
Text(
'Check your email for the 6-digit code',
style: Theme.of(context).textTheme.bodySmall,
textAlign: TextAlign.center,
),
],
),
),
),
),
),
),
),
);
}
}