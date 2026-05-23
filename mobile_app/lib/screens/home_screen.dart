import 'dart:async';
import 'dart:convert';

import 'package:camera/camera.dart';
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
  final _serverUrlController = TextEditingController();
  final _sensorService = SensorService();
  final _cameraService = CameraService();
  final _apiService = ApiService();

  HomeMode _mode = HomeMode.stream;
  bool _isStreaming = false;
  bool _isConnected = false;
  bool _streamCamera = true;
  bool _streamImu = true;
  bool _syncApiAvailable = false;
  String _syncStatusMessage =
      'Start streaming to create a session for sync playback.';
  String _currentSessionId = '';
  double _replayOffsetSeconds = 0.0;
  double _availableReplaySeconds = 0.0;
  double _maxReplaySeconds = 120.0;
  Map<String, dynamic>? _latestSyncReplay;
  String? _latestSyncError;
  Timer? _syncRefreshTimer;
  bool _isReplayLoading = false;
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
            _syncApiAvailable = false;
            _stopSyncAutoRefresh();
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
      _syncApiAvailable = false;
    });

    final connected = await _apiService.setServerUrl(url);

    if (!mounted) return;
    if (connected) {
      setState(() {
        _statusMessage = 'Connected';
        _isConnected = true;
        _currentSessionId = '';
        _syncStatusMessage =
            'Connected. Start streaming to create a session for sync playback.';
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
    final sessionId = _currentSessionId.isNotEmpty
        ? _currentSessionId
        : _apiService.currentSessionId;
    if (sessionId == null || sessionId.isEmpty) {
      if (!mounted) return;
      setState(() {
        _syncApiAvailable = false;
        _syncStatusMessage = 'Start streaming first to create a live session.';
      });
      return;
    }

    final status =
        await _apiService.getSyncPlaybackStatus(sessionId: sessionId);
    if (!mounted) return;
    setState(() {
      _syncApiAvailable = status.ready;
      _availableReplaySeconds = status.availableSeconds;
      _maxReplaySeconds = status.maxReplaySeconds > 0
          ? status.maxReplaySeconds
          : _maxReplaySeconds;
      if (_replayOffsetSeconds > _maxReplaySeconds) {
        _replayOffsetSeconds = _maxReplaySeconds;
      }
      _syncStatusMessage = status.ready
          ? 'Sync playback ready for session ${sessionId.substring(0, sessionId.length > 8 ? 8 : sessionId.length)}.'
          : status.available
              ? 'Session is live, but replay windows are not ready yet.'
              : 'Backend sync playback is unavailable for this session.';
    });

    if (_mode == HomeMode.sync && status.ready) {
      await _loadLatestSyncReplay();
      _startSyncAutoRefresh();
    } else if (_mode != HomeMode.sync || !status.ready) {
      _stopSyncAutoRefresh();
    }
  }

  void _setReplayOffset(double seconds) {
    setState(() {
      _replayOffsetSeconds = seconds.clamp(0.0, _maxReplaySeconds);
    });
  }

  Future<void> _loadLatestSyncReplay({double? overrideOffsetSeconds}) async {
    if (_isReplayLoading) return;
    final sessionId = _currentSessionId.isNotEmpty
        ? _currentSessionId
        : _apiService.currentSessionId;
    if (sessionId == null || sessionId.isEmpty) {
      setState(() {
        _latestSyncReplay = null;
        _latestSyncError = 'Start streaming first to create a replay session.';
      });
      return;
    }

    setState(() {
      _isReplayLoading = true;
    });

    final replay = await _apiService.getLatestSyncReplay(
      sessionId: sessionId,
      offsetSeconds: overrideOffsetSeconds ?? _replayOffsetSeconds,
    );
    if (!mounted) return;

    setState(() {
      _latestSyncReplay = replay;
      _latestSyncError =
          replay == null ? 'No replay window is ready yet.' : null;
      _isReplayLoading = false;
    });
  }

  void _startSyncAutoRefresh() {
    _syncRefreshTimer?.cancel();
    _syncRefreshTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (!mounted) return;
      if (_mode != HomeMode.sync || !_syncApiAvailable) return;
      if (_replayOffsetSeconds > 0.1) return;
      _loadLatestSyncReplay();
    });
  }

  void _stopSyncAutoRefresh() {
    _syncRefreshTimer?.cancel();
    _syncRefreshTimer = null;
  }

  void _onSessionIdCaptured(String sessionId) {
    if (sessionId.isEmpty || sessionId == _currentSessionId) {
      return;
    }

    _currentSessionId = sessionId;
    if (_mode == HomeMode.sync) {
      _checkSyncApiAvailability();
    }
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

  void _stopStreaming({bool updateUi = true}) {
    _sensorSubscription?.cancel();
    _frameSubscription?.cancel();
    _sensorSubscription = null;
    _frameSubscription = null;
    _cameraService.stopCapturing();

    if (!updateUi || !mounted) return;
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

    final sent = await _apiService.sendImuData(imuData.toJson());
    if (!sent) return;

    final sessionId = _apiService.currentSessionId;
    if (sessionId != null) {
      _onSessionIdCaptured(sessionId);
    }

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
      'mode': 'sync',
    };

    final sent = await _apiService.sendCameraFrame(frameJson);
    if (!sent) return;

    final sessionId = _apiService.currentSessionId;
    if (sessionId != null) {
      _onSessionIdCaptured(sessionId);
    }

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
    _stopStreaming(updateUi: false);
    _connectionStatusSubscription?.cancel();
    _serverUrlController.dispose();
    _sensorService.dispose();
    _cameraService.dispose();
    _stopSyncAutoRefresh();
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
              } else {
                _stopSyncAutoRefresh();
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

  Widget _buildReplaySummary(
    ThemeData theme,
    ColorScheme colorScheme,
    Map<String, dynamic> replay,
  ) {
    final prediction = replay['prediction'];
    final confidence = replay['confidence'] ?? replay['confidence_score'];
    final windowStart = replay['window_start'];
    final windowEnd = replay['window_end'];
    final framePreview = replay['frame_preview'];
    final imuSummary = replay['imu_summary'];

    Widget? frameWidget;
    if (framePreview is String && framePreview.isNotEmpty) {
      try {
        final bytes = base64Decode(framePreview);
        frameWidget = ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: AspectRatio(
            aspectRatio: 16 / 9,
            child: Image.memory(bytes, fit: BoxFit.cover),
          ),
        );
      } catch (_) {
        frameWidget = Text(
          'Frame preview is unavailable.',
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        );
      }
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Latest replay window', style: theme.textTheme.titleSmall),
          const SizedBox(height: 8),
          Text('Prediction: ${prediction ?? 'Unknown'}'),
          Text('Confidence: ${_formatNumber(confidence)}'),
          Text('Window: ${windowStart ?? 'N/A'} -> ${windowEnd ?? 'N/A'}'),
          if (frameWidget != null) ...[
            const SizedBox(height: 12),
            frameWidget,
          ],
          if (imuSummary is Map<String, dynamic>) ...[
            const SizedBox(height: 12),
            _buildImuSummary(theme, colorScheme, imuSummary),
          ],
        ],
      ),
    );
  }

  Widget _buildImuSummary(
    ThemeData theme,
    ColorScheme colorScheme,
    Map<String, dynamic> imuSummary,
  ) {
    final count = imuSummary['count'];
    final start = imuSummary['start_timestamp'];
    final end = imuSummary['end_timestamp'];
    final axes = imuSummary['axes'];

    final rows = <Widget>[];
    if (axes is Map) {
      axes.forEach((key, value) {
        if (value is Map) {
          rows.add(
            Text(
              '$key avg ${_formatNumber(value['avg'])} '
              '(min ${_formatNumber(value['min'])}, max ${_formatNumber(value['max'])})',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          );
        }
      });
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colorScheme.surface.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('IMU summary', style: theme.textTheme.titleSmall),
          const SizedBox(height: 6),
          Text('Samples: ${count ?? 'N/A'}'),
          Text('Range: ${start ?? 'N/A'} -> ${end ?? 'N/A'}'),
          if (rows.isNotEmpty) ...[
            const SizedBox(height: 6),
            ...rows,
          ],
        ],
      ),
    );
  }

  String _formatNumber(dynamic value) {
    if (value is num) {
      return value.toStringAsFixed(2);
    }
    return 'N/A';
  }

  Widget _buildCameraPreview(ThemeData theme, ColorScheme colorScheme) {
    final controller = _cameraService.controller;
    if (controller == null || !controller.value.isInitialized) {
      return Container(
        height: 180,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          'Camera preview will appear here once streaming starts.',
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: AspectRatio(
        aspectRatio: controller.value.aspectRatio,
        child: CameraPreview(controller),
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
          if (_streamCamera) ...[
            const SizedBox(height: 16),
            _buildCameraPreview(theme, colorScheme),
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
    final hasSession = _currentSessionId.isNotEmpty ||
        (_apiService.currentSessionId ?? '').isNotEmpty;

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
                      !hasSession
                          ? Icons.hourglass_disabled_rounded
                          : unavailable
                              ? Icons.hourglass_disabled_rounded
                              : Icons.play_circle_rounded,
                      color: !hasSession
                          ? colorScheme.error
                          : unavailable
                              ? colorScheme.error
                              : colorScheme.primary,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        !hasSession
                            ? 'Start streaming to create a replay session'
                            : unavailable
                                ? 'Session active, waiting for replay windows'
                                : 'Sync playback ready',
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  hasSession
                      ? _syncStatusMessage
                      : 'Start a live camera/IMU stream first. The backend creates a session automatically, and this screen can then replay the latest fused windows for that session.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    height: 1.45,
                  ),
                ),
                if (_latestSyncError != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _latestSyncError!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.error,
                    ),
                  ),
                ],
                if (_latestSyncReplay != null) ...[
                  const SizedBox(height: 12),
                  _buildReplaySummary(theme, colorScheme, _latestSyncReplay!),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildReplayTimeline(theme, colorScheme),
          const SizedBox(height: 16),
          FilledButton.tonalIcon(
            onPressed: _isConnected ? _loadLatestSyncReplay : null,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Load Replay Window'),
          ),
          const SizedBox(height: 12),
          if (_currentSessionId.isNotEmpty ||
              (_apiService.currentSessionId ?? '').isNotEmpty)
            Text(
              'Active session: ${_currentSessionId.isNotEmpty ? _currentSessionId : _apiService.currentSessionId}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildReplayTimeline(ThemeData theme, ColorScheme colorScheme) {
    final canReplay = _syncApiAvailable && _availableReplaySeconds > 0;
    final maxSeconds = _availableReplaySeconds > 0
        ? _availableReplaySeconds.clamp(0.0, _maxReplaySeconds)
        : (_maxReplaySeconds > 0 ? _maxReplaySeconds : 120.0);
    final clampedOffset = _replayOffsetSeconds.clamp(0.0, maxSeconds);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            IconButton.filledTonal(
              onPressed: canReplay
                  ? () {
                      final target =
                          (clampedOffset + 10).clamp(0.0, maxSeconds);
                      _setReplayOffset(target);
                      _loadLatestSyncReplay(overrideOffsetSeconds: target);
                    }
                  : null,
              icon: const Icon(Icons.replay_10_rounded),
              tooltip: 'Move back 10 seconds',
            ),
            Expanded(
              child: Slider(
                value: clampedOffset,
                min: 0,
                max: maxSeconds,
                onChanged: canReplay ? _setReplayOffset : null,
                onChangeEnd: canReplay
                    ? (value) => _loadLatestSyncReplay(
                          overrideOffsetSeconds: value,
                        )
                    : null,
              ),
            ),
            IconButton.filledTonal(
              onPressed: canReplay
                  ? () => _loadLatestSyncReplay(overrideOffsetSeconds: 0)
                  : null,
              icon: const Icon(Icons.play_arrow_rounded),
              tooltip: 'Play synchronized stream',
            ),
          ],
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextButton(
              onPressed: canReplay
                  ? () {
                      _setReplayOffset(maxSeconds);
                      _loadLatestSyncReplay(
                        overrideOffsetSeconds: maxSeconds,
                      );
                    }
                  : null,
              child: Text(
                _maxReplaySeconds >= 120
                    ? '-2:00'
                    : '-${maxSeconds.toStringAsFixed(0)}s',
              ),
            ),
            TextButton(
              onPressed: canReplay
                  ? () {
                      _setReplayOffset(0);
                      _loadLatestSyncReplay(overrideOffsetSeconds: 0);
                    }
                  : null,
              child: const Text('Live'),
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
                  label: Text(
                    _currentSessionId.isNotEmpty ||
                            (_apiService.currentSessionId ?? '').isNotEmpty
                        ? (_syncApiAvailable ? 'Sync Ready' : 'Session Live')
                        : 'Sync Pending',
                  ),
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
