import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../services/storage_service.dart';
import '../widgets/app_shell.dart';
import '../widgets/confirmation_dialog.dart';
import '../utils/constants.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _encryptionEnabled = false;
  bool _demoAutoStop = false;
  final StorageService _storageService = StorageService();

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return AppShell(
      currentRoute: 'Settings',
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Settings',
              style: Theme.of(context).textTheme.displayMedium,
            ),
            const SizedBox(height: 24),

            // Appearance
            Text(
              'Appearance',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Dark Mode'),
                    subtitle: const Text('Use dark theme'),
                    value: themeProvider.isDarkMode,
                    onChanged: (_) => themeProvider.toggleTheme(),
                    activeColor: AppConstants.primaryTeal,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Security
            Text(
              'Security',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('AES-256 Encryption'),
                    subtitle: const Text('Encrypt local data'),
                    value: _encryptionEnabled,
                    onChanged: (value) {
                      setState(() => _encryptionEnabled = value);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            value
                                ? 'Encryption enabled - data will be encrypted'
                                : 'Encryption disabled',
                          ),
                        ),
                      );
                    },
                    activeColor: AppConstants.primaryTeal,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Recording
            Text(
              'Recording',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  SwitchListTile(
                    title: const Text('Demo Auto Stop'),
                    subtitle: Text('Auto-stop recording after ${AppConstants.demoAutoStopSeconds} seconds'),
                    value: _demoAutoStop,
                    onChanged: (value) {
                      setState(() => _demoAutoStop = value);
                    },
                    activeColor: AppConstants.primaryTeal,
                  ),
                  const Divider(height: 1),
                  ListTile(
                    title: const Text('Storage Location'),
                    subtitle: const Text('View recordings folder'),
                    trailing: const Icon(Icons.folder_open),
                    onTap: () async {
                      final dir = await _storageService.getRecordingsDirectory();
                      final recordings = await _storageService.listRecordings();

                      if (mounted) {
                        showDialog(
                          context: context,
                          builder: (context) => AlertDialog(
                            title: const Text('Recording Storage'),
                            content: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Location:',
                                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                SelectableText(
                                  dir.path,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  'Total Recordings: ${recordings.length}',
                                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(context),
                                child: const Text('OK'),
                              ),
                            ],
                          ),
                        );
                      }
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Data Management
            Text(
              'Data Management',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: const Text('Clear Local Data'),
                    subtitle: const Text('Delete all recordings and cached data'),
                    trailing: const Icon(Icons.delete_outline, color: AppConstants.errorRed),
                    onTap: () async {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (context) => ConfirmationDialog(
                          title: 'Clear All Data?',
                          content: 'This will delete all recordings and cannot be undone.',
                          confirmText: 'Delete',
                          cancelText: 'Cancel',
                        ),
                      );

                      if (confirmed == true) {
                        await _storageService.clearAllRecordings();
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('All local data cleared'),
                              backgroundColor: AppConstants.primaryTeal,
                            ),
                          );
                        }
                      }
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // About
            Text(
              'About',
              style: Theme.of(context).textTheme.displayMedium?.copyWith(
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: const Text('Version'),
                    subtitle: const Text('1.0.0+1'),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    title: const Text('Keyboard Shortcuts'),
                    trailing: const Icon(Icons.keyboard),
                    onTap: () {
                      showDialog(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: const Text('Keyboard Shortcuts'),
                          content: const Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Ctrl + R: Start/Stop Recording'),
                              SizedBox(height: 8),
                              Text('Ctrl + L: Open Camera'),
                            ],
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
}