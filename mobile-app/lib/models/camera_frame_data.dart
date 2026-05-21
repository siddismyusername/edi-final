/// Represents captured camera frame data
class CameraFrameData {
  final double timestamp;
  final List<int> jpegData;
  final int frameId;
  final String resolution;

  CameraFrameData({
    required this.timestamp,
    required this.jpegData,
    required this.frameId,
    required this.resolution,
  });

  @override
  String toString() =>
      'CameraFrameData(ts: $timestamp, size: ${jpegData.length} bytes, id: $frameId, res: $resolution)';
}
