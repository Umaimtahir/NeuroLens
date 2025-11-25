import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class KeyboardShortcuts extends StatelessWidget {
  final Widget child;
  final VoidCallback? onStartStopRecording;
  final VoidCallback? onOpenCamera;

  const KeyboardShortcuts({
    Key? key,
    required this.child,
    this.onStartStopRecording,
    this.onOpenCamera,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Focus(
      autofocus: true,
      onKey: (node, event) {
        if (event is RawKeyDownEvent) {
          // Ctrl+R for Start/Stop Recording
          if (event.isControlPressed && event.logicalKey == LogicalKeyboardKey.keyR) {
            onStartStopRecording?.call();
            return KeyEventResult.handled;
          }
          // Ctrl+L for Open Camera
          if (event.isControlPressed && event.logicalKey == LogicalKeyboardKey.keyL) {
            onOpenCamera?.call();
            return KeyEventResult.handled;
          }
        }
        return KeyEventResult.ignored;
      },
      child: child,
    );
  }
}