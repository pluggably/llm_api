// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter

import 'dart:async';
import 'dart:html' as html;
import 'dart:typed_data';

Future<Uint8List?> readClipboardImage() async {
  final clipboard = html.window.navigator.clipboard;
  if (clipboard == null) return null;

  try {
    final dynamic items = await clipboard.read();
    if (items is! Iterable) return null;
    for (final item in items) {
      final types = (item as dynamic).types as List?;
      if (types == null) continue;
      for (final type in types) {
        if (type.toString().startsWith('image/')) {
          final blob = await (item as dynamic).getType(type);
          final completer = Completer<Uint8List?>();
          final reader = html.FileReader();
          reader.readAsArrayBuffer(blob);
          reader.onLoadEnd.first.then((_) {
            final result = reader.result;
            if (result is ByteBuffer) {
              completer.complete(Uint8List.view(result));
            } else {
              completer.complete(null);
            }
          });
          return completer.future;
        }
      }
    }
  } catch (_) {
    return null;
  }

  return null;
}