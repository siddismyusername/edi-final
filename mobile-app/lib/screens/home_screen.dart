import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/imu_data.dart';
import '../models/sensor_data.dart';
import '../models/camera_frame_data.dart';
import '../services/api_service.dart';
import '../services/camera_service.dart';
import '../services/sensor_service.dart';

/// Main home screen of the ETA-Sync application
/// Provides UI for streaming mode selection, server configuration, and data capture control
class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _serverUrlController = TextEditingController();
  final _sensorService = SensorService();
  final _cameraService = CameraService();
  final _apiService = ApiService();

  bool _isStreaming = false;
  String _streamingMode = 'sync'; // 'sync' or 'async'
  String _statusMessage = 'Not connected';
  bool _isConnected = false;
  int _imuCount = 0;
  int _frameCount = 0;

  StreamSubscription<bool>? _connectionStatusSubscription;
  StreamSubscription<SensorData>? _sensorSubscription;
  StreamSubscription<CameraFrameData>? _frameSubscription;

  Timer? _asyncDelayTimer;
  SensorData? _pendingSensorData;

  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  /// Initializes all services
  Future<void> _initializeServices() async {
    try {
      // Initialize sensor service
      _sensorService.initialize();

      // Initialize camera service
      await _cameraService.initialize();

      // Subscribe to connection status changes
      _connectionStatusSubscription =
          _apiService.connectionStatusStream.listen((connected) {
        setState(() {
          _isConnected = connected;
          _statusMessage = connected ? 'Connected' : 'Disconnected';
        });
      });

      setState(() {
        _statusMessage = 'Initialized';
      });
    } catch (e) {
      setState(() {
        _statusMessage = 'Initialization error: $e';
      });
    }
  }

  /// Requests necessary permissions from the user
  Future<bool> _requestPermissions() async {
    final cameraStatus = await Permission.camera.request();
    final microphoneStatus = await Permission.microphone.request();
    final sensorsStatus = await Permission.sensors.request();

    return cameraStatus.isGranted &&
        microphoneStatus.isGranted &&
        sensorsStatus.isGranted;
  }

  /// Connects to the server using the provided URL
  Future<void> _connectToServer() async {
    String url = _serverUrlController.text.trim();

    if (url.isEmpty) {
      _showErrorDialog('Please enter a server URL');
      return;
    }

    if (!url.startsWith('http')) {
      url = 'http://$url';
    }

    setState(() {
      _statusMessage = 'Connecting...';
    });

    final connected = await _apiService.setServerUrl(url);

    if (connected) {
      setState(() {
        _statusMessage = 'Connected';
        _isConnected = true;
      });
      _showSuccessSnackbar('Connected to server');
    } else {
      setState(() {
        _statusMessage = 'Connection failed';
        _isConnected = false;
      });
      _showErrorDialog('Failed to connect to server.\nMake sure the server is running at: $url');
    }
  }

  /// Starts streaming sensor and camera data
  Future<void> _startStreaming() async {
    // Check permissions
    final hasPermissions = await _requestPermissions();
    if (!hasPermissions) {
      _showErrorDialog('Camera and sensor permissions are required');
      return;
    }

    if (!_isConnected) {
      _showErrorDialog('Please connect to a server first');
      return;
    }

    try {
      setState(() {
        _isStreaming = true;
        _imuCount = 0;
        _frameCount = 0;
        _statusMessage = 'Streaming ($streamingMode mode)...';
      });

      // Start camera capturing
      _cameraService.startCapturing(fps: 10);

      // Subscribe to sensor data
      _sensorSubscription = _sensorService.sensorStream.listen(
        (sensorData) => _handleSensorData(sensorData),
        onError: (error) {
          print('Sensor error: $error');
          _stopStreaming();
        },
      );

      // Subscribe to camera frames
      _frameSubscription = _cameraService.frameStream?.listen(
        (frameData) => _handleCameraFrame(frameData),
        onError: (error) {
          print('Camera error: $error');
          _stopStreaming();
        },
      );
    } catch (e) {
      _showErrorDialog('Error starting stream: $e');
      setState(() {
        _isStreaming = false;
      });
    }
  }

  /// Stops streaming sensor and camera data
  void _stopStreaming() {
    _sensorSubscription?.cancel();
    _frameSubscription?.cancel();
    _cameraService.stopCapturing();
    _asyncDelayTimer?.cancel();

    setState(() {
      _isStreaming = false;
      _statusMessage = 'Stopped';
    });
  }

  /// Handles incoming sensor data
  void _handleSensorData(SensorData sensorData) async {
    if (_streamingMode == 'sync') {
      // Send immediately in synchronous mode
      final imuData = ImuData(
        timestamp: sensorData.timestamp,
        ax: sensorData.ax,
        ay: sensorData.ay,
        az: sensorData.az,
        gx: sensorData.gx,
        gy: sensorData.gy,
        gz: sensorData.gz,
        mode: 'sync',
      );

      await _apiService.sendImuData(imuData.toJson());

      setState(() {
        _imuCount++;
        _statusMessage =
            'Streaming (sync) - IMU: $_imuCount, Frames: $_frameCount';
      });
    } else {
      // In asynchronous mode, intentionally delay one stream
      // We'll delay sensor data by 200ms
      _pendingSensorData = sensorData;

      _asyncDelayTimer?.cancel();
      _asyncDelayTimer = Timer(const Duration(milliseconds: 200), () {
        if (_pendingSensorData != null && _isStreaming) {
          final imuData = ImuData(
            timestamp: _pendingSensorData!.timestamp,
            ax: _pendingSensorData!.ax,
            ay: _pendingSensorData!.ay,
            az: _pendingSensorData!.az,
            gx: _pendingSensorData!.gx,
            gy: _pendingSensorData!.gy,
            gz: _pendingSensorData!.gz,
            mode: 'async',
          );

          _apiService.sendImuData(imuData.toJson());

          setState(() {
            _imuCount++;
            _statusMessage =
                'Streaming (async) - IMU: $_imuCount, Frames: $_frameCount';
          });
        }
      });
    }
  }

  /// Handles incoming camera frames
  void _handleCameraFrame(CameraFrameData frameData) async {
    // Convert frame data to base64 for transmission
    final base64Frame = base64Encode(frameData.jpegData);

    final frameJson = {
      'timestamp': frameData.timestamp,
      'frame_id': frameData.frameId,
      'resolution': frameData.resolution,
      'data': base64Frame,
      'mode': _streamingMode,
    };

    await _apiService.sendCameraFrame(frameJson);

    setState(() {
      _frameCount++;
      _statusMessage =
          'Streaming ($_streamingMode) - IMU: $_imuCount, Frames: $_frameCount';
    });
  }

  /// Shows an error dialog
  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Error'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  /// Shows a success snackbar
  void _showSuccessSnackbar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  void dispose() {
    _stopStreaming();
    _connectionStatusSubscription?.cancel();
    _asyncDelayTimer?.cancel();
    _serverUrlController.dispose();
    _sensorService.dispose();
    _cameraService.dispose();
    _apiService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ETA-Sync Mobile'),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.blue.shade700,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Card
            Card(
              elevation: 2,
              color: _isConnected ? Colors.green.shade50 : Colors.red.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _isConnected ? Colors.green : Colors.red,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _statusMessage,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: _isConnected ? Colors.green.shade800 : Colors.red.shade800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Server URL Input
            Text(
              'Server Configuration',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _serverUrlController,
              decoration: InputDecoration(
                hintText: 'e.g., 192.168.1.10:8000',
                labelText: 'Server Address',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                prefixIcon: const Icon(Icons.language),
                suffixIcon: _isConnected
                    ? const Icon(Icons.check_circle, color: Colors.green)
                    : null,
              ),
              enabled: !_isStreaming,
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _isStreaming ? null : _connectToServer,
              icon: const Icon(Icons.cloud_queue),
              label: const Text('Connect to Server'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 12),
                backgroundColor: Colors.blue.shade600,
                disabledBackgroundColor: Colors.grey,
              ),
            ),
            const SizedBox(height: 30),

            // Streaming Mode Selection
            Text(
              'Streaming Mode',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            Card(
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  children: [
                    RadioListTile<String>(
                      title: const Text('Synchronous Mode'),
                      subtitle: const Text('Fixed-interval data collection'),
                      value: 'sync',
                      groupValue: _streamingMode,
                      onChanged: _isStreaming
                          ? null
                          : (value) {
                              setState(() {
                                _streamingMode = value!;
                              });
                            },
                    ),
                    RadioListTile<String>(
                      title: const Text('Asynchronous Mode'),
                      subtitle: const Text('Event-driven with 200ms offset'),
                      value: 'async',
                      groupValue: _streamingMode,
                      onChanged: _isStreaming
                          ? null
                          : (value) {
                              setState(() {
                                _streamingMode = value!;
                              });
                            },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 30),

            // Control Buttons
            Text(
              'Data Collection',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: !_isConnected || _isStreaming
                        ? null
                        : _startStreaming,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Streaming'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      backgroundColor: Colors.green.shade600,
                      disabledBackgroundColor: Colors.grey,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: !_isStreaming ? null : _stopStreaming,
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop Streaming'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      backgroundColor: Colors.red.shade600,
                      disabledBackgroundColor: Colors.grey,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 30),

            // Statistics Card
            Card(
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Session Statistics',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          children: [
                            Text(
                              _imuCount.toString(),
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                color: Colors.blue,
                              ),
                            ),
                            const Text('IMU Samples'),
                          ],
                        ),
                        Column(
                          children: [
                            Text(
                              _frameCount.toString(),
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                color: Colors.purple,
                              ),
                            ),
                            const Text('Frames'),
                          ],
                        ),
                        Column(
                          children: [
                            Text(
                              _streamingMode.toUpperCase(),
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: Colors.orange,
                              ),
                            ),
                            const Text('Mode'),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Info Card
            Card(
              color: Colors.grey.shade100,
              elevation: 0,
              child: const Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'How to Use',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      '1. Enter the FastAPI server IP address and port\n'
                      '2. Click "Connect to Server" to establish connection\n'
                      '3. Select your preferred streaming mode\n'
                      '4. Click "Start Streaming" to begin data capture\n'
                      '5. Move your device and rotate it to collect diverse sensor data\n'
                      '6. Click "Stop Streaming" when done',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.black87,
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Helper to get streaming mode display name
  String get streamingMode => _streamingMode == 'sync' ? 'Synchronous' : 'Asynchronous';
}
