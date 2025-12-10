import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/theme_provider.dart';
import 'login_screen.dart';
import 'dashboard_screen.dart';
import '../utils/constants.dart';
import 'email_verification_screen.dart';
class SignupScreen extends StatefulWidget {
  const SignupScreen({Key? key}) : super(key: key);

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _acceptTerms = false;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleSignup() async {
    if (!_formKey.currentState!.validate()) return;

    if (!_acceptTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please accept the terms and conditions'),
          backgroundColor: AppConstants.errorRed,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final success = await authProvider.signup(
      name: _nameController.text,
      email: _emailController.text,
      username: _usernameController.text,
      password: _passwordController.text,
      confirmPassword: _confirmPasswordController.text,  // ✅ ADDED THIS LINE
    );

    setState(() => _isLoading = false);

    if (success && mounted) {
      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Verification code sent! Please check your email.'),
          backgroundColor: AppConstants.primaryTeal,
        ),
      );
      
      // Navigate to email verification screen
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => EmailVerificationScreen(
            email: _emailController.text.trim(),
            name: _nameController.text.trim(),
          ),
        ),
      );
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Signup failed. Username or email may already exist, or email is invalid.'),
          backgroundColor: AppConstants.errorRed,
        ),
      );
    }
  }

  void _showTermsAndConditions() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 600, maxHeight: 500),
          child: Column(
            children: [
              // Header
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppConstants.primaryTeal,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(4),
                    topRight: Radius.circular(4),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.description, color: Colors.white),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Terms & Conditions',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),
              // Content
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'NeuroLens Terms and Conditions',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Last Updated: November 18, 2025',
                        style: TextStyle(
                          fontStyle: FontStyle.italic,
                          color: Colors.grey,
                        ),
                      ),
                      SizedBox(height: 16),
                      
                      _TermsSection(
                        title: '1. Acceptance of Terms',
                        content: 'By accessing and using NeuroLens ("the App"), you agree to be bound by these Terms and Conditions. If you do not agree to these terms, please do not use the App.',
                      ),
                      
                      _TermsSection(
                        title: '2. Description of Service',
                        content: 'NeuroLens is a mental well-being monitoring application that uses camera-based emotion detection technology to help users track their emotional states during digital content consumption.\n\nFeatures include:\n• Real-time emotion detection using facial recognition\n• Content type classification (Studying, Coding, Video, Reading)\n• Weekly reports and analytics\n• Personalized recommendations\n• Secure, encrypted data storage',
                      ),
                      
                      _TermsSection(
                        title: '3. Camera Usage',
                        content: '• The App uses your device camera for emotion detection\n• Audio is NEVER recorded or captured\n• Camera access is required for real-time analysis\n• You can revoke camera permissions at any time',
                      ),
                      
                      _TermsSection(
                        title: '4. Privacy and Data Collection',
                        content: 'Data We Collect:\n• Personal Information: Name, email address, username\n• Emotion Data: Facial emotion analysis results\n• Usage Data: Session duration, content types, timestamps\n\nData Storage:\n• All data is encrypted using AES-256 encryption\n• Data is stored securely on our servers\n• You can request data deletion at any time\n\nWe DO NOT sell your personal data to third parties.',
                      ),
                      
                      _TermsSection(
                        title: '5. User Responsibilities',
                        content: 'You agree NOT to:\n• Use the App for illegal purposes\n• Attempt to breach security measures\n• Reverse engineer or modify the App\n• Upload malicious content or viruses\n• Impersonate other users',
                      ),
                      
                      _TermsSection(
                        title: '6. Medical Disclaimer',
                        content: '• Emotion detection is AI-based and may not be 100% accurate\n• The App is for informational purposes only\n• NOT a substitute for professional medical advice\n• Do not rely solely on App results for health decisions\n• Consult healthcare professionals for mental health concerns',
                      ),
                      
                      _TermsSection(
                        title: '7. Account Termination',
                        content: 'We may terminate or suspend your account if you violate these terms. You may delete your account at any time through the app settings.',
                      ),
                      
                      _TermsSection(
                        title: '8. Contact Information',
                        content: 'For questions about these Terms & Conditions, contact us at:\nEmail: support@neurolens.app',
                      ),
                    ],
                  ),
                ),
              ),
              // Footer
              Container(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    ElevatedButton(
                      onPressed: () {
                        setState(() => _acceptTerms = true);
                        Navigator.pop(context);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppConstants.primaryTeal,
                      ),
                      child: const Text('I Accept', style: TextStyle(color: Colors.white)),
                    ),
                    const SizedBox(width: 12),
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Close'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 500),
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
                        Icons.person_add,
                        size: 64,
                        color: AppConstants.primaryTeal,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Create Account',
                        style: Theme.of(context).textTheme.displayMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Sign up to get started',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 32),

                      // Full Name
                      TextFormField(
                        controller: _nameController,
                        decoration: const InputDecoration(
                          labelText: 'Full Name',
                          prefixIcon: Icon(Icons.person),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter your name';
                          }
                          if (value.length < 2) {
                            return 'Name must be at least 2 characters';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Email
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
                      const SizedBox(height: 16),

                      // Username
                      TextFormField(
                        controller: _usernameController,
                        decoration: const InputDecoration(
                          labelText: 'Username',
                          prefixIcon: Icon(Icons.account_circle),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter a username';
                          }
                          if (value.length < 3) {
                            return 'Username must be at least 3 characters';
                          }
                          if (value.contains(' ')) {
                            return 'Username cannot contain spaces';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Password
                      TextFormField(
                        controller: _passwordController,
                        obscureText: _obscurePassword,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.lock),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword ? Icons.visibility : Icons.visibility_off,
                            ),
                            onPressed: () {
                              setState(() => _obscurePassword = !_obscurePassword);
                            },
                          ),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter a password';
                          }
                          if (value.length < 8) {
                            return 'Password must be at least 8 characters';
                          }
                          if (value.length > 72) {
                            return 'Password must be less than 72 characters';
                          }
                          if (!value.contains(RegExp(r'[A-Z]'))) {
                            return 'Must contain at least one uppercase letter';
                          }
                          if (!value.contains(RegExp(r'[a-z]'))) {
                            return 'Must contain at least one lowercase letter';
                          }
                          if (!value.contains(RegExp(r'[0-9]'))) {
                            return 'Must contain at least one number';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Confirm Password
                      TextFormField(
                        controller: _confirmPasswordController,
                        obscureText: _obscureConfirmPassword,
                        decoration: InputDecoration(
                          labelText: 'Confirm Password',
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureConfirmPassword ? Icons.visibility : Icons.visibility_off,
                            ),
                            onPressed: () {
                              setState(() => _obscureConfirmPassword = !_obscureConfirmPassword);
                            },
                          ),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please confirm your password';
                          }
                          if (value != _passwordController.text) {
                            return 'Passwords do not match';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Terms and Conditions
                      Row(
                        children: [
                          Checkbox(
                            value: _acceptTerms,
                            onChanged: (value) {
                              setState(() => _acceptTerms = value ?? false);
                            },
                            activeColor: AppConstants.primaryTeal,
                          ),
                          Expanded(
                            child: Wrap(
                              children: [
                                GestureDetector(
                                  onTap: () {
                                    setState(() => _acceptTerms = !_acceptTerms);
                                  },
                                  child: Text(
                                    'I accept the ',
                                    style: Theme.of(context).textTheme.bodyMedium,
                                  ),
                                ),
                                GestureDetector(
                                  onTap: () => _showTermsAndConditions(),
                                  child: Text(
                                    'Terms & Conditions',
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      color: AppConstants.primaryTeal,
                                      decoration: TextDecoration.underline,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),

                      // Signup Button
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _handleSignup,
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
                                : const Text('Sign Up'),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Login Link
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text('Already have an account? '),
                          TextButton(
                            onPressed: () {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(builder: (_) => const LoginScreen()),
                              );
                            },
                            child: const Text('Login'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // Theme Toggle
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text('Dark Mode'),
                          const SizedBox(width: 8),
                          Switch(
                            value: themeProvider.isDarkMode,
                            onChanged: (_) => themeProvider.toggleTheme(),
                            activeColor: AppConstants.primaryTeal,
                          ),
                        ],
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

// Helper widget for terms sections
class _TermsSection extends StatelessWidget {
  final String title;
  final String content;

  const _TermsSection({
    required this.title,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            content,
            style: const TextStyle(fontSize: 14, height: 1.5),
          ),
        ],
      ),
    );
  }
}