// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter

import 'dart:html' as html;

import 'package:flutter/material.dart';

Future<void> downloadUrl(
  BuildContext context,
  String url, {
  String? filename,
}) async {
  try {
    final request = await html.HttpRequest.request(
      url,
      method: 'GET',
      responseType: 'blob',
    );
    final blob = request.response as html.Blob;
    final objectUrl = html.Url.createObjectUrlFromBlob(blob);
    final anchor = html.AnchorElement(href: objectUrl)
      ..download = filename ?? _inferFilename(url)
      ..target = 'download';
    html.document.body?.append(anchor);
    anchor.click();
    anchor.remove();
    html.Url.revokeObjectUrl(objectUrl);
  } catch (_) {
    // Fallback to direct open
    final anchor = html.AnchorElement(href: url)
      ..download = filename ?? _inferFilename(url)
      ..target = 'download';
    html.document.body?.append(anchor);
    anchor.click();
    anchor.remove();
  }
}

String _inferFilename(String url) {
  final uri = Uri.tryParse(url);
  if (uri == null) return 'download';
  final segment = uri.pathSegments.isNotEmpty ? uri.pathSegments.last : '';
  if (segment.isEmpty) return 'download';
  return segment.contains('.') ? segment : '$segment.obj';
}
