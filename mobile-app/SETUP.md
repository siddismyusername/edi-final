# ETA-Sync Mobile App - Setup Guide

## Installation & Setup Instructions

This guide will help you set up and run the ETA-Sync Flutter mobile application.

### Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Flutter SDK**: Download from [flutter.dev](https://flutter.dev/docs/get-started/install)
   - Verify installation: `flutter --version`
   - Run `flutter doctor` to check for any missing dependencies

2. **Dart SDK**: Usually comes with Flutter, verify with `dart --version`

3. **Android Development** (for Android builds):
   - Android Studio
   - Android SDK (API 21+)
   - Gradle

4. **iOS Development** (for iOS builds):
   - Xcode 13.0+
   - CocoaPods: `sudo gem install cocoapods`

5. **Git**: For version control

### Project Structure

```
eta_sync_app/
├── lib/
│   ├── main.dart                 # Application entry point
│   ├── screens/
│   │   └── home_screen.dart     # Main UI with controls
│   ├── services/
│   │   ├── api_service.dart     # Server communication
│   │   ├── camera_service.dart  # Camera frame capture
│   │   └── sensor_service.dart  # IMU sensor data collection
│   └── models/
│       └── imu_data.dart         # IMU data model
├── pubspec.yaml                  # Project dependencies
├── android/                       # Android native files
├── ios/                          # iOS native files
└── test/                         # Test files
```

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/eta-sync.git
cd eta_sync_app
```

### Step 2: Install Flutter Dependencies

```bash
flutter pub get
```

This command downloads and installs all dependencies specified in `pubspec.yaml`.

### Step 3: Generate JSON Serialization Code

This project uses `json_serializable` for model serialization. Generate the required files:

```bash
flutter pub run build_runner build
```

Or use watch mode for continuous generation:

```bash
flutter pub run build_runner watch
```

### Step 4: Configure Your Device

#### For Android Emulator:
```bash
flutter emulators --launch Pixel_5_API_30
```

#### For Physical Android Device:
1. Enable USB Debugging on your Android device
2. Connect the device via USB
3. Verify connection: `flutter devices`

#### For iOS Simulator:
```bash
open -a Simulator
```

#### For Physical iOS Device:
1. Connect device via USB
2. Trust the computer on your device
3. Verify connection: `flutter devices`

### Step 5: Run the Application

#### Basic Run:
```bash
flutter run
```

#### Run with Verbose Output (for debugging):
```bash
flutter run -v
```

#### Specify a Target Device:
```bash
flutter run -d <device_id>
```

### Step 6: Configure the Server Address

1. Open the app on your device/emulator
2. Find your FastAPI server's IP address:
   ```bash
   # On Windows (in PowerShell):
   ipconfig
   
   # On macOS/Linux:
   ifconfig
   ```
   Look for the IPv4 address (usually 192.168.x.x or 10.x.x.x)

3. In the app, enter the server URL in format: `192.168.1.10:8000`

4. Tap "Connect to Server" to test the connection

### Building for Distribution

#### Android APK:
```bash
flutter build apk --release
```
Output: `build/app/outputs/flutter-apk/app-release.apk`

#### Android App Bundle (for Google Play):
```bash
flutter build appbundle --release
```
Output: `build/app/outputs/bundle/release/app-release.aab`

#### iOS (requires developer account):
```bash
flutter build ios --release
```
Then open in Xcode: `open ios/Runner.xcworkspace`

### Troubleshooting

#### 1. Camera Permission Denied
- **Android**: Go to Settings > Apps > ETA-Sync > Permissions > Enable Camera
- **iOS**: Go to Settings > Privacy > Camera > Enable ETA-Sync

#### 2. Sensor Permission Denied
- **Android**: Go to Settings > Apps > ETA-Sync > Permissions > Enable Sensors
- **iOS**: Sensors are usually enabled by default

#### 3. Cannot Connect to Server
- Ensure both devices are on the same WiFi network
- Check firewall settings to allow port 8000
- Verify the IPv4 address is correct
- Test connectivity: `ping <server_ip>`
- Check server logs to see if it's receiving requests

#### 4. Camera Not Initializing
- Ensure at least one camera is available on the device
- Check camera permissions (see #1)
- Try restarting the app
- On Android, some devices may have issues; try upgrading the camera package

#### 5. Build Errors
```bash
# Clean the build cache
flutter clean

# Regenerate pubspec.lock
rm pubspec.lock
flutter pub get

# Rebuild JSON files
flutter pub run build_runner clean
flutter pub run build_runner build

# Run again
flutter run
```

#### 6. Hot Reload Issues
If hot reload/restart doesn't work:
1. Stop the running app (press `q` in terminal)
2. Run `flutter clean`
3. Run `flutter run` again

### Development Tips

#### Enable Debug Logging:
The app includes debug print statements. View logs with:
```bash
flutter logs
```

#### Run Tests:
```bash
flutter test
```

#### Format Code:
```bash
dart format lib/
```

#### Analyze Code Quality:
```bash
flutter analyze
```

### Project Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sensors_plus | ^1.4.0 | IMU sensor access |
| camera | ^0.10.0 | Camera frame capture |
| http | ^1.1.0 | HTTP requests to server |
| permission_handler | ^11.4.0 | Runtime permission management |
| image | ^4.0.0 | Image processing and JPEG encoding |
| json_annotation | ^4.8.0 | JSON serialization support |
| async | ^2.11.0 | Async utilities |

### API Integration

The app sends data to these endpoints:

- **`POST /imu`**: Send IMU sensor data
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

- **`POST /frame`**: Send camera frames
  ```json
  {
    "timestamp": 1709874022.123456,
    "frame_id": 1234,
    "resolution": "640x480",
    "data": "<base64_encoded_jpeg>",
    "mode": "sync"
  }
  ```

- **`GET /health`**: Health check endpoint

### Environment Configuration

Create a `.env` file in the project root (optional):

```
SERVER_HOST=192.168.1.10
SERVER_PORT=8000
DEBUG=true
```

Then use `flutter_dotenv` to load these values (requires additional setup).

### Performance Optimization

1. **Reduce Camera Resolution**: Lower resolution = faster processing
2. **Adjust Sampling Rate**: Decrease IMU sampling frequency if needed
3. **Batch Data**: Send multiple readings in one request
4. **Release Build**: Use `--release` flag for production

### Next Steps

1. **Test Connection**: Verify app can communicate with server
2. **Collect Data**: Use the app to collect IMU and camera data
3. **Analyze Data**: Review collected datasets in server storage
4. **Train Models**: Use collected data for DTW/attention model training

### Additional Resources

- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Language Guide](https://dart.dev/guides)
- [sensors_plus Package](https://pub.dev/packages/sensors_plus)
- [camera Package](https://pub.dev/packages/camera)
- [HTTP Package](https://pub.dev/packages/http)

### Support

For issues or questions:
1. Check the troubleshooting section above
2. Review app logs: `flutter logs`
3. Check GitHub issues: [github.com/yourusername/eta-sync/issues](https://github.com)
4. Enable verbose mode: `flutter run -v`

### License

This project is licensed under the MIT License - see the LICENSE file for details.
