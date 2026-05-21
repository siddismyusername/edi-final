/// Configuration file for ETA-Sync Mobile Application
/// 
/// Contains server URL, API endpoints, and app configuration constants

class AppConfig {
  // Server Configuration
  // Change these values to match your FastAPI server setup
  
  /// Default FastAPI server host (set at runtime)
  static String serverHost = 'localhost';
  
  /// Default FastAPI server port
  static const int serverPort = 8000;
  
  /// Connection timeout in seconds
  static const int connectionTimeoutSeconds = 5;
  
  // Sensor Configuration
  
  /// Default IMU sampling rate in Hz
  static const int imuSamplingRateHz = 100;
  
  /// Default camera frame rate in FPS (frames per second)
  static const int cameraFrameRateFps = 10;
  
  /// Maximum camera resolution (lower = better performance)
  static const String cameraResolution = 'medium';
  
  // Streaming Configuration
  
  /// Delay in milliseconds for async mode (simulates sensor delay)
  static const int asyncModeDelayMs = 200;
  
  // Data Format Configuration
  
  /// API version
  static const String apiVersion = 'v1';
  
  /// JPEG compression quality (0-100)
  static const int jpegCompressionQuality = 80;
  
  // Server Endpoints
  
  /// Build full server URL
  static String getServerUrl() {
    return 'http://$serverHost:$serverPort';
  }
  
  /// Health check endpoint
  static const String healthEndpoint = '/health';
  
  /// IMU data endpoint
  static const String imuEndpoint = '/imu';
  
  /// Camera frame endpoint
  static const String frameEndpoint = '/frame';
  
  /// Session creation endpoint
  static const String sessionEndpoint = '/session';
  
  // App Metadata
  
  static const String appName = 'ETA-Sync Mobile';
  static const String appVersion = '1.0.0';
  static const String buildNumber = '1';
  
  /// Get formatted server URL with endpoint
  static String getEndpointUrl(String endpoint) {
    return '${getServerUrl()}$endpoint';
  }
  
  /// Validate server URL format
  static bool isValidServerUrl(String url) {
    try {
      Uri.parse(url);
      return url.isNotEmpty;
    } catch (e) {
      return false;
    }
  }
}
