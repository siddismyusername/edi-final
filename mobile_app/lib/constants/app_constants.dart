// App-wide constants used throughout the ETA-Sync mobile application.

class AppConstants {
  // Prevent instantiation
  AppConstants._();

  // ==================== App Information ====================
  static const String appName = 'ETA-Sync Mobile';
  static const String appVersion = '1.0.0';
  static const String appBuildNumber = '1';

  // ==================== Network Configuration ====================
  /// Default connection timeout in seconds
  static const int networkTimeoutSeconds = 5;

  /// Default retry attempts for failed connections
  static const int connectionRetryAttempts = 3;

  /// Delay between retry attempts in milliseconds
  static const int retryDelayMs = 1000;

  // ==================== Sensor Configuration ====================
  /// Default sampling rate for accelerometer and gyroscope (Hz)
  static const int defaultSamplingRateHz = 100;

  /// Minimum sampling rate (Hz)
  static const int minSamplingRateHz = 10;

  /// Maximum sampling rate (Hz)
  static const int maxSamplingRateHz = 200;

  // ==================== Camera Configuration ====================
  /// Default camera frame rate (FPS)
  static const int defaultFrameRateFps = 10;

  /// Minimum camera frame rate (FPS)
  static const int minFrameRateFps = 1;

  /// Maximum camera frame rate (FPS)
  static const int maxFrameRateFps = 30;

  /// JPEG compression quality (0-100)
  static const int jpegQuality = 80;

  // ==================== UI Constants ====================
  /// Standard padding for UI elements
  static const double standardPadding = 16.0;

  /// Standard border radius
  static const double standardBorderRadius = 8.0;

  /// Card elevation
  static const double standardCardElevation = 2.0;

  // ==================== Database & Storage ====================
  /// Session timestamp format pattern
  static const String sessionTimestampPattern = 'yyyy-MM-dd_HH:mm:ss';

  /// Max stored sessions to keep locally
  static const int maxLocalSessions = 100;

  // ==================== Error Messages ====================
  static const String errorCameraNotAvailable =
      'No camera found on this device';

  static const String errorCameraInitFailed =
      'Failed to initialize camera. Check permissions.';

  static const String errorSensorAccessDenied =
      'Sensor access permission denied';

  static const String errorCameraAccessDenied =
      'Camera access permission denied';

  static const String errorServerConnectionFailed =
      'Could not connect to server. Check IP address and network.';

  static const String errorInvalidServerUrl = 'Invalid server URL format';

  static const String errorDataSendFailed = 'Failed to send data to server';

  // ==================== Success Messages ====================
  static const String successServerConnected = 'Connected to server';

  static const String successStreamingStarted = 'Data streaming started';

  static const String successStreamingStopped = 'Data streaming stopped';

  static const String successDataSent = 'Data successfully sent';

  // ==================== Info Messages ====================
  static const String infoConnecting = 'Connecting to server...';

  static const String infoStreaming = 'Streaming data...';

  static const String infoStopped = 'Stopped';

  // ==================== Logging Prefixes ====================
  static const String logSensorService = '[SensorService]';
  static const String logCameraService = '[CameraService]';
  static const String logApiService = '[ApiService]';
  static const String logHomeScreen = '[HomeScreen]';
  static const String logMain = '[Main]';

  // ==================== Data Limits ====================
  /// Maximum batch size for data transmission
  static const int maxBatchSize = 100;

  /// Maximum frame history to keep in memory
  static const int maxFrameHistory = 500;

  /// Maximum sensor sample history
  static const int maxSensorHistory = 5000;
}
