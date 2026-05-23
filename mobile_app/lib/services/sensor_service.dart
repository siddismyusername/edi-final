import 'dart:async';
import 'package:sensors_plus/sensors_plus.dart';
import '../models/sensor_data.dart';

/// Service responsible for capturing IMU (accelerometer and gyroscope) sensor data.
class SensorService {
  // Singleton instance
  static final SensorService _instance = SensorService._internal();

  factory SensorService() {
    return _instance;
  }

  SensorService._internal();

  // Stream controllers for sensor data
  late StreamController<SensorData> _sensorDataController;
  StreamSubscription<AccelerometerEvent>? _accelSubscription;
  StreamSubscription<GyroscopeEvent>? _gyroSubscription;

  // Latest sensor readings
  AccelerometerEvent? _latestAccel;
  GyroscopeEvent? _latestGyro;

  /// Gets the stream of combined sensor data
  Stream<SensorData> get sensorStream => _sensorDataController.stream;

  /// Initializes the sensor service
  /// Starts listening to accelerometer and gyroscope events
  void initialize() {
    _sensorDataController = StreamController<SensorData>.broadcast();

    // Listen to accelerometer events
    _accelSubscription =
        accelerometerEventStream().listen((AccelerometerEvent event) {
      _latestAccel = event;
      _emitSensorData();
    });

    // Listen to gyroscope events
    _gyroSubscription =
        gyroscopeEventStream().listen((GyroscopeEvent event) {
      _latestGyro = event;
      _emitSensorData();
    });
  }

  /// Emits combined sensor data when both accel and gyro data are available
  void _emitSensorData() {
    if (_latestAccel != null && _latestGyro != null) {
      final sensorData = SensorData(
        timestamp: DateTime.now().millisecondsSinceEpoch / 1000.0,
        ax: _latestAccel!.x,
        ay: _latestAccel!.y,
        az: _latestAccel!.z,
        gx: _latestGyro!.x,
        gy: _latestGyro!.y,
        gz: _latestGyro!.z,
      );

      if (!_sensorDataController.isClosed) {
        _sensorDataController.add(sensorData);
      }
    }
  }

  /// Disposes the sensor service and closes all streams
  void dispose() {
    _accelSubscription?.cancel();
    _gyroSubscription?.cancel();
    _sensorDataController.close();
  }
}
