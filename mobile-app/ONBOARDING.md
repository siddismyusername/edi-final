# ETA-Sync Mobile App - Developer Onboarding Guide

Welcome to the ETA-Sync Mobile App project! This guide will get you up and running in 5 minutes.

## ⚡ Quickstart (Do This First!)

### 1️⃣ Prerequisites Check
```bash
# Verify Flutter is installed
flutter --version

# Run doctor to check dependencies
flutter doctor
```

### 2️⃣ Setup Project
```bash
# Navigate to project
cd eta_sync_app

# Get dependencies
flutter pub get

# Generate JSON serialization code
flutter pub run build_runner build
```

### 3️⃣ Run the App
```bash
# See available devices
flutter devices

# Run on your device
flutter run

# (Or add -v for verbose output)
flutter run -v
```

**That's it!** The app should now be running. 🎉

---

## 🎯 What This App Does

### Captures:
- 📡 **Accelerometer data** (X, Y, Z axes)
- 🔄 **Gyroscope data** (X, Y, Z rotation)
- 📸 **Camera frames** (JPEG, ~10 FPS)

### Sends:
- HTTP POST to `/imu` endpoint (sensor data)
- HTTP POST to `/frame` endpoint (camera frames)
- Both with precise timestamps

### Modes:
- **Sync Mode**: Both streams timestamped together
- **Async Mode**: IMU stream delayed by 200ms (simulates asynchronous sensors)

---

## 📂 Project Structure (What's Where)

```
lib/
├── main.dart                    ← App entry point
├── screens/
│   └── home_screen.dart        ← UI with controls
├── services/
│   ├── sensor_service.dart     ← Captures IMU data
│   ├── camera_service.dart     ← Captures frames
│   └── api_service.dart        ← Sends to server
├── models/
│   └── imu_data.dart           ← Sensor data format
├── config/
│   └── app_config.dart         ← Settings
└── constants/
    └── app_constants.dart      ← Constants
```

**Key File: `home_screen.dart`** - This is the UI you see when you open the app.

---

## 🔧 Configuration

All settings are in `lib/config/app_config.dart`:

```dart
// Server settings
static String serverHost = 'localhost';
static const int serverPort = 8000;

// Sensor settings
static const int imuSamplingRateHz = 100;      // IMU frequency

// Camera settings
static const int cameraFrameRateFps = 10;      // Camera frequency
static const int jpegCompressionQuality = 80;  // Image quality

// Streaming settings
static const int asyncModeDelayMs = 200;       // Async delay
```

**To connect to your server:**
In the app, enter your server IP (e.g., `192.168.1.10:8000`)

---

## 📱 App Features

### Main Screen Controls:
- 📍 **Server Address input** - Enter server IP
- 🔌 **Connect button** - Test connection
- 🔘 **Mode selection** - Choose Sync or Async
- ▶️ **Start button** - Begin streaming
- ⏹️ **Stop button** - End streaming
- 📊 **Status display** - Connection & streaming status
- 📈 **Statistics** - Counter of IMU samples and frames sent

---

## 🚀 Common Development Tasks

### View Live Logs
```bash
flutter logs
```

### Hot Reload (Update Code Without Restart)
1. Save your code
2. Press `r` in the terminal
3. Changes appear immediately!

### Hot Restart (Full App Restart)
```bash
# Press R in terminal (instead of r)
# Or manually:
flutter run --hot-restart
```

### Format Code
```bash
dart format lib/
```

### Check for Code Issues
```bash
flutter analyze
```

### Run Tests
```bash
flutter test
```

### Clean Build (When Things Break)
```bash
flutter clean
rm pubspec.lock
flutter pub get
flutter run
```

---

## 🌐 Server Connection

### Getting Your Server IP

**Windows** (PowerShell):
```bash
ipconfig
# Look for IPv4 Address (usually 192.168.x.x)
```

**macOS/Linux**:
```bash
ifconfig
# Look for inet (192.168.x.x)
```

### In the App
1. Enter your IP: `192.168.1.10:8000` (use your IP)
2. Tap "Connect to Server"
3. Watch status change to "Connected" ✓

### Testing Connection
```bash
# From your laptop, test the server is running
curl http://localhost:8000/health
```

---

## 📊 Data Format

### What Gets Sent to Server

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
  "data": "base64_encoded_jpeg_bytes",
  "mode": "sync"
}
```

---

## 🔐 Permissions

The app requests:
- **Camera**: To capture video frames
- **Sensors**: To access accelerometer & gyroscope
- **Microphone**: For camera functionality

On Android, these are requested at runtime.
On iOS, add descriptions to `ios/Runner/Info.plist`.

---

## 🐛 Troubleshooting

### "Cannot connect to server"
- [ ] Is the server running? `curl http://your-ip:8000/health`
- [ ] Are both devices on the same WiFi?
- [ ] Did you enter the correct IP? Check with `ipconfig`
- [ ] Is the port 8000 open in firewall?

### "Camera permission denied"
- **Android**: Settings > Apps > ETA-Sync > Permissions > Camera > ON
- **iOS**: Settings > Privacy > Camera > Enable ETA-Sync

### "Build errors"
```bash
flutter clean
rm pubspec.lock
flutter pub get
flutter run
```

### "Hot reload not working"
```bash
# Do a full restart instead
flutter run --hot-restart
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| [INDEX.md](INDEX.md) | Navigation guide (this project) |
| [QUICK_START.md](QUICK_START.md) | 5-min quick start |
| [SETUP.md](SETUP.md) | Detailed setup instructions |
| [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) | Architecture & code details |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | What was built |
| [README.md](README.md) | Main project documentation |

**Start with**: QUICK_START.md then CODE_DOCUMENTATION.md

---

## 🏗️ How the Code Works

### Flow When You Click "Start Streaming":

```
You click Start Streaming
    ↓
HomeScreen._startStreaming() method runs
    ↓
SensorService starts emitting IMU data
CameraService starts capturing frames
    ↓
For each IMU reading:
  - Create ImuData object
  - Convert to JSON
  - ApiService sends to /imu endpoint
  - Update UI counter
    ↓
For each camera frame:
  - Encode frame to base64
  - ApiService sends to /frame endpoint
  - Update UI counter
```

### In Async Mode:
IMU data is delayed by 200ms before sending (to simulate asynchronous sensors).

---

## 🎓 Key Classes to Know

| Class | File | What It Does |
|-------|------|--------------|
| `HomeScreen` | home_screen.dart | The UI you see |
| `SensorService` | sensor_service.dart | Reads IMU sensors |
| `CameraService` | camera_service.dart | Captures camera frames |
| `ApiService` | api_service.dart | Sends data to server |
| `ImuData` | imu_data.dart | Package for sensor data |

Each service is a **singleton** - only one active instance at a time.

---

## 💡 Pro Developer Tips

1. **Always run `flutter doctor`** before starting development
2. **Use hot reload** (press `r`) to save time during development
3. **Check logs** with `flutter logs` when debugging
4. **Test on real device** - emulator can be slower
5. **Clear cache** with `flutter clean` when stuff breaks mysteriously
6. **Use verbose mode** for detailed error info: `flutter run -v`

---

## 🚢 Ready to Deploy?

### For Testing:
```bash
flutter run --profile  # Release mode with profiling
```

### For Production:
```bash
# Android APK
flutter build apk --release

# Android App Bundle (for Play Store)
flutter build appbundle --release

# iOS (requires developer account)
flutter build ios --release
```

---

## 🔗 Quick Links

- [Flutter Docs](https://flutter.dev/docs)
- [Dart Guide](https://dart.dev/guides)
- [sensors_plus Package](https://pub.dev/packages/sensors_plus)
- [camera Package](https://pub.dev/packages/camera)

---

## 📋 Pre-Coding Checklist

- [ ] Fluttersdk installed
- [ ] All dependencies installed (`flutter pub get`)
- [ ] JSON code generated (`flutter pub run build_runner build`)
- [ ] Device/emulator connected (`flutter devices`)
- [ ] Read QUICK_START.md
- [ ] App runs successfully (`flutter run`)

---

## ❓ Common Questions

**Q: Where do I change the server IP?**
A: In the app UI itself! Enter it in the "Server Address" field.

**Q: How do I change the sampling rate?**
A: Edit `lib/config/app_config.dart` and set `imuSamplingRateHz`.

**Q: Can I use a real device instead of emulator?**
A: Yes! Connect it, run `flutter devices`, then `flutter run`.

**Q: What if the camera isn't working?**
A: Check app logs with `flutter logs`. Usually a permission issue.

**Q: How do I see what data is being sent?**
A: Run `flutter logs` in another terminal while the app is streaming.

---

## 🎯 Next Steps

1. ✅ Run the app with `flutter run`
2. 📖 Read [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) to understand the architecture
3. 🔍 Browse `home_screen.dart` to see how the UI works
4. 📝 Modify `app_config.dart` to customize settings
5. 🚀 Connect to your server and collect data!

---

**Welcome to the team! Happy coding!** 🚀

💬 **Questions?** Check the documentation files or review the source code comments.

---

**Last Updated**: March 2026 | **For**: ETA-Sync Mobile App v1.0.0
