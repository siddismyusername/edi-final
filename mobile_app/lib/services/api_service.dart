import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

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
  final _connectionStatusController = StreamController<bool>.broadcast();

  /// Gets the connection status stream
  Stream<bool> get connectionStatusStream => _connectionStatusController.stream;

  /// Gets the current connection status
  bool get isConnected => _isConnected;

  /// Gets the current server URL
  String get serverUrl => _serverUrl;

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
    } catch (e) {
      _isConnected = false;
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
        print('[ApiService] IMU response: ${response.statusCode}');
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
        print('[ApiService] Frame response: ${response.statusCode}');
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

  /// Checks whether the backend exposes the planned sync playback API.
  Future<bool> isSyncPlaybackAvailable() async {
    if (!_isConnected || _serverUrl.isEmpty) {
      return false;
    }

    try {
      final response = await http
          .get(
            Uri.parse('$_serverUrl/sync/status'),
          )
          .timeout(const Duration(seconds: 5));

      if (kDebugMode) {
        print('[ApiService] Sync status response: ${response.statusCode}');
      }

      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) {
        print('[ApiService] Sync status unavailable: $e');
      }
      return false;
    }
  }

  /// Disposes the API service
  void dispose() {
    _connectionStatusController.close();
  }
}
