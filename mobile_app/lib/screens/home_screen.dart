import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../models/camera_frame_data.dart';
import '../models/imu_data.dart';
import '../models/sensor_data.dart';
import '../services/api_service.dart';
import '../services/camera_service.dart';
import '../services/sensor_service.dart';

enum HomeMode {
  stream,
  sync,
}

/// Main home screen of the ETA-Sync application.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const List<String> _backendRequirements = [
    'Maintain a per-session rolling synchronized cache for the latest 120 seconds.',
    'Expose GET /sync/status?session_id=... with readiness and available replay seconds.',
    'Expose GET /sync/latest?session_id=...&offset_seconds=0..120 for fused playback.',
    'Return session_id, server_timestamp, window_start, window_end, prediction, confidence_score, all_probabilities, imu_summary or sampled aligned IMU packets, optional frame preview, dtw_distance, and alignment_path.',
    'Keep /imu, /frame, /ws/diagnostics, and existing dashboard events unchanged.',
    'Reuse the existing session, WindowBuffer, fusion output, and artifact model instead of creating a parallel pipeline.',
  ];

  final _serverUrlController = TextEditingController();
  final _sensorService = SensorService();
  final _cameraService = CameraService();
  final _apiService = ApiService();

  HomeMode _mode = HomeMode.stream;
  bool _isStreaming = false;
  bool _isConnected = false;
  bool _streamCamera = true;
  bool _streamImu = true;
  bool _syncApiChecked = false;
  bool _syncApiAvailable = false;
  String _statusMessage = 'Not connected';
  int _imuCount = 0;
  int _frameCount = 0;

  StreamSubscription<bool>? _connectionStatusSubscription;
  StreamSubscription<SensorData>? _sensorSubscription;
  StreamSubscription<CameraFrameData>? _frameSubscription;

  bool get _hasSelectedStream => _streamCamera || _streamImu;

  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  Future<void> _initializeServices() async {
    try {
      _sensorService.initialize();

      _connectionStatusSubscription =
          _apiService.connectionStatusStream.listen((connected) {
        if (!mounted) return;
        setState(() {
          _isConnected = connected;
          _statusMessage = connected ? 'Connected' : 'Disconnected';
          if (!connected) {
            _syncApiChecked = false;
            _syncApiAvailable = false;
          }
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

  Future<bool> _requestCameraPermission() async {
    var status = await Permission.camera.status;
    if (status.isGranted) return true;

    status = await Permission.camera.request();
    if (status.isPermanentlyDenied) {
      _showErrorDialog(
        'Camera permission is permanently denied.\n'
        'Please enable it in your device Settings > Apps > ETA-Sync > Permissions.',
      );
      return false;
    }
    return status.isGranted;
  }

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
      _syncApiChecked = false;
      _syncApiAvailable = false;
    });

    final connected = await _apiService.setServerUrl(url);

    if (!mounted) return;
    if (connected) {
      setState(() {
        _statusMessage = 'Connected';
        _isConnected = true;
      });
      _showSuccessSnackbar('Connected to server');
      await _checkSyncApiAvailability();
    } else {
      setState(() {
        _statusMessage = 'Connection failed';
        _isConnected = false;
      });
      _showErrorDialog(
        'Failed to connect to server.\nMake sure the server is running at: $url',
      );
    }
  }

  Future<void> _checkSyncApiAvailability() async {
    if (!_isConnected) return;
    final available = await _apiService.isSyncPlaybackAvailable();
    if (!mounted) return;
    setState(() {
      _syncApiChecked = true;
      _syncApiAvailable = available;
    });
  }

  Future<void> _startStreaming() async {
    if (!_hasSelectedStream) {
      _showErrorDialog('Select Camera, IMU, or both before starting.');
      return;
    }

    if (!_isConnected) {
      _showErrorDialog('Please connect to a server first');
      return;
    }

    try {
      if (_streamCamera) {
        final hasPermission = await _requestCameraPermission();
        if (!hasPermission) {
          _showErrorDialog(
              'Camera permission is required for camera streaming.');
          return;
        }

        if (!_cameraService.isInitialized) {
          await _cameraService.initialize();
        }
      }

      await _sensorSubscription?.cancel();
      await _frameSubscription?.cancel();
      _sensorSubscription = null;
      _frameSubscription = null;

      setState(() {
        _isStreaming = true;
        _imuCount = 0;
        _frameCount = 0;
        _statusMessage = _streamLabel();
      });

      if (_streamImu) {
        _sensorSubscription = _sensorService.sensorStream.listen(
          (sensorData) => _handleSensorData(sensorData),
          onError: (error) {
            debugPrint('Sensor error: $error');
            _stopStreaming();
          },
        );
      }

      if (_streamCamera) {
        _frameSubscription = _cameraService.frameStream?.listen(
          (frameData) => _handleCameraFrame(frameData),
          onError: (error) {
            debugPrint('Camera error: $error');
            _stopStreaming();
          },
        );
        await _cameraService.startCapturing(fps: 5);
      }
    } catch (e) {
      _showErrorDialog('Error starting stream: $e');
      if (!mounted) return;
      setState(() {
        _isStreaming = false;
      });
    }
  }

  void _stopStreaming() {
    _sensorSubscription?.cancel();
    _frameSubscription?.cancel();
    _sensorSubscription = null;
    _frameSubscription = null;
    _cameraService.stopCapturing();

    if (!mounted) return;
    setState(() {
      _isStreaming = false;
      _statusMessage = 'Stopped';
    });
  }

  Future<void> _handleSensorData(SensorData sensorData) async {
    if (!_isStreaming || !_streamImu) {
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

    if (!mounted || !_isStreaming) return;
    setState(() {
      _imuCount++;
      _statusMessage = _streamLabel();
    });
  }

  Future<void> _handleCameraFrame(CameraFrameData frameData) async {
    if (!_isStreaming || !_streamCamera) {
      return;
    }

    final frameJson = {
      'timestamp': frameData.timestamp,
      'frame_id': frameData.frameId,
      'resolution': frameData.resolution,
      'data': base64Encode(frameData.jpegData),
    };

    await _apiService.sendCameraFrame(frameJson);

    if (!mounted || !_isStreaming) return;
    setState(() {
      _frameCount++;
      _statusMessage = _streamLabel();
    });
  }

  String _streamLabel() {
    final parts = <String>[];
    if (_streamImu) parts.add('IMU: $_imuCount');
    if (_streamCamera) parts.add('Frames: $_frameCount');
    return 'Streaming - ${parts.join(', ')}';
  }

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
            _buildModeSelector(colorScheme),
            const SizedBox(height: 16),
            _buildServerConfiguration(colorScheme),
            const SizedBox(height: 16),
            if (_mode == HomeMode.stream) ...[
              _buildStreamControls(theme, colorScheme),
              const SizedBox(height: 16),
              _buildSessionStatistics(theme, colorScheme),
            ] else ...[
              _buildSyncPlayback(theme, colorScheme),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildModeSelector(ColorScheme colorScheme) {
    return SegmentedButton<HomeMode>(
      segments: const [
        ButtonSegment<HomeMode>(
          value: HomeMode.stream,
          icon: Icon(Icons.sensors_rounded),
          label: Text('Stream Sensor Data'),
        ),
        ButtonSegment<HomeMode>(
          value: HomeMode.sync,
          icon: Icon(Icons.video_library_rounded),
          label: Text('Get Sync Stream'),
        ),
      ],
      selected: {_mode},
      onSelectionChanged: _isStreaming
          ? null
          : (selection) {
              setState(() {
                _mode = selection.first;
              });
              if (selection.first == HomeMode.sync && _isConnected) {
                _checkSyncApiAvailability();
              }
            },
    );
  }

  Widget _buildServerConfiguration(ColorScheme colorScheme) {
    return _buildSectionCard(
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
    );
  }

  Widget _buildStreamControls(ThemeData theme, ColorScheme colorScheme) {
    return _buildSectionCard(
      title: 'Stream Sensor Data',
      icon: Icons.podcasts_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CheckboxListTile(
            value: _streamCamera,
            onChanged: _isStreaming
                ? null
                : (value) {
                    setState(() {
                      _streamCamera = value ?? false;
                    });
                  },
            secondary: const Icon(Icons.photo_camera_front_rounded),
            title: const Text('Camera'),
            subtitle: const Text('Send JPEG frames to /frame'),
            contentPadding: EdgeInsets.zero,
          ),
          CheckboxListTile(
            value: _streamImu,
            onChanged: _isStreaming
                ? null
                : (value) {
                    setState(() {
                      _streamImu = value ?? false;
                    });
                  },
            secondary: const Icon(Icons.sensors_rounded),
            title: const Text('IMU'),
            subtitle:
                const Text('Send accelerometer and gyroscope samples to /imu'),
            contentPadding: EdgeInsets.zero,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed:
                      !_isConnected || _isStreaming || !_hasSelectedStream
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
          if (!_hasSelectedStream) ...[
            const SizedBox(height: 10),
            Text(
              'Select at least one stream source.',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.error,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSessionStatistics(ThemeData theme, ColorScheme colorScheme) {
    final inactive = colorScheme.onSurfaceVariant;
    return _buildSectionCard(
      title: 'Session Statistics',
      icon: Icons.insights_rounded,
      child: Row(
        children: [
          Expanded(
            child: _buildStatTile(
              theme,
              icon: Icons.sensors_rounded,
              label: 'IMU Samples',
              value: _streamImu ? _imuCount.toString() : 'Off',
              tint: _streamImu ? colorScheme.primary : inactive,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _buildStatTile(
              theme,
              icon: Icons.photo_camera_front_rounded,
              label: 'Frames',
              value: _streamCamera ? _frameCount.toString() : 'Off',
              tint: _streamCamera ? colorScheme.secondary : inactive,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSyncPlayback(ThemeData theme, ColorScheme colorScheme) {
    final unavailable = !_syncApiAvailable;

    return _buildSectionCard(
      title: 'Get Sync Stream',
      icon: Icons.video_library_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color:
                  colorScheme.surfaceContainerHighest.withValues(alpha: 0.55),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      unavailable
                          ? Icons.hourglass_disabled_rounded
                          : Icons.play_circle_rounded,
                      color:
                          unavailable ? colorScheme.error : colorScheme.primary,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        unavailable
                            ? 'Backend sync playback API not available'
                            : 'Sync playback ready',
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  unavailable
                      ? 'This screen is ready for a fused, synchronized two-minute playback stream once the backend exposes the required read-only sync endpoints.'
                      : 'Use the timeline to inspect synchronized fused windows from the latest two minutes.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildDisabledTimeline(theme, colorScheme),
          const SizedBox(height: 16),
          FilledButton.tonalIcon(
            onPressed: _isConnected ? _checkSyncApiAvailability : null,
            icon: const Icon(Icons.refresh_rounded),
            label:
                Text(_syncApiChecked ? 'Recheck Sync API' : 'Check Sync API'),
          ),
          const SizedBox(height: 16),
          Text(
            'Backend requirements',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          ..._backendRequirements.map(
            (requirement) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 7),
                    child: Icon(
                      Icons.circle,
                      size: 6,
                      color: colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      requirement,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                        height: 1.35,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDisabledTimeline(ThemeData theme, ColorScheme colorScheme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            IconButton.filledTonal(
              onPressed: null,
              icon: const Icon(Icons.replay_10_rounded),
              tooltip: 'Move back 10 seconds',
            ),
            Expanded(
              child: Slider(
                value: 120,
                min: 0,
                max: 120,
                onChanged: null,
              ),
            ),
            IconButton.filledTonal(
              onPressed: null,
              icon: const Icon(Icons.play_arrow_rounded),
              tooltip: 'Play synchronized stream',
            ),
          ],
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '-2:00',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            Text(
              'Live',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ],
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
                  backgroundColor: statusColor.withValues(alpha: 0.18),
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
                  label: Text(_streamImu ? 'IMU $_imuCount' : 'IMU Off'),
                ),
                Chip(
                  avatar: const Icon(Icons.image_rounded, size: 18),
                  label: Text(
                      _streamCamera ? 'Frames $_frameCount' : 'Camera Off'),
                ),
                Chip(
                  avatar: const Icon(Icons.sync_rounded, size: 18),
                  label:
                      Text(_syncApiAvailable ? 'Sync Ready' : 'Sync Pending'),
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
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
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
        color: tint.withValues(alpha: 0.08),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 15,
            backgroundColor: tint.withValues(alpha: 0.2),
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
