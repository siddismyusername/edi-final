# ETA-Sync Flutter App - Code Documentation

## Architecture Overview

The ETA-Sync Flutter application follows a modular, service-based architecture with clear separation of concerns.

```
┌─────────────────────────────────────────┐
│         UI Layer (Screens)              │
│  - HomeScreen (Main UI)                 │
│  - Status Display                       │
│  - Controls & Configuration             │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│       Service Layer (Services)          │
│  - SensorService (IMU data)             │
│  - CameraService (Frame capture)        │
│  - ApiService (Network comms)           │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      Model Layer (Data Models)          │
│  - ImuData (IMU sensor reading)         │
│  - CameraFrameData (Frame info)         │
└─────────────────────────────────────────┘
```

## Module Descriptions

### 1. Main Application (`lib/main.dart`)

**Purpose**: Application entry point and root widget configuration

**Key Components**:
- `ETASyncApp`: Root MaterialApp widget
- Defines theme, routes, and global configuration

**Usage**:
```dart
void main() {
  runApp(const ETASyncApp());
}
```

---

### 2. Home Screen (`lib/screens/home_screen.dart`)

**Purpose**: Main user interface for data capture and server configuration

**Key Features**:
- Server URL input and connection management
- Streaming mode selection (Sync/Async)
- Start/Stop data collection buttons
- Real-time status and statistics display

**State Management**:
- `_isStreaming`: Indicates if data capture is active
- `_streamingMode`: Selected mode ('sync' or 'async')
- `_isConnected`: Server connection status
- `_imuCount`, `_frameCount`: Data counters

**Key Methods**:
```dart
_connectToServer()      // Establish server connection
_startStreaming()       // Begin data capture
_stopStreaming()        // End data capture
_handleSensorData()     // Process incoming IMU data
_handleCameraFrame()    // Process incoming camera frames
```

---

### 3. Sensor Service (`lib/services/sensor_service.dart`)

**Purpose**: Captures and manages IMU sensor data streams

**Singleton Pattern**: Single instance throughout app lifetime

**Supported Sensors**:
- Accelerometer (x, y, z axes in m/s²)
- Gyroscope (x, y, z axes in rad/s)

**Key Classes**:
- `SensorService`: Main service class
- `SensorData`: Container for combined sensor reading

**Usage Example**:
```dart
final sensorService = SensorService();

// Initialize sensor service
sensorService.initialize();

// Subscribe to sensor stream
sensorService.sensorStream.listen((SensorData data) {
  print('Accel: ${data.ax}, ${data.ay}, ${data.az}');
  print('Gyro: ${data.gx}, ${data.gy}, ${data.gz}');
});

// Cleanup
sensorService.dispose();
```

**Data Output**:
```dart
SensorData {
  timestamp: 1709874022.123456,   // Unix timestamp in seconds
  ax: 0.12,                        // m/s²
  ay: 0.034,                       // m/s²
  az: 9.81,                        // m/s²
  gx: 0.001,                       // rad/s
  gy: 0.0002,                      // rad/s
  gz: 0.0015                       // rad/s
}
```

---

### 4. Camera Service (`lib/services/camera_service.dart`)

**Purpose**: Captures camera frames and processes them for transmission

**Key Features**:
- Asynchronous frame capture at specified FPS
- JPEG compression for efficient transmission
- Frame metadata (timestamp, ID, resolution)

**Key Classes**:
- `CameraService`: Main service class
- `CameraFrameData`: Container for frame information

**Usage Example**:
```dart
final cameraService = CameraService();

// Initialize camera
await cameraService.initialize();

// Start capturing at 10 FPS
cameraService.startCapturing(fps: 10);

// Subscribe to frames
cameraService.frameStream?.listen((CameraFrameData frame) {
  print('Frame ${frame.frameId} at ${frame.timestamp}');
  print('Size: ${frame.jpegData.length} bytes');
});

// Stop capturing
cameraService.stopCapturing();

// Cleanup
await cameraService.dispose();
```

**Data Output**:
```dart
CameraFrameData {
  timestamp: 1709874022.123456,    // Unix timestamp in seconds
  jpegData: List<int>,              // Raw JPEG bytes
  frameId: 1234,                    // Sequential frame ID
  resolution: "640x480"             // Camera resolution
}
```

---

### 5. API Service (`lib/services/api_service.dart`)

**Purpose**: Handles all network communication with FastAPI server

**Singleton Pattern**: Single instance for all API calls

**Key Methods**:
```dart
setServerUrl(String url)           // Configure server and test connection
sendImuData(Map json)              // POST IMU data to /imu
sendCameraFrame(Map json)          // POST frame to /frame
testConnection()                   // Test server connectivity
```

**Connection Status Stream**:
```dart
apiService.connectionStatusStream.listen((bool connected) {
  print(connected ? 'Connected' : 'Disconnected');
});
```

**Error Handling**:
- Automatic timeout management (5 seconds)
- Connection retry logic
- Error logging via print statements

---

### 6. IMU Data Model (`lib/models/imu_data.dart`)

**Purpose**: Data model for sensor readings with JSON serialization

**Features**:
- JSON serialization via `json_serializable` package
- Type-safe data access
- Automatic code generation

**Definition**:
```dart
class ImuData {
  final double timestamp;  // Unix timestamp
  final double ax, ay, az; // Accelerometer
  final double gx, gy, gz; // Gyroscope
  final String mode;       // "sync" or "async"
  
  Map<String, dynamic> toJson()  // Convert to JSON
  factory ImuData.fromJson(Map<String, dynamic> json)  // Create from JSON
}
```

**JSON Format**:
```json
{
  "timestamp": 1709874022.123456,
  "ax": 0.12,
  "ay": 0.034,
  "az": 9.81,
  "gx": 0.001,
  "gy": 0.0002,
  "gz": 0.0015,
  "mode": "sync"
}
```

---

### 7. Configuration (`lib/config/app_config.dart`)

**Purpose**: Centralized configuration management

**Key Constants**:
```dart
AppConfig.serverHost         // Server IP address
AppConfig.serverPort         // Server port (default: 8000)
AppConfig.imuSamplingRateHz  // IMU sampling frequency
AppConfig.cameraFrameRateFps // Camera FPS
AppConfig.asyncModeDelayMs   // Async mode delay (200ms)
```

**Helper Methods**:
```dart
AppConfig.getServerUrl()              // Get full server URL
AppConfig.getEndpointUrl(endpoint)    // Get full endpoint URL
AppConfig.isValidServerUrl(url)       // Validate URL format
```

---

## Data Flow

### Synchronous Mode

```
1. HomeScreen calls _startStreaming()
   ↓
2. SensorService.initialize() starts listening to device sensors
   ↓
3. CameraService.startCapturing() begins frame capture at 10 FPS
   ↓
4. When IMU data arrives:
   - Create ImuData with current timestamp
   - Call ApiService.sendImuData() (POST to /imu)
   - Update UI counter
   ↓
5. When camera frame arrives:
   - Encode frame to base64
   - Call ApiService.sendCameraFrame() (POST to /frame)
   - Update UI counter
```

### Asynchronous Mode

```
1-3. Same as synchronous mode
   ↓
4. When IMU data arrives:
   - Store in _pendingSensorData
   - Schedule delayed execution (200ms timer)
   - After delay: send to server
   - Update UI counter
   ↓
5. When camera frame arrives:
   - Send immediately (no delay)
   - Update UI counter
```

---

## Permission Handling

The app requests the following permissions at runtime:

**Android** (via `permission_handler`):
- `Permission.camera`: Camera access
- `Permission.microphone`: Microphone (for camera)
- `Permission.sensors`: IMU sensor access

**iOS** (via `Info.plist`):
- `NSCameraUsageDescription`: Camera access request
- `NSMotionUsageDescription`: Motion sensor access
- `NSMicrophoneUsageDescription`: Microphone access
- `NSLocationWhenInUseUsageDescription`: Location context

Request flow:
```dart
Future<bool> _requestPermissions() async {
  final cameraStatus = await Permission.camera.request();
  final microphoneStatus = await Permission.microphone.request();
  final sensorsStatus = await Permission.sensors.request();
  
  return cameraStatus.isGranted && 
         microphoneStatus.isGranted && 
         sensorsStatus.isGranted;
}
```

---

## Error Handling Strategy

### Connection Errors
```dart
try {
  final connected = await _apiService.setServerUrl(url);
  if (!connected) {
    _showErrorDialog('Failed to connect to server');
  }
} catch (e) {
  _showErrorDialog('Error: $e');
}
```

### Permission Errors
```dart
final hasPermissions = await _requestPermissions();
if (!hasPermissions) {
  _showErrorDialog('Camera and sensor permissions are required');
  return;
}
```

### Sensor Errors
```dart
sensorSubscription = sensorService.sensorStream.listen(
  (data) => _handleSensorData(data),
  onError: (error) {
    print('Sensor error: $error');
    _stopStreaming();
  },
);
```

---

## State Management

The app uses Flutter's built-in `setState()` for state management. For larger apps, consider:
- **Provider**: Simple, reactive state management
- **BLoC**: Event-driven pattern
- **Riverpod**: Modern reactive framework
- **GetX**: Full-featured framework

---

## Debugging Tips

### Enable Verbose Logging:
```bash
flutter run -v
flutter logs
```

### Add Custom Debug Logs:
```dart
if (kDebugMode) {
  print('[ServiceName] Debug message');
}
```

### Monitor Network Traffic:
- Use Flutter DevTools: `flutter pub global activate devtools`
- Run: `devtools` and connect to running app

### Test Sensor Data:
```dart
final sensorService = SensorService();
sensorService.initialize();
sensorService.sensorStream.listen((data) {
  print('IMU Data: $data');
});
```

---

## Performance Optimization

### Memory Management
- Use StreamControllers with `.broadcast()` to allow multiple listeners
- Cancel subscriptions in `dispose()`
- Limit buffer sizes for continuous streams

### Network Optimization
- Use `http` package for simple REST APIs
- Consider `web_socket_channel` for real-time streaming
- Implement retry logic with exponential backoff

### Camera Performance
- Lower resolution = faster processing
- Reduce frame rate if needed
- Use JPEG compression (currently quality: 80)

### Sensor Performance
- Use appropriate sampling rate (default: 100 Hz)
- Filter outliers in server-side processing

---

## Testing

### Unit Tests:
```dart
test('IMU data serialization', () {
  final imuData = ImuData(
    timestamp: 1.0,
    ax: 0.1, ay: 0.2, az: 9.8,
    gx: 0.01, gy: 0.02, gz: 0.03,
    mode: 'sync',
  );
  
  final json = imuData.toJson();
  expect(json['ax'], 0.1);
});
```

### Widget Tests:
```dart
testWidgets('Home screen renders', (WidgetTester tester) async {
  await tester.pumpWidget(const ETASyncApp());
  expect(find.text('ETA-Sync Mobile'), findsOneWidget);
});
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flutter | SDK | UI framework |
| sensors_plus | 1.4.0 | IMU sensors |
| camera | 0.10.0 | Camera access |
| http | 1.1.0 | HTTP requests |
| permission_handler | 11.4.0 | Runtime permissions |
| image | 4.0.0 | Image processing |
| json_annotation | 4.8.0 | JSON support |

---

## Contributing Guidelines

1. Follow Dart style conventions
2. Add documentation for public APIs
3. Use meaningful variable names
4. Add error handling for async operations
5. Test code before submitting PR
6. Keep commits atomic and descriptive

---

## License

MIT License - See LICENSE file for details

---

**Last Updated**: March 2026 | **Version**: 1.0.0
