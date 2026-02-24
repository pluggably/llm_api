// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter

import 'dart:async';
import 'dart:html' as html;
import 'dart:math' as math;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';
import 'package:three_dart/three_dart.dart' as three;
import 'package:three_dart_jsm/three_dart_jsm.dart' as three_jsm;

class MeshViewer extends StatefulWidget {
  final String objUrl;
  final double height;

  const MeshViewer({super.key, required this.objUrl, this.height = 280});

  @override
  State<MeshViewer> createState() => _MeshViewerState();
}

class _MeshViewerState extends State<MeshViewer> {
  three.WebGLRenderer? _renderer;
  three.Scene? _scene;
  three.PerspectiveCamera? _camera;
  three_jsm.OrbitControls? _controls;
  three.Object3D? _object;
  html.CanvasElement? _canvas;
  bool _loading = true;
  String? _error;
  Timer? _timer;
  String? _viewId;
  final _controlsKey = GlobalKey<three_jsm.DomLikeListenableState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _init());
  }

  Future<void> _init() async {
    try {
      final width = context.size?.width ?? 300;
      final height = widget.height;

      _canvas = html.CanvasElement(width: width.toInt(), height: height.toInt());
      _canvas!.style.width = '${width}px';
      _canvas!.style.height = '${height}px';

      _viewId = 'mesh-canvas-${DateTime.now().microsecondsSinceEpoch}';
      ui_web.platformViewRegistry.registerViewFactory(_viewId!, (int viewId) {
        return _canvas!;
      });

      _renderer = three.WebGLRenderer({'canvas': _canvas, 'antialias': true});
      _renderer!.setSize(width, height, false);
      _renderer!.setClearColor(three.Color(0x1E1E1E));

      _scene = three.Scene();
      _camera = three.PerspectiveCamera(45, width / height, 0.1, 1000);
      _camera!.position.set(0, 0, 3);

      final ambient = three.AmbientLight(0xffffff, 0.8);
      _scene!.add(ambient);
      final dirLight = three.DirectionalLight(0xffffff, 0.8);
      dirLight.position.set(5, 5, 5);
      _scene!.add(dirLight);

      _controls = three_jsm.OrbitControls(_camera!, _controlsKey);
      _controls!.enableDamping = true;
      _controls!.dampingFactor = 0.1;

      await _loadObj();

      if (!mounted) return;
      setState(() {
        _loading = false;
      });

      _startRenderLoop();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _loadObj() async {
    try {
      final objText = await _fetchObjText(widget.objUrl);
      final loader = three_jsm.OBJLoader(null);
      _object = loader.parse(objText);
      _object!.traverse((child) {
        if (child is three.Mesh) {
          child.material = three.MeshNormalMaterial();
        }
      });
      _object!.scale.set(1.0, 1.0, 1.0);
      _scene!.add(_object!);

      // Center and fit the object
      final box = three.Box3().setFromObject(_object!);
      final size = box.getSize(three.Vector3());
      final center = box.getCenter(three.Vector3());
      _object!.position.sub(center);
      final maxDim = math.max(size.x, math.max(size.y, size.z));
      final camZ = maxDim * 2.2;
      _camera!.position.set(0, 0, camZ);
      _camera!.lookAt(three.Vector3(0, 0, 0));
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<String> _fetchObjText(String url) async {
    final completer = Completer<html.HttpRequest>();
    final request = html.HttpRequest();
    request
      ..open('GET', url)
      ..responseType = 'text'
      ..timeout = 15000;
    request.overrideMimeType('text/plain; charset=utf-8');
    request.onLoad.first.then((_) => completer.complete(request));
    request.onError.first.then((_) {
      if (!completer.isCompleted) {
        completer.completeError(Exception('Failed to load OBJ (network error)'));
      }
    });
    request.onTimeout.first.then((_) {
      if (!completer.isCompleted) {
        completer.completeError(Exception('Failed to load OBJ (timeout)'));
      }
    });
    request.send();

    final response = await completer.future;
    final status = response.status;
    if (status != 200 && status != 0) {
      throw Exception('Failed to load OBJ ($status)');
    }
    final text = response.responseText ?? '';
    if (text.trim().isEmpty) {
      throw Exception('Failed to load OBJ (empty response)');
    }
    return text;
  }

  void _startRenderLoop() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(milliseconds: 16), (_) {
      if (!mounted || _renderer == null || _scene == null || _camera == null) {
        return;
      }
      try {
        _controls?.update();
        _renderer!.render(_scene!, _camera!);
        setState(() {});
      } catch (e) {
        _timer?.cancel();
        if (!mounted) return;
        setState(() {
          _error = '3D renderer error: $e';
        });
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controls?.dispose();
    _renderer?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Container(
        height: widget.height,
        color: Colors.grey.shade900,
        alignment: Alignment.center,
        child: Text(
          _error!,
          style: const TextStyle(color: Colors.white70),
          textAlign: TextAlign.center,
        ),
      );
    }

    if (_loading || _viewId == null) {
      return Container(
        height: widget.height,
        color: Colors.grey.shade900,
        alignment: Alignment.center,
        child: const CircularProgressIndicator(),
      );
    }

    return SizedBox(
      height: widget.height,
      child: Stack(
        children: [
          HtmlElementView(viewType: _viewId!),
          Positioned.fill(
            child: three_jsm.DomLikeListenable(
              key: _controlsKey,
              builder: (context) => const SizedBox.expand(),
            ),
          ),
        ],
      ),
    );
  }
}
