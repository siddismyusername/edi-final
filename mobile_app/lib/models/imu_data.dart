import 'package:json_annotation/json_annotation.dart';

part 'imu_data.g.dart';

/// Represents a single IMU (Inertial Measurement Unit) sensor reading.
/// Contains accelerometer and gyroscope data with a timestamp.
@JsonSerializable()
class ImuData {
  /// Unix timestamp in seconds (with microsecond precision)
  final double timestamp;

  /// Accelerometer X-axis reading in m/s²
  final double ax;

  /// Accelerometer Y-axis reading in m/s²
  final double ay;

  /// Accelerometer Z-axis reading in m/s²
  final double az;

  /// Gyroscope X-axis reading in rad/s
  final double gx;

  /// Gyroscope Y-axis reading in rad/s
  final double gy;

  /// Gyroscope Z-axis reading in rad/s
  final double gz;

  /// Creates an IMU data instance
  ImuData({
    required this.timestamp,
    required this.ax,
    required this.ay,
    required this.az,
    required this.gx,
    required this.gy,
    required this.gz,
  });

  /// Converts IMU data to JSON
  Map<String, dynamic> toJson() => _$ImuDataToJson(this);

  /// Creates IMU data from JSON
  factory ImuData.fromJson(Map<String, dynamic> json) =>
      _$ImuDataFromJson(json);

  @override
  String toString() =>
      'ImuData(ts: $timestamp, ax: $ax, ay: $ay, az: $az, gx: $gx, gy: $gy, gz: $gz)';
}
