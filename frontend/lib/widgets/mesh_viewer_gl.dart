import 'package:flutter/material.dart';

class MeshViewer extends StatelessWidget {
  final String objUrl;
  final double height;

  const MeshViewer({super.key, required this.objUrl, this.height = 280});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      color: Colors.grey.shade900,
      alignment: Alignment.center,
      padding: const EdgeInsets.all(16),
      child: Text(
        '3D preview is only available on web for now.\nUse download to open the OBJ file.',
        style: const TextStyle(color: Colors.white70),
        textAlign: TextAlign.center,
      ),
    );
  }
}
