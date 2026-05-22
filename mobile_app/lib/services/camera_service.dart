import 'dart:async';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import '../models/camera_frame_data.dart';

// ─── Top-level function: runs inside a background isolate via compute() ─────
// Must be top-level (not a class method) for compute() to work.
List<int> _encodeFrameInIsolate(Map<String, dynamic> p) {
  final int w = p['w'] as int;
  final int h = p['h'] as int;
  final String fmt = p['fmt'] as String;
  final int quality = p['q'] as int;

  final image = img.Image(width: w, height: h);

  if (fmt == 'yuv420') {
    final Uint8List yBytes = p['y'] as Uint8List;
    final Uint8List uBytes = p['u'] as Uint8List;
    final Uint8List vBytes = p['v'] as Uint8List;
    final int yBpr = p['yBpr'] as int;
    final int uvBpr = p['uvBpr'] as int;
    final int uvBpp = p['uvBpp'] as int; // bytes-per-pixel for UV planes

    for (int row = 0; row < h; row++) {
      final int uvRow = (row >> 1) * uvBpr;
      for (int col = 0; col < w; col++) {
        final int yVal = yBytes[row * yBpr + col];
        final int uvOff = uvRow + (col >> 1) * uvBpp;
        final int uVal = uBytes[uvOff];
        final int vVal = vBytes[uvOff];

        final int r = (yVal + 1.402 * (vVal - 128)).round().clamp(0, 255);
        final int g = (yVal - 0.344136 * (uVal - 128) - 0.714136 * (vVal - 128))
            .round()
            .clamp(0, 255);
        final int b = (yVal + 1.772 * (uVal - 128)).round().clamp(0, 255);

        image.setPixelRgb(col, row, r, g, b);
      }
    }
  } else if (fmt == 'bgra8888') {
    final Uint8List bytes = p['bytes'] as Uint8List;
    final int bpr = p['bpr'] as int;
    for (int row = 0; row < h; row++) {
      for (int col = 0; col < w; col++) {
        final int off = row * bpr + col * 4;
        image.setPixelRgba(col, row, bytes[off + 2], bytes[off + 1], bytes[off],
            bytes[off + 3]);
      }
    }
  }
  // Unknown format → return empty JPEG (won't crash the caller)

  return img.encodeJpg(image, quality: quality);
}

// ─── Snapshot camera image bytes synchronously (fast - just copies refs) ────
Map<String, dynamic>? _snapshotParams(CameraImage image, int quality) {
  try {
    if (image.format.group == ImageFormatGroup.yuv420) {
      final p0 = image.planes[0];
      final p1 = image.planes[1];
      final p2 = image.planes[2];
      return {
        'fmt': 'yuv420',
        'w': image.width,
        'h': image.height,
        'q': quality,
        'y': Uint8List.fromList(p0.bytes),
        'u': Uint8List.fromList(p1.bytes),
        'v': Uint8List.fromList(p2.bytes),
        'yBpr': p0.bytesPerRow,
        'uvBpr': p1.bytesPerRow,
        'uvBpp': p1.bytesPerPixel ?? 1,
      };
    } else if (image.format.group == ImageFormatGroup.bgra8888) {
      final p0 = image.planes[0];
      return {
        'fmt': 'bgra8888',
        'w': image.width,
        'h': image.height,
        'q': quality,
        'bytes': Uint8List.fromList(p0.bytes),
        'bpr': p0.bytesPerRow,
      };
    } else {
      if (kDebugMode) {
        print('[CameraService] Unsupported format: ${image.format.group} '
            '(raw: ${image.format.raw})');
      }
      return null;
    }
  } catch (e) {
    if (kDebugMode) print('[CameraService] _snapshotParams error: $e');
    return null;
  }
}

// ─── Service ─────────────────────────────────────────────────────────────────
class CameraService {
  static final CameraService _instance = CameraService._internal();
  factory CameraService() => _instance;
  CameraService._internal();

  CameraController? _cameraController;
  StreamController<CameraFrameData>? _frameStreamController;

  bool _isCapturingFrame = false;
  bool _isStreamingFrames = false;
  int _frameId = 0;
  int _targetIntervalMs = 500; // 2 FPS default
  DateTime? _lastFrameAt;

  Stream<CameraFrameData>? get frameStream => _frameStreamController?.stream;

  Future<void> initialize() async {
    try {
      if (_cameraController != null && _cameraController!.value.isInitialized) {
        return;
      }

      final cameras = await availableCameras();
      if (cameras.isEmpty) throw Exception('No cameras found on this device');

      _cameraController = CameraController(
        cameras.first,
        ResolutionPreset.low,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.yuv420,
      );

      await _cameraController!.initialize();
      _frameStreamController ??= StreamController<CameraFrameData>.broadcast();

      if (kDebugMode) {
        print('[CameraService] Initialized: '
            '${_cameraController!.value.previewSize}');
      }
    } catch (e) {
      if (kDebugMode) print('[CameraService] Initialization error: $e');
      rethrow;
    }
  }

  Future<void> startCapturing({int fps = 3}) async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      throw Exception('CameraController not initialized');
    }

    _targetIntervalMs = (1000 / fps).round();
    _frameId = 0;
    _lastFrameAt = null;
    _isCapturingFrame = false;

    // Always cleanly stop any existing stream before starting a new one.
    // This avoids the race where unawaited(stopImageStream) hasn't finished
    // when startImageStream is re-called after Stop → Start.
    if (_cameraController!.value.isStreamingImages) {
      await _cameraController!.stopImageStream();
    }

    _isStreamingFrames = true;

    await _cameraController!.startImageStream((CameraImage rawImage) async {
      // Throttle check
      if (!_isStreamingFrames || _isCapturingFrame) return;

      final now = DateTime.now();
      if (_lastFrameAt != null &&
          now.difference(_lastFrameAt!).inMilliseconds < _targetIntervalMs) {
        return;
      }
      _lastFrameAt = now;
      _isCapturingFrame = true;

      try {
        // Snapshot raw bytes synchronously (fast) then hand off to an isolate.
        final params = _snapshotParams(rawImage, 75);
        if (params == null) return;

        // compute() runs _encodeFrameInIsolate in a background Dart isolate.
        // The main thread is NOT blocked during this call.
        final jpegBytes = await compute(_encodeFrameInIsolate, params);

        if (!_isStreamingFrames) return; // streaming was stopped while encoding

        final frameData = CameraFrameData(
          timestamp: DateTime.now().millisecondsSinceEpoch / 1000.0,
          jpegData: jpegBytes,
          frameId: _frameId++,
          resolution: '${rawImage.width}x${rawImage.height}',
        );

        if (_frameStreamController != null &&
            !_frameStreamController!.isClosed) {
          _frameStreamController!.add(frameData);
        }
      } catch (e) {
        if (kDebugMode) print('[CameraService] Encode error: $e');
      } finally {
        _isCapturingFrame = false;
      }
    });

    if (kDebugMode) print('[CameraService] Started at $fps FPS');
  }

  void stopCapturing() {
    _isStreamingFrames = false;
    _isCapturingFrame = false;
    _lastFrameAt = null;

    if (_cameraController?.value.isStreamingImages ?? false) {
      unawaited(_cameraController!.stopImageStream());
    }

    if (kDebugMode) print('[CameraService] Stopped');
  }

  bool get isInitialized =>
      _cameraController != null && _cameraController!.value.isInitialized;

  CameraController? get controller => _cameraController;

  Future<void> dispose() async {
    _isStreamingFrames = false;
    _isCapturingFrame = false;
    _lastFrameAt = null;

    if (_cameraController?.value.isStreamingImages ?? false) {
      await _cameraController!.stopImageStream();
    }
    await _cameraController?.dispose();
    _cameraController = null;
    await _frameStreamController?.close();
    _frameStreamController = null;

    if (kDebugMode) print('[CameraService] Disposed');
  }
}
