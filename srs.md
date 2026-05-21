# Software Requirements Specification (SRS)

## ETA-Sync: Real-Time DTW-Guided Asynchronous Multi-Modal Fusion System

---

# Revision History

| Version | Date | Description       | Author                     |
| ------- | ---- | ----------------- | -------------------------- |
| 1.0     | 2026 | Initial SRS Draft | Siddharth Chaudhary et al. |

---

# Table of Contents

1. Introduction
2. Overall Description
3. System Features
4. External Interface Requirements
5. Non-Functional Requirements
6. System Architecture Constraints
7. Data Requirements
8. System Models
9. Assumptions and Dependencies
10. Future Scope

---

# 1. Introduction

## 1.1 Purpose

This Software Requirements Specification (SRS) document defines the functional and non-functional requirements for the implementation of ETA-Sync, a real-time asynchronous multi-modal sensor fusion system utilizing DTW-guided cross-attention.

The purpose of the system is to:

* Collect heterogeneous sensor streams from mobile and external devices.
* Stream asynchronous sensor data through WebSockets.
* Perform temporal alignment using Dynamic Time Warping (DTW).
* Execute DTW-guided neural cross-attention fusion.
* Visualize temporal alignment behavior and fusion outputs.
* Provide a research-oriented demonstration platform for asynchronous sensor fusion.

This document focuses exclusively on implementation requirements and system behavior. The internal mathematical working and research methodology are documented separately.

---

## 1.2 Scope

ETA-Sync is designed as a modular edge-oriented asynchronous sensor fusion framework capable of processing camera and IMU streams in real time.

The implementation includes:

* Mobile-based sensor acquisition.
* Real-time sensor streaming infrastructure.
* Backend AI inference engine.
* DTW-based alignment processing.
* Cross-attention fusion module.
* Visualization dashboard.
* WebSocket-based bidirectional communication.

The system is intended primarily for:

* academic demonstrations,
* research experimentation,
* asynchronous fusion analysis,
* visualization of temporal alignment behavior.

The implementation is not intended for commercial deployment, large-scale distributed infrastructure, or production-grade cloud scalability.

---

## 1.3 Definitions, Acronyms, and Abbreviations

| Term            | Description                                         |
| --------------- | --------------------------------------------------- |
| DTW             | Dynamic Time Warping                                |
| IMU             | Inertial Measurement Unit                           |
| AI              | Artificial Intelligence                             |
| API             | Application Programming Interface                   |
| GPU             | Graphics Processing Unit                            |
| CNN             | Convolutional Neural Network                        |
| WebSocket       | Full-duplex communication protocol                  |
| Cross-Attention | Transformer-based feature interaction mechanism     |
| Fusion          | Integration of heterogeneous sensor representations |
| Edge Device     | Resource-constrained local computing device         |

---

## 1.4 Intended Audience

This document is intended for:

* Project developers
* Research supervisors
* Academic evaluators
* Frontend developers
* Backend developers
* AI model developers
* System integrators

---

## 1.5 Development Environment

| Component            | Technology        |
| -------------------- | ----------------- |
| Frontend             | React / Next.js   |
| Mobile Application   | Flutter           |
| Backend              | FastAPI           |
| AI Framework         | PyTorch           |
| Communication        | WebSockets        |
| Visualization        | Plotly / Recharts |
| Video Processing     | OpenCV            |
| Numerical Processing | NumPy, SciPy      |
| DTW Library          | FastDTW           |

---

# 2. Overall Description

## 2.1 Product Perspective

ETA-Sync operates as a modular real-time asynchronous fusion pipeline.

The system architecture consists of:

1. Sensor Acquisition Layer
2. Data Streaming Layer
3. AI Processing Backend
4. Temporal Alignment Engine
5. Fusion Engine
6. Visualization Dashboard

The system processes asynchronous sensor streams using DTW-guided cross-attention and outputs aligned fusion representations in real time.

---

## 2.2 Product Functions

The system shall provide the following functionalities:

* Capture camera and IMU data.
* Stream sensor data through WebSockets.
* Accept external sensor sources.
* Buffer temporal sensor windows.
* Perform DTW temporal alignment.
* Generate DTW bias matrices.
* Execute cross-attention fusion.
* Output aligned fused streams.
* Visualize temporal alignment.
* Display attention heatmaps.
* Display robustness metrics.
* Display latency and synchronization statistics.

---

## 2.3 User Classes

| User Type     | Description                                |
| ------------- | ------------------------------------------ |
| Research User | Performs experimental analysis             |
| Presenter     | Uses the system for academic demonstration |
| Developer     | Maintains and extends the implementation   |
| Observer      | Views visualizations and outputs           |

---

## 2.4 Operating Environment

The system shall operate on:

| Component          | Environment                    |
| ------------------ | ------------------------------ |
| Backend Server     | Linux / Windows                |
| Frontend Dashboard | Modern Web Browser             |
| Mobile Application | Android                        |
| AI Inference       | NVIDIA GPU-enabled environment |

Minimum hardware requirements:

| Hardware | Requirement           |
| -------- | --------------------- |
| CPU      | Quad Core             |
| RAM      | 8 GB                  |
| GPU      | RTX 3050 or higher    |
| Storage  | 10 GB Available Space |

---

## 2.5 Design Constraints

The implementation shall:

* Maintain modular architecture.
* Use lightweight edge-compatible processing.
* Support asynchronous sensor streams.
* Use WebSockets for real-time communication.
* Avoid dependency on cloud infrastructure.
* Operate using short sliding temporal windows.

---

# 3. System Features

## 3.1 Mobile Sensor Acquisition

### Description

The mobile application shall capture camera and IMU sensor data.

### Functional Requirements

* FR-1: The system shall access the device camera.
* FR-2: The system shall access accelerometer data.
* FR-3: The system shall access gyroscope data.
* FR-4: The system shall timestamp sensor packets.
* FR-5: The application shall stream sensor data via WebSocket.
* FR-6: The application shall support configurable streaming rates.

---

## 3.2 WebSocket Streaming Layer

### Description

The backend shall support bidirectional streaming of sensor and fusion data.

### Functional Requirements

* FR-7: The backend shall expose WebSocket endpoints.
* FR-8: The backend shall accept multiple sensor sources.
* FR-9: The backend shall buffer temporal data windows.
* FR-10: The backend shall broadcast aligned output streams.
* FR-11: The system shall support real-time streaming.

---

## 3.3 Temporal Alignment Engine

### Description

The backend shall compute temporal correspondence using DTW.

### Functional Requirements

* FR-12: The backend shall compute DTW cost matrices.
* FR-13: The backend shall generate alignment paths.
* FR-14: The backend shall convert alignment outputs into bias matrices.
* FR-15: The backend shall support sliding-window DTW computation.

---

## 3.4 Cross-Attention Fusion Module

### Description

The AI backend shall perform DTW-guided cross-attention fusion.

### Functional Requirements

* FR-16: The backend shall generate feature embeddings.
* FR-17: The backend shall execute transformer cross-attention.
* FR-18: The backend shall inject DTW alignment priors.
* FR-19: The backend shall generate fused representations.
* FR-20: The backend shall output classification predictions.

---

## 3.5 Visualization Dashboard

### Description

The frontend dashboard shall visualize real-time fusion behavior using Next.js with shadcn/ui as the base UI library.

### Functional Requirements

* FR-21: The dashboard shall be implemented as a Next.js frontend.
* FR-22: The dashboard shall use shadcn/ui as the base component library.
* FR-23: The dashboard shall display live sensor streams.
* FR-24: The dashboard shall display DTW cost matrices.
* FR-25: The dashboard shall display attention heatmaps.
* FR-26: The dashboard shall display alignment paths.
* FR-27: The dashboard shall display latency metrics.
* FR-28: The dashboard shall display fusion confidence scores.
* FR-29: The dashboard shall display jitter robustness metrics.

---

# 4. External Interface Requirements

## 4.1 User Interfaces

The frontend dashboard shall provide:

* Real-time sensor visualization.
* Matrix heatmap visualization.
* Attention visualization.
* Stream status indicators.
* Latency graphs.
* Temporal synchronization metrics.
* A shadcn/ui-based component system for cards, dialogs, tables, tabs, sheets, and forms.

The dashboard shall maintain a research-oriented visualization design.

---

## 4.2 Hardware Interfaces

The system shall interface with:

* Smartphone camera
* Accelerometer sensor
* Gyroscope sensor
* GPU-enabled processing hardware

---

## 4.3 Software Interfaces

| Interface     | Purpose                 |
| ------------- | ----------------------- |
| FastAPI       | Backend services        |
| PyTorch       | AI inference            |
| OpenCV        | Video processing        |
| FastDTW       | Temporal alignment      |
| WebSocket API | Real-time communication |

---

## 4.4 Communication Interfaces

The system shall use:

* WebSockets for live streaming.
* JSON packet formatting.
* TCP/IP networking.

Example packet format:

```json
{
  "timestamp": 1712345678,
  "sensor": "imu",
  "ax": 0.12,
  "ay": 0.44,
  "az": 9.81
}
```

---

# 5. Non-Functional Requirements

## 5.1 Performance Requirements

| Requirement              | Target     |
| ------------------------ | ---------- |
| Sensor Streaming Latency | < 100 ms   |
| Fusion Inference Latency | < 50 ms    |
| Dashboard Refresh Rate   | 30 FPS     |
| WebSocket Availability   | Continuous |

---

## 5.2 Reliability Requirements

The system shall:

* Recover from temporary stream interruptions.
* Handle dropped sensor frames.
* Maintain stable WebSocket connections.
* Prevent backend crashes during malformed packet reception.

---

## 5.3 Scalability Requirements

The system shall support:

* Multiple sensor clients.
* Additional sensor modalities.
* Future lightweight transformer models.

---

## 5.4 Security Requirements

The implementation shall:

* Restrict unauthorized backend access.
* Validate incoming sensor packets.
* Prevent malformed packet injection.

No production-grade authentication infrastructure is required.

---

## 5.5 Maintainability Requirements

The implementation shall:

* Maintain modular architecture.
* Separate frontend and backend logic.
* Separate AI inference modules.
* Support independent component upgrades.

---

# 6. System Architecture Constraints

The implementation architecture shall maintain separation between:

* Data Acquisition Layer
* Streaming Layer
* Temporal Alignment Layer
* AI Fusion Layer
* Visualization Layer

The system shall avoid tightly coupled architecture.

---

# 7. Data Requirements

## 7.1 Input Data

| Data Type          | Source        |
| ------------------ | ------------- |
| Video Frames       | Mobile Camera |
| Accelerometer Data | Mobile IMU    |
| Gyroscope Data     | Mobile IMU    |
| Timestamps         | Device Clock  |

---

## 7.2 Output Data

| Output               | Description               |
| -------------------- | ------------------------- |
| DTW Cost Matrix      | Temporal alignment matrix |
| Attention Matrix     | Cross-modal attention map |
| Fused Representation | Aligned embedding vector  |
| Prediction Output    | Classification result     |
| Confidence Score     | Fusion certainty metric   |

---

# 8. System Models

## 8.1 High-Level Data Flow

```text
Mobile Sensors
      ↓
WebSocket Input Gateway
      ↓
Temporal Buffer Manager
      ↓
Feature Extraction
      ↓
DTW Alignment Engine
      ↓
DTW-Guided Cross-Attention
      ↓
Prediction Head
      ↓
Visualization Dashboard
```

---

## 8.2 Backend Processing Pipeline

```text
Sensor Streams
      ↓
Embedding Generation
      ↓
DTW Temporal Alignment
      ↓
Alignment Bias Matrix
      ↓
Cross-Attention Fusion
      ↓
Prediction Output
```

---

# 9. Assumptions and Dependencies

## 9.1 Assumptions

* Sensor timestamps are available.
* GPU acceleration is available.
* Network latency remains moderate.
* Mobile devices support IMU access.

---

## 9.2 Dependencies

The implementation depends on:

* PyTorch
* FastAPI
* OpenCV
* NumPy
* FastDTW
* Flutter SDK
* React / Next.js
* shadcn/ui

---

# 10. Future Scope

Potential future enhancements include:

* Differentiable DTW optimization.
* Adaptive temporal window sizing.
* Additional sensor modalities.
* Real-time edge deployment optimization.
* Federated asynchronous fusion.
* Multi-device synchronization.
* Lightweight transformer acceleration.

---

# End of Document
