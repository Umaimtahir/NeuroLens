import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/theme_provider.dart';
import 'dashboard_screen.dart';
import '../utils/constants.dart';
import 'signup_screen.dart';
import 'forgot_password_screen.dart';
class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _isAccountLocked = false;
  int _failedAttempts = 0;
  int _remainingAttempts = 5;
  String? _lockMessage;

  // Reduce rebuilds
  final _usernameFocusNode = FocusNode();
  final _passwordFocusNode = FocusNode();

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _usernameFocusNode.dispose();
    _passwordFocusNode.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    // Unfocus to hide keyboard
    FocusScope.of(context).unfocus();

    setState(() => _isLoading = true);

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final result = await authProvider.loginWithDetails(
      _usernameController.text.trim(),
      _passwordController.text,
    );

    if (!mounted) return;

    setState(() => _isLoading = false);

    if (result['success'] == true) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const DashboardScreen()),
      );
    } else {
      // Check if account is locked
      if (result['locked'] == true) {
        setState(() {
          _isAccountLocked = true;
          _lockMessage = result['message'] ?? 'Account locked due to too many failed attempts';
          _failedAttempts = result['failed_attempts'] ?? 5;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_lockMessage!),
            backgroundColor: AppConstants.errorRed,
            duration: const Duration(seconds: 5),
          ),
        );
      } else {
        // Update failed attempts counter
        if (result['failed_attempts'] != null) {
          setState(() {
            _failedAttempts = result['failed_attempts'];
            _remainingAttempts = result['remaining_attempts'] ?? (5 - _failedAttempts);
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Invalid credentials. $_remainingAttempts attempts remaining.'),
              backgroundColor: AppConstants.errorRed,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Invalid username or password'),
              backgroundColor: AppConstants.errorRed,
            ),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return Scaffold(
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
                        Icons.visibility,
                        size: 64,
                        color: AppConstants.primaryTeal,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'NeuroLens',
                        style: Theme.of(context).textTheme.displayMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Sign in to continue',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 32),
                      TextFormField(
                        controller: _usernameController,
                        focusNode: _usernameFocusNode,
                        decoration: const InputDecoration(
                          labelText: 'Username',
                          prefixIcon: Icon(Icons.person),
                        ),
                        textInputAction: TextInputAction.next,
                        onFieldSubmitted: (_) {
                          _passwordFocusNode.requestFocus();
                        },
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter username';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _passwordController,
                        focusNode: _passwordFocusNode,
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
                        textInputAction: TextInputAction.done,
                        onFieldSubmitted: (_) => _handleLogin(),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter password';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 24),
                      
                      // Show locked account warning if locked
                      if (_isAccountLocked) ...[
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppConstants.errorRed.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppConstants.errorRed),
                          ),
                          child: Column(
                            children: [
                              const Icon(
                                Icons.lock_outline,
                                color: AppConstants.errorRed,
                                size: 48,
                              ),
                              const SizedBox(height: 12),
                              const Text(
                                'Account Locked',
                                style: TextStyle(
                                  color: AppConstants.errorRed,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 18,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _lockMessage ?? 'Too many failed login attempts. Please reset your password to unlock your account.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Colors.grey[700],
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const ForgotPasswordScreen(),
                                ),
                              );
                            },
                            icon: const Icon(Icons.lock_reset),
                            label: const Text('Reset Password to Unlock'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppConstants.primaryTeal,
                              padding: const EdgeInsets.symmetric(vertical: 16),
                            ),
                          ),
                        ),
                      ] else ...[
                        // Normal login button (only show when not locked)
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : _handleLogin,
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
                                  : const Text('Sign In'),
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 16),

                      // Forgot Password
                      TextButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const ForgotPasswordScreen(),
                            ),
                          );
                        },
                        child: const Text('Forgot Password?'),
                      ),

                      TextButton(
                        onPressed: () {
                          showDialog(
                            context: context,
                            builder: (context) => AlertDialog(
                              title: const Text('How to Use NeuroLens'),
                              content: const SingleChildScrollView(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text('📱 Getting Started:', style: TextStyle(fontWeight: FontWeight.bold)),
                                    SizedBox(height: 8),
                                    Text('1. Sign up with your email and create an account'),
                                    Text('2. Verify your email with the code sent to you'),
                                    Text('3. Log in with your credentials'),
                                    SizedBox(height: 12),
                                    Text('🎯 Features:', style: TextStyle(fontWeight: FontWeight.bold)),
                                    SizedBox(height: 8),
                                    Text('• Real-time emotion detection using your camera'),
                                    Text('• Track your emotional patterns over time'),
                                    Text('• View weekly stress and focus reports'),
                                    Text('• Get personalized recommendations'),
                                    SizedBox(height: 12),
                                    Text('👤 Guest Mode:', style: TextStyle(fontWeight: FontWeight.bold)),
                                    SizedBox(height: 8),
                                    Text('Try the app without signing up by using "Continue as Guest" option.'),
                                  ],
                                ),
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(context),
                                  child: const Text('Got it!'),
                                ),
                              ],
                            ),
                          );
                        },
                        child: const Text('Need help?'),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text("Don't have an account? "),
                          TextButton(
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const SignupScreen(),
                                ),
                              );
                            },
                            child: const Text('Sign Up'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
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

                      // GUEST MODE AT BOTTOM
                      const SizedBox(height: 24),
                      const Divider(),
                      const SizedBox(height: 16),
                      OutlinedButton.icon(
                        onPressed: () async {
                          final authProvider = Provider.of<AuthProvider>(context, listen: false);
                          final success = await authProvider.guestLogin();

                          if (success && mounted) {
                            Navigator.of(context).pushReplacement(
                              MaterialPageRoute(builder: (_) => const DashboardScreen()),
                            );
                          }
                        },
                        icon: const Icon(Icons.person_outline),
                        label: const Text('Continue as Guest'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          minimumSize: const Size(double.infinity, 50),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Limited features • No report downloads',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey,
                        ),
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