import 'dart:html' as html;
import 'dart:async';

class WebCameraService {
  html.MediaStream? _stream;
  html.MediaRecorder? _recorder;
  List<html.Blob> _recordedChunks = [];
  StreamController<String>? _recordingController;

  /// Initialize web camera
  Future<html.VideoElement?> initializeWebCamera() async {
    try {
      print('🌐 Initializing web camera...');

      // Request camera access (video only, no audio)
      final constraints = {
        'video': {'width': 640, 'height': 480},
        'audio': false, // No audio
      };

      _stream = await html.window.navigator.mediaDevices!
          .getUserMedia(constraints);

      final videoElement = html.VideoElement()
        ..autoplay = true
        ..muted = true
        ..srcObject = _stream
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.objectFit = 'cover';

      print('✅ Web camera initialized');
      return videoElement;
    } catch (e) {
      print('❌ Web camera error: $e');
      return null;
    }
  }

  /// Start recording on web
  Future<void> startRecording() async {
    if (_stream == null) return;

    try {
      _recordedChunks = [];
      _recordingController = StreamController<String>.broadcast();

      // Create MediaRecorder with video/webm codec
      _recorder = html.MediaRecorder(_stream!, {
        'mimeType': 'video/webm;codecs=vp9',
      });

      _recorder!.addEventListener('dataavailable', (event) {
        final html.BlobEvent blobEvent = event as html.BlobEvent;
        if (blobEvent.data != null && blobEvent.data!.size > 0) {
          _recordedChunks.add(blobEvent.data!);
        }
      });

      _recorder!.start();
      print('🎥 Web recording started');
    } catch (e) {
      print('❌ Web recording error: $e');
    }
  }

  /// Stop recording and trigger download
  Future<String?> stopRecording() async {
    if (_recorder == null) return null;

    try {
      final completer = Completer<String?>();

      _recorder!.addEventListener('stop', (event) async {
        if (_recordedChunks.isEmpty) {
          completer.complete(null);
          return;
        }

        // Create blob from recorded chunks
        final blob = html.Blob(_recordedChunks, 'video/webm');
        final url = html.Url.createObjectUrlFromBlob(blob);

        // Generate filename
        final now = DateTime.now();
        final filename = 'recording_${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}_${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}.webm';

        // Trigger download
        final anchor = html.AnchorElement(href: url)
          ..setAttribute('download', filename)
          ..click();

        print('✅ Web recording saved: $filename');
        completer.complete(filename);
      });

      _recorder!.stop();
      await completer.future;
      return completer.future;
    } catch (e) {
      print('❌ Stop recording error: $e');
      return null;
    }
  }

  /// Dispose resources
  void dispose() {
    _stream?.getTracks().forEach((track) => track.stop());
    _recorder?.stop();
    _recordingController?.close();
  }
}