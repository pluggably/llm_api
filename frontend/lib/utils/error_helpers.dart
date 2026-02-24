import 'package:flutter/material.dart';
import 'package:pluggably_llm_client/sdk.dart';

/// Extracts a user-friendly error message from an exception,
/// stripping potentially sensitive details (headers, auth tokens, URLs with keys).
String friendlyError(Object error) {
  if (error is ApiException) {
    // Use the detail field if available, otherwise a generic message
    final detail = error.detail;
    if (detail != null && detail.isNotEmpty) {
      return detail;
    }
    return 'Request failed (${error.statusCode})';
  }
  final msg = error.toString();
  // Strip common sensitive patterns
  final sanitised = msg
      .replaceAll(RegExp(r'(sk-|Bearer |token=)[^\s,;"]+'), r'$1***')
      .replaceAll(
        RegExp(r'https?://[^\s]+'),
        '<url>',
      );
  // Keep it short
  if (sanitised.length > 200) {
    return '${sanitised.substring(0, 200)}…';
  }
  return sanitised;
}

/// Shows a red error SnackBar with a sanitised message.
void showErrorSnackBar(BuildContext context, String prefix, Object error) {
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text('$prefix: ${friendlyError(error)}'),
      backgroundColor: Colors.red,
    ),
  );
}

/// Shows a success SnackBar.
void showSuccessSnackBar(BuildContext context, String message) {
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(message)),
  );
}

/// Formats a DateTime as a relative or short date string.
String formatRelativeDate(DateTime date) {
  final now = DateTime.now();
  final diff = now.difference(date);

  if (diff.inMinutes < 1) {
    return 'Just now';
  } else if (diff.inHours < 1) {
    return '${diff.inMinutes}m ago';
  } else if (diff.inDays < 1) {
    return '${diff.inHours}h ago';
  } else if (diff.inDays < 7) {
    return '${diff.inDays}d ago';
  } else {
    return '${date.month}/${date.day}/${date.year}';
  }
}
