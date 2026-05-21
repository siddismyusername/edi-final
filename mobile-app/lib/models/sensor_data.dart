/// Represents a single sensor reading combining accelerometer and gyroscope data
class SensorData {
  final double timestamp;
  final double ax;
  final double ay;
  final double az;
  final double gx;
  final double gy;
  final double gz;

  SensorData({
    required this.timestamp,
    required this.ax,
    required this.ay,
    required this.az,
    required this.gx,
    required this.gy,
    required this.gz,
  });

  @override
  String toString() =>
      'SensorData(ts: $timestamp, ax: $ax, ay: $ay, az: $az, gx: $gx, gy: $gy, gz: $gz)';
}
