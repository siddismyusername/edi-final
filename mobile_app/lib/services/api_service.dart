import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class SyncPlaybackStatus {
  const SyncPlaybackStatus({
    required this.available,
    required this.ready,
    required this.availableSeconds,
    required this.maxReplaySeconds,
  });

  final bool available;
  final bool ready;
  final double availableSeconds;
  final double maxReplaySeconds;
}

/// Service responsible for API communication with the FastAPI server.
class ApiService {
  // Singleton instance
  static final ApiService _instance = ApiService._internal();

  factory ApiService() {
    return _instance;
  }

  ApiService._internal();

  String _serverUrl = '';
  bool _isConnected = false;
  String? _currentSessionId;
  final _connectionStatusController = StreamController<bool>.broadcast();

  /// Gets the connection status stream
  Stream<bool> get connectionStatusStream => _connectionStatusController.stream;

  /// Gets the current connection status
  bool get isConnected => _isConnected;

  /// Gets the current server URL
  String get serverUrl => _serverUrl;

  /// Gets the latest live session ID returned by the backend.
  String? get currentSessionId => _currentSessionId;

  void _captureSessionIdFromResponse(http.Response response) {
    try {
      if (response.body.isEmpty) {
        return;
      }

      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        final sessionId = decoded['session_id'];
        if (sessionId is String && sessionId.isNotEmpty) {
          _currentSessionId = sessionId;
        }
      }
    } catch (e) {
      if (kDebugMode) {
        print('[ApiService] Failed to parse session id: $e');
      }
    }
  }

  /// Sets the server URL and tests the connection
  /// [url]: The base URL of the FastAPI server (e.g., "http://192.168.1.10:8000")
  Future<bool> setServerUrl(String url) async {
    _serverUrl = url.replaceAll(RegExp(r'/$'), ''); // Remove trailing slash

    try {
      // Test connection with a health check
      final response = await http
          .get(
            Uri.parse('$_serverUrl/health'),
          )
          .timeout(const Duration(seconds: 5));

      _isConnected = response.statusCode == 200;

      if (kDebugMode) {
        print(
            '[ApiService] Connection test: ${_isConnected ? 'SUCCESS' : 'FAILED'}');
      }

      if (!_isConnected) {
        _currentSessionId = null;
      }
    } catch (e) {
      _isConnected = false;
      _currentSessionId = null;
      if (kDebugMode) {
        print('[ApiService] Connection error: $e');
      }
    }

    _connectionStatusController.add(_isConnected);
    return _isConnected;
  }

  /// Sends IMU data to the server
  /// [imuJson]: The IMU data as a JSON map
  Future<bool> sendImuData(Map<String, dynamic> imuJson) async {
    if (!_isConnected) {
      if (kDebugMode) {
        print('[ApiService] Not connected to server');
      }
      return false;
    }

    try {
      final response = await http
          .post(
            Uri.parse('$_serverUrl/imu'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(imuJson),
          )
          .timeout(const Duration(seconds: 5));

      if (kDebugMode) {
        print('[ApiService] IMU response: ${response.statusCode}'
            '${response.statusCode >= 400 ? ' ${response.body}' : ''}');
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        _captureSessionIdFromResponse(response);
      }

      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      if (kDebugMode) {
        print('[ApiService] IMU send error: $e');
      }
      return false;
    }
  }

  /// Sends camera frame to the server
  /// [frameJson]: The frame data as a JSON map with 'data' containing base64 encoded JPEG
  Future<bool> sendCameraFrame(Map<String, dynamic> frameJson) async {
    if (!_isConnected) {
      if (kDebugMode) {
        print('[ApiService] Not connected to server');
      }
      return false;
    }

    try {
      final response = await http
          .post(
            Uri.parse('$_serverUrl/frame'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(frameJson),
          )
          .timeout(const Duration(seconds: 5));

      if (kDebugMode) {
        print('[ApiService] Frame response: ${response.statusCode}'
            '${response.statusCode >= 400 ? ' ${response.body}' : ''}');
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        _captureSessionIdFromResponse(response);
      }

      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      if (kDebugMode) {
        print('[ApiService] Frame send error: $e');
      }
      return false;
    }
  }

  /// Test the server connection without changing the URL
  Future<bool> testConnection() async {
    if (_serverUrl.isEmpty) {
      return false;
    }

    try {
      final response = await http
          .get(
            Uri.parse('$_serverUrl/health'),
          )
          .timeout(const Duration(seconds: 5));

      final connected = response.statusCode == 200;
      if (_isConnected != connected) {
        _isConnected = connected;
        _connectionStatusController.add(_isConnected);
      }

      return connected;
    } catch (e) {
      if (_isConnected) {
        _isConnected = false;
        _connectionStatusController.add(false);
      }
      return false;
    }
  }

  /// Checks whether sync playback is available for the current live session.
  Future<SyncPlaybackStatus> getSyncPlaybackStatus({String? sessionId}) async {
    if (!_isConnected || _serverUrl.isEmpty) {
      return const SyncPlaybackStatus(
        available: false,
        ready: false,
        availableSeconds: 0,
        maxReplaySeconds: 0,
      );
    }

    try {
      final uri = sessionId == null || sessionId.isEmpty
          ? Uri.parse('$_serverUrl/sync/status')
          : Uri.parse('$_serverUrl/sync/status?session_id=$sessionId');

      final response = await http.get(uri).timeout(const Duration(seconds: 5));

      if (kDebugMode) {
        print('[ApiService] Sync status response: ${response.statusCode}');
      }

      if (response.statusCode != 200) {
        return const SyncPlaybackStatus(
          available: false,
          ready: false,
          availableSeconds: 0,
          maxReplaySeconds: 0,
        );
      }

      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        return SyncPlaybackStatus(
          available: decoded['available'] as bool? ?? true,
          ready: decoded['ready'] as bool? ?? false,
          availableSeconds:
              (decoded['available_seconds'] as num?)?.toDouble() ?? 0,
          maxReplaySeconds:
              (decoded['max_replay_seconds'] as num?)?.toDouble() ?? 0,
        );
      }

      return const SyncPlaybackStatus(
        available: true,
        ready: false,
        availableSeconds: 0,
        maxReplaySeconds: 0,
      );
    } catch (e) {
      if (kDebugMode) {
        print('[ApiService] Sync status unavailable: $e');
      }
      return const SyncPlaybackStatus(
        available: false,
        ready: false,
        availableSeconds: 0,
        maxReplaySeconds: 0,
      );
    }
  }

  /// Fetches the latest fused replay snapshot for a session.
  Future<Map<String, dynamic>?> getLatestSyncReplay({
    required String sessionId,
    double offsetSeconds = 0.0,
  }) async {
    if (!_isConnected || _serverUrl.isEmpty || sessionId.isEmpty) {
      return null;
    }

    try {
      final uri = Uri.parse(
        '$_serverUrl/sync/latest?session_id=$sessionId&offset_seconds=$offsetSeconds',
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 5));

      if (kDebugMode) {
        print('[ApiService] Sync latest response: ${response.statusCode}');
      }

      if (response.statusCode != 200) {
        return null;
      }

      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      return null;
    } catch (e) {
      if (kDebugMode) {
        print('[ApiService] Sync latest unavailable: $e');
      }
      return null;
    }
  }

  /// Disposes the API service
  void dispose() {
    _connectionStatusController.close();
  }
}
