import 'dart:async';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import '../models/camera_frame_data.dart';

/// Service responsible for camera frame capture and processing.
class CameraService {
  // Singleton instance
  static final CameraService _instance = CameraService._internal();

  factory CameraService() {
    return _instance;
  }

  CameraService._internal();

  CameraController? _cameraController;
  StreamController<CameraFrameData>? _frameStreamController;
  Timer? _captureTimer;

  /// Gets the stream of camera frames
  Stream<CameraFrameData>? get frameStream => _frameStreamController?.stream;

  /// Initializes the camera service
  /// Gets available cameras and sets up the default camera
  Future<void> initialize() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw Exception('No cameras found on this device');
      }

      // Use the rear camera by default (index 0 is typically rear)
      final selectedCamera = cameras.first;

      _cameraController = CameraController(
        selectedCamera,
        ResolutionPreset.medium,
        enableAudio: false,
      );

      await _cameraController!.initialize();

      _frameStreamController =
          StreamController<CameraFrameData>.broadcast();

      if (kDebugMode) {
        print('[CameraService] Initialized with resolution: ${_cameraController!.value.previewSize}');
      }
    } catch (e) {
      if (kDebugMode) {
        print('[CameraService] Initialization error: $e');
      }
      rethrow;
    }
  }

  /// Starts capturing camera frames at the specified frame rate (FPS)
  /// [fps]: Frames per second (e.g., 10 for 10 FPS)
  void startCapturing({int fps = 10}) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      throw Exception('CameraController not initialized');
    }

    int frameId = 0;
    final intervalMs = (1000 / fps).toInt();

    // Stop any existing timer
    _captureTimer?.cancel();

    _captureTimer = Timer.periodic(Duration(milliseconds: intervalMs), (_) {
      _captureFrame(frameId);
      frameId++;
    });

    if (kDebugMode) {
      print('[CameraService] Started capturing at $fps FPS');
    }
  }

  /// Captures a single frame and processes it
  Future<void> _captureFrame(int frameId) async {
    try {
      if (_cameraController == null || !_cameraController!.value.isInitialized) {
        return;
      }

      final xFile = await _cameraController!.takePicture();
      final imageBytes = await xFile.readAsBytes();

      // Compress to JPEG if needed
      final jpegData = await _compressToJpeg(imageBytes);

      final frameData = CameraFrameData(
        timestamp: DateTime.now().millisecondsSinceEpoch / 1000.0,
        jpegData: jpegData,
        frameId: frameId,
        resolution:
            '${_cameraController!.value.previewSize?.width.toInt() ?? 0}x${_cameraController!.value.previewSize?.height.toInt() ?? 0}',
      );

      if (_frameStreamController != null && !_frameStreamController!.isClosed) {
        _frameStreamController!.add(frameData);
      }
    } catch (e) {
      if (kDebugMode) {
        print('[CameraService] Frame capture error: $e');
      }
    }
  }

  /// Compresses image data to JPEG format
  Future<List<int>> _compressToJpeg(List<int> imageBytes) async {
    try {
      // Convert List<int> to Uint8List for image processing
      final image = img.decodeImage(Uint8List.fromList(imageBytes));
      if (image == null) {
        return imageBytes;
      }

      // Encode to JPEG with quality 80
      final jpegData = img.encodeJpg(image, quality: 80);
      return jpegData;
    } catch (e) {
      if (kDebugMode) {
        print('[CameraService] JPEG compression error: $e');
      }
      return imageBytes;
    }
  }

  /// Stops capturing camera frames
  void stopCapturing() {
    _captureTimer?.cancel();
    _captureTimer = null;
    if (kDebugMode) {
      print('[CameraService] Stopped capturing');
    }
  }

  /// Checks if camera controller is initialized
  bool get isInitialized =>
      _cameraController != null && _cameraController!.value.isInitialized;

  /// Gets the camera controller
  CameraController? get controller => _cameraController;

  /// Disposes the camera service and releases resources
  Future<void> dispose() async {
    _captureTimer?.cancel();
    await _cameraController?.dispose();
    await _frameStreamController?.close();
    if (kDebugMode) {
      print('[CameraService] Disposed');
    }
  }
}
