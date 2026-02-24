import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

Future<void> downloadUrl(
  BuildContext context,
  String url, {
  String? filename,
}) async {
  final uri = Uri.parse(url);
  final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!context.mounted) return;
  if (!launched) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Failed to open $url')));
  }
}
