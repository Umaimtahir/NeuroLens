import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../providers/settings_provider.dart';
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
  final StorageService _storageService = StorageService();

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);
    final settingsProvider = Provider.of<SettingsProvider>(context);

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
                    title: const Text('Auto Stop Recording'),
                    subtitle: Text('Automatically stop after ${settingsProvider.autoStopSeconds} seconds'),
                    value: settingsProvider.autoStopEnabled,
                    onChanged: (value) {
                      settingsProvider.setAutoStopEnabled(value);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            value
                                ? 'Auto-stop enabled (${settingsProvider.autoStopSeconds}s)'
                                : 'Auto-stop disabled',
                          ),
                          backgroundColor: AppConstants.primaryTeal,
                        ),
                      );
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
                    subtitle: const Text('View available shortcuts'),
                    trailing: const Icon(Icons.keyboard),
                    onTap: () {
                      showDialog(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: const Text('Keyboard Shortcuts'),
                          content: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildShortcutRow('Ctrl + R', 'Start/Stop Recording'),
                              const SizedBox(height: 12),
                              _buildShortcutRow('Ctrl + L', 'Open Camera'),
                              const SizedBox(height: 16),
                              const Text(
                                'Note: Shortcuts work when the app has focus.',
                                style: TextStyle(fontSize: 12, color: Colors.grey),
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

  Widget _buildShortcutRow(String shortcut, String description) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: AppConstants.primaryTeal.withOpacity(0.2),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            shortcut,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(description),
      ],
    );
  }
}