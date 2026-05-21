# ETA-Sync Mobile App - Project Index

**Quick Navigation Guide for Developers**

## 📚 Documentation Files

### Start Here 👇

1. **[QUICK_START.md](QUICK_START.md)** ⭐ START HERE
   - 5-minute quick start guide
   - Installation in 3 steps
   - Common commands and troubleshooting
   - **Read this first!**

2. **[SETUP.md](SETUP.md)** - Detailed Setup Guide
   - Complete installation instructions
   - Device configuration
   - Building for distribution
   - Comprehensive troubleshooting
   - Performance optimization

3. **[CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md)** - Architecture & Implementation
   - System architecture overview
   - Detailed module descriptions
   - Data flow diagrams
   - API documentation
   - Testing examples

4. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Project Summary
   - Overview of all created files
   - Feature checklist
   - File listing with descriptions
   - Architecture diagrams
   - Testing checklist

5. **[README.md](README.md)** - Main Project README
   - Project overview
   - System architecture
   - Features overview
   - Tech stack
   - API endpoints reference

---

## 📁 Source Code Structure

```
lib/
├── main.dart                           ← APPLICATION ENTRY POINT
│
├── screens/
│   └── home_screen.dart               ← MAIN UI (Server config, controls, status)
│
├── services/
│   ├── sensor_service.dart            ← IMU sensor data capture
│   ├── camera_service.dart            ← Camera frame capture
│   └── api_service.dart               ← Network communication
│
├── models/
│   ├── imu_data.dart                  ← IMU data model
│   └── imu_data.g.dart               ← Auto-generated JSON code
│
├── config/
│   └── app_config.dart                ← Configuration management
│
└── constants/
    └── app_constants.dart             ← App-wide constants
```

---

## 🚀 Quick Reference

### Getting Started (3 commands)
```bash
flutter pub get
flutter pub run build_runner build
flutter run
```

### File Purposes at a Glance

| File | Purpose | Lines |
|------|---------|-------|
| `main.dart` | App entry point & theme | 56 |
| `home_screen.dart` | Main UI with all controls | 480+ |
| `sensor_service.dart` | Accelerometer + Gyroscope | 90 |
| `camera_service.dart` | Camera frame capture | 140 |
| `api_service.dart` | Network & server communication | 120 |
| `imu_data.dart` | Model for sensor readings | 50 |
| `app_config.dart` | Configuration constants | 70 |
| `app_constants.dart` | App-wide string constants | 130 |

---

## 🔑 Key Concepts

### Services (Singleton Pattern)
Each service is a singleton for app-wide use:
```dart
final sensorService = SensorService();      // Single instance
final cameraService = CameraService();      // Single instance
final apiService = ApiService();            // Single instance
```

### Streaming Modes
- **Sync Mode**: Real-time synchronized data
- **Async Mode**: Simulated asynchronous (200ms delay on IMU)

### Data Flow
```
Device Sensors → Services → HomeScreen → ApiService → FastAPI Server
     (IMU)    (streaming)  (UI updates) (HTTP POST)    (/imu, /frame)
```

### Main Classes Overview

| Class | File | Responsibility |
|-------|------|-----------------|
| `ETASyncApp` | main.dart | Root app widget |
| `HomeScreen` | home_screen.dart | UI & user interactions |
| `SensorService` | sensor_service.dart | IMU data acquisition |
| `CameraService` | camera_service.dart | Camera frame capture |
| `ApiService` | api_service.dart | Server communication |
| `ImuData` | imu_data.dart | Sensor data model |

---

## 🔧 Development Workflow

```
1. Edit code in lib/ files
                ↓
2. Save (hot reload automatic)
                ↓
3. Test in emulator/device
                ↓
4. Check logs: flutter logs
                ↓
5. Generate code: flutter pub run build_runner build
                ↓
6. Build release: flutter build apk --release
```

---

## 📊 Project Statistics

- **Total Dart Files**: 9
- **Lines of Code**: ~1,500+
- **Documentation Pages**: 5
- **Services**: 3 (Sensor, Camera, API)
- **Models**: 2 (ImuData + generated)
- **Configuration Files**: 2
- **Supported Platforms**: Android, iOS, Linux, macOS, Windows

---

## 🎯 Common Tasks

### Change Server IP
Edit in app UI: "Server Address" text field

### Adjust Sampling Rate
Edit `lib/config/app_config.dart`:
```dart
static const int imuSamplingRateHz = 100;  // Change to desired Hz
```

### Adjust Camera FPS
Edit `lib/config/app_config.dart`:
```dart
static const int cameraFrameRateFps = 10;  // Change to 1-30
```

### Change Async Delay
Edit `lib/config/app_config.dart`:
```dart
static const int asyncModeDelayMs = 200;   // Change to desired ms
```

### View Console Logs
```bash
flutter logs
```

### Debug on Connected Device
```bash
flutter devices                    # See available devices
flutter run -d <device_id>        # Run on specific device
flutter run -v                    # Verbose mode
```

---

## 🐛 Debugging

### Enable Debug Output
All services use `kDebugMode` for logging:
```dart
if (kDebugMode) {
  print('[ServiceName] Debug message');
}
```

### Monitor Network
Check `ApiService` logs for HTTP requests/responses

### Monitor Sensors
Check `SensorService` logs for IMU data stream

### Monitor Camera
Check `CameraService` logs for frame capture

### Test Connection
App automatically tests connection when you click "Connect to Server"

---

## 📋 Checklist Before Building

- [ ] Flutter SDK installed (`flutter --version`)
- [ ] Dependencies installed (`flutter pub get`)
- [ ] JSON code generated (`flutter pub run build_runner build`)
- [ ] Device/emulator connected (`flutter devices`)
- [ ] Server IP configured in app
- [ ] Server running on laptop
- [ ] Both devices on same network

---

## 🚢 Building for Release

### Android APK:
```bash
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

### Android App Bundle (for Play Store):
```bash
flutter build appbundle --release
# Output: build/app/outputs/bundle/release/app-release.aab
```

### iOS:
```bash
flutter build ios --release
# Then open in Xcode: open ios/Runner.xcworkspace
```

---

## 🔗 API Integration

### Server Endpoints Used:

| Endpoint | Method | Purpose | Data Format |
|----------|--------|---------|------------|
| `/health` | GET | Connection check | - |
| `/imu` | POST | Send sensor data | JSON |
| `/frame` | POST | Send camera frame | JSON |

### Data Formats:

**IMU Data (POST /imu):**
```json
{
  "timestamp": 1709874022.123456,
  "ax": 0.12, "ay": 0.034, "az": 9.81,
  "gx": 0.001, "gy": 0.0002, "gz": 0.0015,
  "mode": "sync"
}
```

**Camera Frame (POST /frame):**
```json
{
  "timestamp": 1709874022.123456,
  "frame_id": 1234,
  "resolution": "640x480",
  "data": "base64_jpeg",
  "mode": "sync"
}
```

---

## 📦 Dependencies

| Package | Version | What For |
|---------|---------|----------|
| sensors_plus | 1.4.0 | Accelerometer & Gyroscope |
| camera | 0.10.0 | Camera frames |
| http | 1.1.0 | HTTP requests |
| permission_handler | 11.4.0 | Runtime permissions |
| image | 4.0.0 | Image processing |
| json_annotation | 4.8.0 | JSON support |

---

## 🆘 Troubleshooting Quick Links

- **Cannot connect to server**: See [SETUP.md](SETUP.md#3-cannot-connect-to-server)
- **Camera not working**: See [SETUP.md](SETUP.md#4-camera-not-initializing)
- **Build errors**: See [SETUP.md](SETUP.md#5-build-errors)
- **Permission denied**: See [SETUP.md](SETUP.md#1-camera-permission-denied)
- **Hot reload issues**: See [SETUP.md](SETUP.md#6-hot-reload-issues)

---

## 📞 Support Resources

- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Language Guide](https://dart.dev/guides)
- [sensors_plus Package](https://pub.dev/packages/sensors_plus)
- [camera Package](https://pub.dev/packages/camera)
- [http Package](https://pub.dev/packages/http)

---

## 📝 File Reading Order

**For New Developers:**
1. This file (INDEX.md) - Overview
2. [QUICK_START.md](QUICK_START.md) - Get running fast
3. [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) - Understand architecture
4. Source code files in order: main.dart → home_screen.dart → services

**For DevOps/Build:**
1. [SETUP.md](SETUP.md) - Installation & deployment
2. [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Build checklist

**For Researchers:**
1. [README.md](README.md) - Project overview
2. [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) - Data format details
3. Server README for backend details

---

## 🎓 Learning Path

```
BEGINNER    → QUICK_START.md → Run the app
       ↓
INTERMEDIATE → CODE_DOCUMENTATION.md → Understand architecture
       ↓
ADVANCED    → Source code files → Customize for research
       ↓
EXPERT      → SETUP.md → Deploy to production
```

---

## 📌 Important Files to Know

| File | When to Read |
|------|-------------|
| main.dart | Understanding app initialization |
| home_screen.dart | Adding UI features |
| sensor_service.dart | Modifying sensor behavior |
| camera_service.dart | Changing camera settings |
| api_service.dart | Modifying network communication |
| app_config.dart | Changing configuration |
| QUICK_START.md | Getting started fast |
| CODE_DOCUMENTATION.md | Understanding overall architecture |

---

## 💡 Pro Tips

1. **Hot Reload**: Press `r` in terminal while running
2. **Hot Restart**: Press `R` in terminal while running
3. **View Logs**: Run `flutter logs` in another terminal
4. **Verbose Mode**: Add `-v` flag: `flutter run -v`
5. **Clean Build**: Run `flutter clean` before troubleshooting
6. **Device List**: `flutter devices` to see available devices

---

## 📅 Version Information

- **Project Version**: 1.0.0
- **Flutter SDK**: 3.0+
- **Dart SDK**: 3.0+
- **Android SDK**: API 21+
- **iOS**: 11.0+
- **Created**: March 2026

---

**Last Updated**: March 2026 | **Status**: ✅ Complete and Ready for Use
