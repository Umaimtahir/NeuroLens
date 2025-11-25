import 'dart:io';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:path_provider/path_provider.dart';
import '../utils/constants.dart';

class StorageService {
  static final StorageService _instance = StorageService._internal();
  factory StorageService() => _instance;
  StorageService._internal();

  /// Get recordings directory (cross-platform)
  Future<Directory> getRecordingsDirectory() async {
    if (kIsWeb) {
      throw UnsupportedError('Web platform uses browser downloads');
    }

    final baseDir = await getApplicationDocumentsDirectory();
    final recordingsDir = Directory('${baseDir.path}/${AppConstants.recordingsFolder}');

    if (!await recordingsDir.exists()) {
      await recordingsDir.create(recursive: true);
      print('📁 Created recordings directory: ${recordingsDir.path}');
    }

    return recordingsDir;
  }

  /// Save recording file
  Future<String> saveRecording(List<int> bytes, String filename) async {
    final recordingsDir = await getRecordingsDirectory();
    final file = File('${recordingsDir.path}/$filename');
    await file.writeAsBytes(bytes);
    print('💾 Recording saved: ${file.path}');
    return file.path;
  }

  /// List all recordings
  Future<List<FileSystemEntity>> listRecordings() async {
    try {
      final recordingsDir = await getRecordingsDirectory();
      final entities = recordingsDir.listSync();
      print('📂 Found ${entities.length} recordings');
      return entities;
    } catch (e) {
      print('❌ Error listing recordings: $e');
      return [];
    }
  }

  /// Delete recording
  Future<void> deleteRecording(String path) async {
    try {
      final file = File(path);
      if (await file.exists()) {
        await file.delete();
        print('🗑️ Deleted recording: $path');
      }
    } catch (e) {
      print('❌ Error deleting recording: $e');
    }
  }

  /// Clear all recordings
  Future<void> clearAllRecordings() async {
    try {
      final recordings = await listRecordings();
      for (var recording in recordings) {
        await recording.delete();
      }
      print('🗑️ Cleared all recordings (${recordings.length} files)');
    } catch (e) {
      print('❌ Error clearing recordings: $e');
    }
  }

  /// Get platform-specific storage info
  Future<Map<String, dynamic>> getStorageInfo() async {
    if (kIsWeb) {
      return {
        'platform': 'Web',
        'location': 'Browser Downloads',
        'path': 'N/A',
      };
    }

    final dir = await getRecordingsDirectory();
    final recordings = await listRecordings();

    return {
      'platform': kIsWeb ? 'Web' : 'Desktop/Mobile',
      'location': dir.path,
      'path': dir.path,
      'totalRecordings': recordings.length,
    };
  }
}