# ETA-Sync Mobile App - Quick Start Guide

## 5-Minute Quick Start

### Prerequisites
- Flutter SDK installed (`flutter --version` to verify)
- A physical device or emulator
- FastAPI server running (see server README)

### Installation

```bash
# 1. Get dependencies
flutter pub get

# 2. Generate JSON code
flutter pub run build_runner build

# 3. Run the app
flutter run
```

### First Time Setup

1. **Connect to Server**
   - Find your server IP: `ipconfig` (Windows) or `ifconfig` (macOS/Linux)
   - In the app, enter: `192.168.1.10:8000` (replace with your IP)
   - Tap "Connect to Server"
   - Status should show "Connected" ✓

2. **Select Streaming Mode**
   - Choose between:
     - **Sync Mode**: Real-time fixed-interval streaming
     - **Async Mode**: Demonstrates asynchronous sensors with 200ms delay

3. **Collect Data**
   - Tap "Start Streaming" 
   - Move your device and rotate it
   - Watch the counters increase (IMU samples & frames)
   - Tap "Stop Streaming" when done

### Project Structure

```
lib/
├── main.dart                    # App entry point
├── config/
│   └── app_config.dart         # Configuration
├── constants/
│   └── app_constants.dart      # App constants
├── screens/
│   └── home_screen.dart        # Main UI
├── services/
│   ├── api_service.dart        # Network communication
│   ├── camera_service.dart     # Camera frames
│   └── sensor_service.dart     # IMU sensors
└── models/
    └── imu_data.dart           # Data model
```

### Key Files

| File | Purpose |
|------|---------|
| `main.dart` | Application entry point |
| `home_screen.dart` | Main UI and controls |
| `sensor_service.dart` | IMU data capture |
| `camera_service.dart` | Camera frame capture |
| `api_service.dart` | Server communication |
| `imu_data.dart` | Sensor data model |

### Common Commands

```bash
# Run the app
flutter run

# Debug build
flutter run -v

# Release build (Android)
flutter build apk --release

# Clean build cache
flutter clean

# Check for issues
flutter analyze

# View live logs
flutter logs

# Format code
dart format lib/

# Run tests
flutter test
```

### Troubleshooting

#### "Cannot connect to server"
- [ ] Server is running on laptop
- [ ] Both devices on same WiFi network
- [ ] IP address is correct (e.g., 192.168.1.10)
- [ ] Port number is correct (default: 8000)
- [ ] Firewall allows port 8000

#### "Camera permission denied"
```bash
# Android
Settings > Apps > ETA-Sync > Permissions > Camera > ON

# iOS
Settings > Privacy > Camera > Enable ETA-Sync
```

#### "Build errors"
```bash
flutter clean
rm pubspec.lock
flutter pub get
flutter run
```

#### "Camera not initializing"
- Check at least one camera is available
- Try restarting the app
- Check Android/iOS logs: `flutter logs`

### API Endpoints

The app sends data to:

- **`POST /imu`** - Accelerometer & gyroscope data
- **`POST /frame`** - Camera frames (JPEG)
- **`GET /health`** - Server health check

### Data Format Sent to Server

**IMU Data:**
```json
{
  "timestamp": 1709874022.123456,
  "ax": 0.12, "ay": 0.034, "az": 9.81,
  "gx": 0.001, "gy": 0.0002, "gz": 0.0015,
  "mode": "sync"
}
```

**Camera Frame:**
```json
{
  "timestamp": 1709874022.123456,
  "frame_id": 1234,
  "resolution": "640x480",
  "data": "base64_encoded_jpeg_bytes",
  "mode": "sync"
}
```

### Configuration

Edit `lib/config/app_config.dart` to change:
- Server host/port
- IMU sampling rate (Hz)
- Camera frame rate (FPS)
- Async delay (ms)
- JPEG quality

### File Structure Generated

When you run `flutter pub run build_runner build`:
- `imu_data.g.dart` - Auto-generated JSON serialization code

**Don't manually edit `*.g.dart` files!**

### Performance Tips

1. **Lower camera resolution** for faster processing
2. **Reduce sampling rate** if device lags
3. **Use release build** for better performance:
   ```bash
   flutter run --release
   ```

### What the App Does

1. **Captures**
   - Accelerometer data (x, y, z) in m/s²
   - Gyroscope data (x, y, z) in rad/s
   - Camera frames at 10 FPS

2. **Sends** (continuously while streaming)
   - IMU samples to `/imu` endpoint
   - Frames to `/frame` endpoint
   - Timestamps with each reading

3. **Modes**
   - **Sync**: Both streams timestamped together
   - **Async**: IMU stream delayed by 200ms

### Next Steps

1. ✅ Complete the Quick Start above
2. 📖 Read [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) for architecture details
3. 🔧 Read [SETUP.md](SETUP.md) for advanced setup
4. 🚀 Collect data and train models!

### Development Workflow

```bash
# Edit code
# (auto-reload enabled)
# Press 'r' in terminal to hot-reload
# Press 'R' to hot-restart

# When ready to deploy
flutter build apk --release  # Android
flutter build ios --release  # iOS
```

### Useful Resources

- [Flutter Docs](https://flutter.dev/docs)
- [Dart Guide](https://dart.dev/guides)
- [sensors_plus Package](https://pub.dev/packages/sensors_plus)
- [camera Package](https://pub.dev/packages/camera)
- [http Package](https://pub.dev/packages/http)

### Network Architecture

```
┌─────────────────────────────────────────┐
│  ETA-Sync Mobile App (Flutter/Dart)     │
│  ├─ IMU Sensors (Accel + Gyro)          │
│  ├─ Camera (10 FPS)                     │
│  └─ WiFi/Network                        │
└────────────────┬────────────────────────┘
                 │ HTTP POST
                 │ /imu & /frame
                 ▼
┌─────────────────────────────────────────┐
│  FastAPI Server (Python)                │
│  Runs on: http://192.168.1.10:8000      │
│  ├─ Receives IMU data                   │
│  ├─ Receives camera frames              │
│  ├─ Stores to disk/database             │
│  └─ Provides API endpoints              │
└─────────────────────────────────────────┘
```

### Real-World Usage

The app is designed for research data collection:

1. Place device on subject in controlled environment
2. Start streaming (app will collect IMU + video)
3. Subject performs actions (walk, run, gesture, etc.)
4. Stop streaming when done
5. Data automatically sent to server
6. Use collected dataset for:
   - Training alignment models
   - DTW analysis
   - Cross-attention mechanism studies

### Support

For issues:
1. Check troubleshooting section above
2. Review [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md)
3. Run: `flutter logs` to see debug output
4. Run: `flutter run -v` for verbose diagnostics

---

**Need help?** Create an issue on GitHub or check the documentation files.

**Happy coding!** 🚀
