# ETA-Sync: DTW-Guided Cross-Attention for Asynchronous Multi-Sensor Alignment

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Flutter](https://img.shields.io/badge/Flutter-3.0+-blue.svg)](https://flutter.dev)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-critical.svg)](https://fastapi.tiangolo.com/)

## 📋 Project Overview

**ETA-Sync** is an innovative system designed to capture and synchronize multi-sensor data streams from mobile devices with a centralized server. The system combines real-time IMU (Inertial Measurement Unit) sensor data and camera frames from a Flutter mobile application with a FastAPI server backend.

The primary purpose is to build a comprehensive dataset for training deep learning models that leverage **Dynamic Time Warping (DTW)** and **Cross-Attention mechanisms** to achieve robust temporal alignment between asynchronous multi-sensor inputs.

### Key Objectives
- Capture synchronized IMU (accelerometer + gyroscope) and camera data from mobile devices
- Stream data in real-time with flexible synchronous and asynchronous modes
- Persist sensor data with precise timestamps for post-hoc analysis
- Enable research in multi-modal sensor fusion and temporal alignment
- Support model training for temporal synchronization tasks

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ETA-Sync Architecture                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐                ┌──────────────────────┐
│   Flutter Mobile App     │                │   FastAPI Server     │
│  ┌────────────────────┐  │                │  ┌────────────────┐  │
│  │  IMU Sensors       │  │                │  │  Data Storage  │  │
│  │  • Accelerometer   │  │    HTTP/WS     │  │  (JSON/DB)     │  │
│  │  • Gyroscope       │  ├───────────────>│  │                │  │
│  │                    │  │                │  │  API Endpoints │  │
│  │  Camera Frame      │  │                │  │  • Stream      │  │
│  │  (Video Stream)    │  │                │  │  • Store       │  │
│  └────────────────────┘  │                │  │  • Retrieve    │  │
│                          │                │  │  • Switch Mode │  │
│  ┌────────────────────┐  │                │  └────────────────┘  │
│  │  Synchronous Mode  │  │                │                      │
│  │  (Timed intervals) │  │                │  ┌────────────────┐  │
│  │                    │  │                │  │  DTW + Cross-  │  │
│  │  Asynchronous Mode │  │                │  │  Attention     │  │
│  │  (Event-driven)    │  │                │  │  Model Training│  │
│  └────────────────────┘  │                │  └────────────────┘  │
└──────────────────────────┘                └──────────────────────┘
```

---

## ✨ Features

### Mobile Application (Flutter)
- ✅ **Real-time IMU Data Capture**: Access device accelerometer and gyroscope sensors
- ✅ **Camera Frame Streaming**: Capture and transmit video frames to the server
- ✅ **Dual Streaming Modes**:
  - **Synchronous Mode**: Fixed-interval data collection
  - **Asynchronous Mode**: Event-driven, on-demand streaming
- ✅ **Timestamp Precision**: Microsecond-level timestamp resolution
- ✅ **User-Friendly UI**: Simple controls for starting/stopping data collection
- ✅ **Connection Status Monitoring**: Real-time server connectivity feedback
- ✅ **Configurable Parameters**: Adjust sampling rates and streaming intervals

### Server Backend (FastAPI)
- ✅ **High-Performance Data Reception**: Asynchronous request handling with FastAPI
- ✅ **Multi-modal Data Storage**: Persistent storage of sensor and camera data
- ✅ **RESTful API**: Clean, intuitive endpoints for data management
- ✅ **WebSocket Support**: Real-time bidirectional communication
- ✅ **Data Export**: Download collected datasets in standardized formats
- ✅ **Session Management**: Track and organize data by collection sessions
- ✅ **CORS Enabled**: Cross-origin support for flexible client deployment

### Dataset & Model Training
- ✅ **Standardized Data Format**: JSON-based storage for easy integration
- ✅ **Temporal Alignment**: DTW-based sequence alignment capability
- ✅ **Cross-Attention Ready**: Model architecture support for attention mechanisms
- ✅ **Validation Support**: Train/test/validation split utilities

---

## 🛠️ Tech Stack

### Frontend (Mobile)
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Flutter | 3.0+ |
| Language | Dart | 2.18+ |
| Sensors | `sensors_plus` | Latest |
| Camera | `camera` | Latest |
| HTTP Client | `http` / `web_socket_channel` | Latest |

### Backend (Server)
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.100+ |
| Server | Uvicorn | 0.20+ |
| Language | Python | 3.9+ |
| Async | asyncio | Built-in |
| Database | SQLite/PostgreSQL | Optional |
| Data Science | NumPy, Pandas | Latest |

### Supporting Libraries
| Purpose | Library |
|---------|---------|
| Temporal Alignment | `dtaidistance` |
| Machine Learning | PyTorch / TensorFlow |
| Data Processing | NumPy, SciPy |
| Visualization | Matplotlib, Plotly |

---

## 📁 Project Structure

```
eta_sync_app/
├── lib/                          # Flutter application source code
│   ├── main.dart                # Application entry point
│   ├── screens/                 # UI screens
│   ├── services/                # API communication & sensor services
│   ├── models/                  # Data models
│   └── widgets/                 # Reusable UI components
│
├── android/                      # Android native code
├── ios/                          # iOS native code
├── linux/                        # Linux desktop support
├── macos/                        # macOS desktop support
├── windows/                      # Windows desktop support
│
├── pubspec.yaml                 # Flutter dependencies
├── analysis_options.yaml        # Dart code analysis config
└── README.md                    # This file

server/                           # (Recommended structure)
├── main.py                      # FastAPI application entry
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── routes.py           # API endpoint definitions
│   │   └── models.py           # Pydantic request/response models
│   ├── services/
│   │   ├── sensor_service.py   # Sensor data handling
│   │   └── storage_service.py  # Data persistence
│   └── config.py               # Configuration management
├── data/                        # Collected dataset storage
├── requirements.txt             # Python dependencies
└── README.md                    # Server documentation
```

---

## 📱 Mobile Application (Flutter) Description

The Flutter mobile application serves as the data acquisition frontend for the ETA-Sync system.

### Key Components

**Main Features:**
- **Sensor Integration**: Uses `sensors_plus` package to access device IMU sensors (accelerometer, gyroscope)
- **Camera Module**: Captures video frames at configurable frame rates
- **Network Communication**: Establishes HTTP/WebSocket connections to the FastAPI server
- **Data Buffering**: Maintains efficient in-memory buffers for sensor streams
- **UI Controls**: Intuitive interface for starting/stopping data collection and mode selection

**Streaming Modes:**
1. **Synchronous Mode**: Collects and sends sensor data at fixed intervals (e.g., 100ms)
2. **Asynchronous Mode**: Sends data on-demand when significant sensor changes are detected

### Configuration
- **Sampling Rate**: 
Adjustable IMU sampling frequency (default: 100 Hz)
- **Frame Rate**: Camera frame capture rate (default: 30 FPS)
- **Server Address**: Configurable server endpoint URL
- **Batch Size**: Number of sensor readings per transmission

---

## 🖥️ FastAPI Server Description

The FastAPI server handles data reception, validation, storage, and model training support.

### Core Functionality

**Data Reception & Storage:**
- Receives sensor data and camera frames in a structured JSON format
- Validates incoming data for completeness and temporal consistency
- Persists data to disk with original timestamps
- Organizes data into sessions for better dataset management

**API Services:**
- RESTful endpoints for data management and retrieval
- WebSocket support for real-time streaming
- Session endpoint for creating and managing collection sessions
- Export endpoints for downloading collected datasets

**Processing Pipeline:**
- Data validation and normalization
- Temporal alignment preprocessing
- Dataset splitting for train/test/validation
- Optional on-the-fly preprocessing and augmentation

---

## 📊 Data Streaming Workflow

### Synchronous Streaming Flow

```
Mobile App                          Server
    │                                 │
    ├─ Collect sensor data (T=100ms)──┤
    │                                 ├─ Receive & validate
    ├─ Append camera frame────────────┤
    │                                 ├─ Store to DB/file
    ├─ Send JSON batch ─────────────→ │
    │                                 ├─ Return confirmation
    ├─ Receive ACK ←────────────────┤
    │                                 │
    └─ Repeat every Δt ──────────────┘
```

### Asynchronous Streaming Flow

```
Mobile App                          Server
    │                                 │
    ├─ Monitor sensor changes ───────┤
    │                                 │
    ├─ Significant event detected ───┤
    │                                 ├─ Receive
    ├─ Send data (on-demand) ────────→│
    │                                 ├─ Validate & store
    │                                 
    ├─ Continue monitoring ──────────┤
    │                                 
    └─ Send on next trigger ────────→│
```

### Data Packet Format (JSON)

```json
{
  "session_id": "session_20260307_143022",
  "timestamp": 1709874022.123456,
  "mode": "synchronous",
  "sensor_data": {
    "accelerometer": [0.12, 0.034, 9.81],
    "gyroscope": [0.001, 0.0002, 0.0015]
  },
  "camera_frame": {
    "frame_id": 1234,
    "encoded_data": "base64_encoded_jpeg",
    "resolution": "640x480"
  }
}
```

---

## 🚀 Installation Instructions

### Prerequisites

**For Mobile Development:**
- Flutter SDK (3.0 or higher)
- Dart SDK (2.18 or higher)
- Android Studio or Xcode (platform-specific)
- A physical device or emulator

**For Server Development:**
- Python 3.9 or higher
- pip package manager
- Virtual environment tool (venv or conda)

### Mobile App Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/eta-sync.git
   cd eta_sync_app
   ```

2. **Install Flutter Dependencies**
   ```bash
   flutter pub get
   ```

3. **Configure Server Address**
   - Edit `lib/config/server_config.dart`
   - Set your server URL: `const String SERVER_URL = 'http://your-server-ip:8000';`

4. **Build for Target Platform**
   
   **Android:**
   ```bash
   flutter build apk --release
   flutter install
   ```
   
   **iOS:**
   ```bash
   flutter build ios
   # Then open in Xcode for further configuration
   ```

### Server Setup

1. **Create Project Directory**
   ```bash
   mkdir eta-sync-server
   cd eta-sync-server
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create Required Directories**
   ```bash
   mkdir -p data/sessions
   mkdir -p logs
   ```

5. **Configure Environment Variables**
   - Create `.env` file with:
     ```
     SERVER_HOST=0.0.0.0
     SERVER_PORT=8000
     DEBUG=False
     DATA_STORAGE_PATH=./data
     DATABASE_URL=sqlite:///./eta_sync.db
     ```

---

## 🏃 Running the Server

### Development Mode

```bash
# With auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# With Gunicorn for multiple workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

### Verify Server is Running
- Check: `http://localhost:8000/docs` (Interactive API documentation)
- Health check: `http://localhost:8000/health`

---

## 📲 Running the Flutter App

### Development Mode

```bash
# Run on connected device/emulator
flutter run

# Run with verbose output
flutter run -v
```

### Release Build

**Android:**
```bash
flutter build apk --release
flutter install --release
```

**iOS:**
```bash
flutter build ios --release
```

### Testing
```bash
# Run unit tests
flutter test

# Run integration tests
flutter drive --target=test_driver/app.dart
```

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### Authentication & Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions/create` | Create a new data collection session |
| `GET` | `/sessions/{session_id}` | Retrieve session metadata |
| `GET` | `/sessions/list` | List all sessions |
| `DELETE` | `/sessions/{session_id}` | Delete a session |

#### Data Streaming
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/data/stream` | Receive sensor and camera data |
| `GET` | `/data/{session_id}` | Retrieve data for a session |
| `POST` | `/data/switch-mode` | Switch between sync/async mode |

#### Model Training
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dataset/export` | Export dataset for training |
| `POST` | `/dataset/split` | Create train/test/val splits |
| `GET` | `/align/dtw` | Perform DTW alignment |

#### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Server health check |
| `GET` | `/status` | Current server status |

### Example Requests

**Create Session:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"device_id": "mobile_001", "mode": "synchronous"}'
```

**Stream Sensor Data:**
```bash
curl -X POST http://localhost:8000/api/v1/data/stream \
  -H "Content-Type: application/json" \
  -d @data_packet.json
```

---

## 📦 Dataset Format

### Directory Structure
```
dataset/
├── sessions/
│   ├── session_20260307_143022/
│   │   ├── metadata.json
│   │   ├── sensor_data.jsonl
│   │   ├── camera_frames/
│   │   │   ├── frame_0001.jpg
│   │   │   ├── frame_0002.jpg
│   │   │   └── ...
│   │   └── alignment/
│   │       ├── dtw_alignment.json
│   │       └── attention_weights.npy
│   └── ...
├── train/
├── test/
└── validation/
```

### Metadata Format (metadata.json)
```json
{
  "session_id": "session_20260307_143022",
  "device_id": "mobile_001",
  "start_time": 1709874022.123456,
  "end_time": 1709874082.654321,
  "duration_seconds": 60.531,
  "mode": "synchronous",
  "sampling_rate_hz": 100,
  "camera_fps": 30,
  "total_sensor_samples": 6053,
  "total_frames": 1813,
  "timezone": "UTC"
}
```

### Sensor Data Format (sensor_data.jsonl)
```jsonl
{"timestamp": 1709874022.123456, "accel": [0.12, 0.034, 9.81], "gyro": [0.001, 0.0002, 0.0015]}
{"timestamp": 1709874022.213456, "accel": [0.11, 0.035, 9.82], "gyro": [0.001, 0.0003, 0.0014]}
```

---

## 🎬 Demo Instructions

### Quick Start Demo

1. **Start the Server**
   ```bash
   cd server
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Launch the Mobile App**
   ```bash
   cd eta_sync_app
   flutter run
   ```

3. **Create a Session**
   - Open the app
   - Tap "New Session"
   - Select "Synchronous Mode"
   - Enter device ID and optional notes

4. **Collect Data**
   - Tap "Start Collection"
   - Move your device in various patterns
   - Rotate it in different axes
   - App should show real-time sensor values

5. **Stop and Export**
   - Tap "Stop Collection"
   - Data is automatically saved
   - View session on server dashboard

6. **Verify Data**
   ```bash
   curl http://localhost:8000/api/v1/sessions/list
   ```

### Advanced Demo: DTW Alignment

```python
# Python script to perform alignment
from server.services.alignment import DTWAligner
import json

# Load session data
with open('data/sessions/session_xxx/sensor_data.jsonl') as f:
    data = [json.loads(line) for line in f]

# Perform alignment
aligner = DTWAligner()
alignment = aligner.align(data)

# Save results
with open('data/sessions/session_xxx/alignment/dtw_alignment.json', 'w') as f:
    json.dump(alignment, f)
```

---

## 🔮 Future Improvements

### Planned Features
- [ ] **Real-time Visualization**: Live plotting of sensor data on server dashboard
- [ ] **Multi-device Synchronization**: Sync data from multiple mobile devices
- [ ] **Edge Processing**: On-device preprocessing and compression
- [ ] **Offline Mode**: Capture data offline and sync when connection available
- [ ] **Advanced UI**: 3D visualization of device orientation using gyroscope data
- [ ] **Authentication**: User authentication and cloud storage integration
- [ ] **Web Dashboard**: Real-time monitoring interface for server backend
- [ ] **Model Integration**: On-server training and evaluation pipeline
- [ ] **Benchmarking Tools**: Performance metrics and latency analysis
- [ ] **ROS Integration**: Support for Robot Operating System for robotics projects

### Research Directions
- Exploration of different attention mechanisms for temporal alignment
- Comparison with state-of-the-art temporal alignment methods
- Application to gesture recognition and activity classification
- Cross-modal fusion of IMU and vision data
- Lightweight models for on-device deployment

---

## 👥 Contributors

- **Project Lead**: [Your Name]
- **Mobile Development**: [Contributor Names]
- **Backend Development**: [Contributor Names]

### Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure:
- Code follows project style guidelines
- Tests are updated for new functionality
- Documentation is updated
- Commits have clear, descriptive messages

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support & Contact

- **Issues**: Please use the [GitHub Issues](https://github.com/yourusername/eta-sync/issues) page
- **Discussions**: Join our [GitHub Discussions](https://github.com/yourusername/eta-sync/discussions)
- **Email**: your-email@example.com

---

## 🙏 Acknowledgments

- Flutter and Dart teams for excellent mobile development tools
- FastAPI for providing an intuitive web framework
- The open-source community for invaluable libraries and tools

---

**Last Updated**: March 2026 | **Version**: 1.0.0
