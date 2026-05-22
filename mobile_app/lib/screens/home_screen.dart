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
  String _statusMessage = 'Not connected';
  bool _isConnected = false;
  int _imuCount = 0;
  int _frameCount = 0;

  StreamSubscription<bool>? _connectionStatusSubscription;
  StreamSubscription<SensorData>? _sensorSubscription;
  StreamSubscription<CameraFrameData>? _frameSubscription;

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
      final cameraStatus = await Permission.camera.request();
      if (!cameraStatus.isGranted) {
        setState(() {
          _statusMessage = 'Camera permission is required';
        });
        return;
      }

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

  /// Requests camera permission if not already granted
  Future<bool> _requestPermissions() async {
    var status = await Permission.camera.status;
    if (status.isGranted) return true;
    status = await Permission.camera.request();
    if (status.isPermanentlyDenied) {
      _showErrorDialog(
        'Camera permission is permanently denied.\n'
        'Please enable it in your device Settings ➜ Apps ➜ ETA-Sync ➜ Permissions.',
      );
      return false;
    }
    return status.isGranted;
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
      _showErrorDialog(
          'Failed to connect to server.\nMake sure the server is running at: $url');
    }
  }

  /// Starts streaming sensor and camera data
  Future<void> _startStreaming() async {
    // Check permissions
    final hasPermissions = await _requestPermissions();
    if (!hasPermissions) {
      _showErrorDialog('Camera permission is required to start streaming.');
      return;
    }

    if (!_isConnected) {
      _showErrorDialog('Please connect to a server first');
      return;
    }

    try {
      if (!_cameraService.isInitialized) {
        await _cameraService.initialize();
      }

      await _sensorSubscription?.cancel();
      await _frameSubscription?.cancel();

      setState(() {
        _isStreaming = true;
        _imuCount = 0;
        _frameCount = 0;
        _statusMessage = 'Streaming...';
      });

      // Subscribe before starting the frame stream so early frames are not lost.
      _sensorSubscription = _sensorService.sensorStream.listen(
        (sensorData) => _handleSensorData(sensorData),
        onError: (error) {
          print('Sensor error: $error');
          _stopStreaming();
        },
      );

      _frameSubscription = _cameraService.frameStream?.listen(
        (frameData) => _handleCameraFrame(frameData),
        onError: (error) {
          print('Camera error: $error');
          _stopStreaming();
        },
      );

      await _cameraService.startCapturing(fps: 5);
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

    setState(() {
      _isStreaming = false;
      _statusMessage = 'Stopped';
    });
  }

  /// Handles incoming sensor data
  void _handleSensorData(SensorData sensorData) async {
    if (!_isStreaming) {
      return;
    }

    final imuData = ImuData(
      timestamp: sensorData.timestamp,
      ax: sensorData.ax,
      ay: sensorData.ay,
      az: sensorData.az,
      gx: sensorData.gx,
      gy: sensorData.gy,
      gz: sensorData.gz,
    );

    await _apiService.sendImuData(imuData.toJson());

    setState(() {
      _imuCount++;
      _statusMessage = 'Streaming - IMU: $_imuCount, Frames: $_frameCount';
    });
  }

  /// Handles incoming camera frames
  void _handleCameraFrame(CameraFrameData frameData) async {
    if (!_isStreaming) {
      return;
    }

    // Convert frame data to base64 for transmission
    final base64Frame = base64Encode(frameData.jpegData);

    final frameJson = {
      'timestamp': frameData.timestamp,
      'frame_id': frameData.frameId,
      'resolution': frameData.resolution,
      'data': base64Frame,
    };

    await _apiService.sendCameraFrame(frameJson);

    setState(() {
      _frameCount++;
      _statusMessage = 'Streaming - IMU: $_imuCount, Frames: $_frameCount';
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
    _serverUrlController.dispose();
    _sensorService.dispose();
    _cameraService.dispose();
    _apiService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('ETA-Sync Mobile'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHeroStatusCard(theme, colorScheme),
            const SizedBox(height: 16),
            _buildSectionCard(
              title: 'Server Configuration',
              icon: Icons.cloud_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _serverUrlController,
                    decoration: InputDecoration(
                      hintText: '192.168.1.10:8000',
                      labelText: 'Server Address',
                      prefixIcon: const Icon(Icons.language),
                      suffixIcon: _isConnected
                          ? Icon(
                              Icons.verified_rounded,
                              color: colorScheme.primary,
                            )
                          : null,
                    ),
                    enabled: !_isStreaming,
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _isStreaming ? null : _connectToServer,
                    icon: const Icon(Icons.wifi_find),
                    label: const Text('Connect to Server'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _buildSectionCard(
              title: 'Data Collection',
              icon: Icons.sensors_rounded,
              child: Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: !_isConnected || _isStreaming
                          ? null
                          : _startStreaming,
                      icon: const Icon(Icons.play_arrow_rounded),
                      label: const Text('Start'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: !_isStreaming ? null : _stopStreaming,
                      icon: const Icon(Icons.stop_rounded),
                      label: const Text('Stop'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _buildSectionCard(
              title: 'Session Statistics',
              icon: Icons.insights_rounded,
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: _buildStatTile(
                          theme,
                          icon: Icons.sensors_rounded,
                          label: 'IMU Samples',
                          value: _imuCount.toString(),
                          tint: colorScheme.primary,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildStatTile(
                          theme,
                          icon: Icons.photo_camera_front_rounded,
                          label: 'Frames',
                          value: _frameCount.toString(),
                          tint: colorScheme.secondary,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _buildSectionCard(
              title: 'How to Use',
              icon: Icons.info_outline_rounded,
              child: Text(
                '1. Enter the FastAPI server IP address and port.\n'
                '2. Tap Connect to verify connectivity.\n'
                '3. Tap Start to stream sensor and camera data.\n'
                '4. Move and rotate device for diverse samples.\n'
                '5. Tap Stop to end the session.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  height: 1.55,
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeroStatusCard(ThemeData theme, ColorScheme colorScheme) {
    final statusColor = _isConnected ? colorScheme.primary : colorScheme.error;
    final statusTone = _isConnected
        ? colorScheme.primaryContainer
        : colorScheme.errorContainer;

    return Card(
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          gradient: LinearGradient(
            colors: [
              statusTone,
              colorScheme.surface,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: statusColor.withOpacity(0.18),
                  foregroundColor: statusColor,
                  child:
                      Icon(_isConnected ? Icons.cloud_done : Icons.cloud_off),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _isConnected
                            ? 'Server Connected'
                            : 'No Active Connection',
                        style: theme.textTheme.titleMedium,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _statusMessage,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Chip(
                  avatar: Icon(
                    _isStreaming ? Icons.podcasts_rounded : Icons.pause_circle,
                    size: 18,
                    color: statusColor,
                  ),
                  label: Text(_isStreaming ? 'Streaming' : 'Idle'),
                ),
                Chip(
                  avatar: const Icon(Icons.memory_rounded, size: 18),
                  label: Text('IMU $_imuCount'),
                ),
                Chip(
                  avatar: const Icon(Icons.image_rounded, size: 18),
                  label: Text('Frames $_frameCount'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required IconData icon,
    required Widget child,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }

  Widget _buildStatTile(
    ThemeData theme, {
    required IconData icon,
    required String label,
    required String value,
    required Color tint,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: tint.withOpacity(0.08),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 15,
            backgroundColor: tint.withOpacity(0.2),
            foregroundColor: tint,
            child: Icon(icon, size: 16),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: tint,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  label,
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
