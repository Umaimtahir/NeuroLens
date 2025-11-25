import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/app_shell.dart';
import '../utils/constants.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final user = authProvider.user;

    return AppShell(
      currentRoute: 'Profile',
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Profile',
              style: Theme.of(context).textTheme.displayMedium,
            ),
            const SizedBox(height: 24),

            // Profile Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 50,
                      backgroundColor: AppConstants.primaryTeal,
                      child: Text(
                        user?.name.substring(0, 1).toUpperCase() ?? 'U',
                        style: const TextStyle(
                          fontSize: 40,
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      user?.name ?? 'User',
                      style: Theme.of(context).textTheme.displayMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      user?.email ?? 'user@example.com',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 24),
                    const Divider(),
                    const SizedBox(height: 16),
                    _buildInfoRow(context, 'User ID', user?.id.toString() ?? 'N/A'),
                    _buildInfoRow(context, 'Account Type', 'Demo Account'),
                    _buildInfoRow(context, 'Member Since', 'November 2025'),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Privacy Settings
            Text(
              'Privacy Settings',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 20,
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Local Data Storage'),
                    subtitle: const Text('Store recordings locally on device'),
                    value: true,
                    onChanged: (value) {},
                    activeColor: AppConstants.primaryTeal,
                  ),
                  const Divider(height: 1),
                  SwitchListTile(
                    title: const Text('Anonymous Analytics'),
                    subtitle: const Text('Help improve NeuroLens'),
                    value: false,
                    onChanged: (value) {},
                    activeColor: AppConstants.primaryTeal,
                  ),
                  const Divider(height: 1),
                  ListTile(
                    title: const Text('Privacy Policy'),
                    trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                    onTap: () {
                      showDialog(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: const Text('Privacy Notice'),
                          content: const SingleChildScrollView(
                            child: Text(
                              'NeuroLens stores all data locally on your device. '
                                  'No data is sent to external servers by default. '
                                  'When encryption is enabled, all local data is encrypted using AES-256. '
                                  'Recordings contain video only - audio is never captured.',
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: const Text('OK'),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}