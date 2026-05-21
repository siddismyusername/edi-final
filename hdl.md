````markdown
# High-Level Design (HLD)

# ETA-Sync Research Prototype

---

# Revision History

| Version | Date | Description | Author |
|---|---|---|---|
| 1.0 | 2026 | Initial HLD Draft | Siddharth Chaudhary et al. |

---

# Table of Contents

1. Introduction  
2. Design Goals  
3. Architectural Overview  
4. Layer Definitions  
5. System Boundary Decisions  
6. Session Lifecycle  
7. Data Flow Architecture  
8. Storage and Artifact Model  
9. Major Interfaces  
10. Windowing Strategy  
11. Failure Handling Strategy  
12. Design Constraints  
13. Anti-Drift Rules  
14. Traceability Snapshot  
15. Deliverable Outcome  

---

# 1. Introduction

This High-Level Design (HLD) document defines the architectural structure of ETA-Sync, a research-oriented asynchronous multi-modal sensor fusion prototype utilizing DTW-guided cross-attention.

The purpose of this document is to establish stable architectural boundaries before implementation begins. The HLD defines:

- system layers,
- ownership responsibilities,
- data flow,
- interface boundaries,
- artifact generation,
- operational constraints.

This document intentionally avoids low-level implementation details and internal algorithmic derivations, which are documented separately.

---

# 2. Design Goals

ETA-Sync shall:

- Collect asynchronous camera and IMU data from a mobile client.
- Stream sensor packets to a backend in real time.
- Persist raw and derived session artifacts.
- Compute DTW alignment over sliding temporal windows.
- Generate DTW-derived temporal bias matrices.
- Inject temporal priors into cross-attention fusion.
- Produce aligned fused representations.
- Expose diagnostic metrics and visualizations.
- Maintain modular research-oriented architecture.
- Support lightweight edge-compatible deployment.

---

# 3. Architectural Overview

The ETA-Sync architecture is organized into six major layers:

1. Data Acquisition Layer  
2. Streaming Layer  
3. Storage Layer  
4. Temporal Alignment Layer  
5. AI Fusion Layer  
6. Visualization Layer  

Each layer owns a clearly isolated responsibility domain.

---

# 4. Layer Definitions

## 4.1 Data Acquisition Layer

### Responsibilities

- Capture camera frames.
- Capture accelerometer readings.
- Capture gyroscope readings.
- Timestamp packets at the source.
- Normalize outgoing payload structure.
- Stream packets to backend services.

### Primary Technology

- Flutter mobile application

### Output Artifacts

- Serialized sensor packets
- Camera frame payloads
- IMU payload streams

---

## 4.2 Streaming Layer

### Responsibilities

- Accept REST requests.
- Accept WebSocket streams.
- Validate packet structure.
- Manage active sessions.
- Buffer temporal windows.
- Forward packets to downstream systems.

### Primary Technology

- FastAPI backend

### Output Artifacts

- Session buffers
- Validated sensor streams
- Stream health metrics

---

## 4.3 Storage Layer

### Responsibilities

- Persist raw sensor packets.
- Persist DTW matrices.
- Persist attention matrices.
- Persist fused outputs.
- Persist prediction results.
- Store session metadata.
- Support replay and inspection workflows.

### Storage Scope

The storage layer exists strictly for:

- reproducibility,
- debugging,
- offline analysis,
- research traceability.

### Output Artifacts

- Session archives
- Matrix artifacts
- Prediction logs
- Diagnostic metrics

---

## 4.4 Temporal Alignment Layer

### Responsibilities

- Construct DTW cost matrices.
- Generate alignment paths.
- Compute temporal correspondence maps.
- Produce normalized DTW bias matrices.
- Expose deterministic alignment outputs.

### Core Objective

Provide temporally plausible alignment priors for asynchronous fusion.

### Output Artifacts

- DTW cost matrices
- Alignment paths
- DTW bias matrices
- Temporal correspondence maps

---

## 4.5 AI Fusion Layer

### Responsibilities

- Generate sensor embeddings.
- Project embeddings into query, key, and value spaces.
- Execute DTW-guided cross-attention.
- Generate fused representations.
- Produce prediction outputs.
- Generate confidence metrics.

### Internal Subsystems

```text
Feature Extraction
      ↓
Embedding Projection
      ↓
DTW-Guided Attention
      ↓
Prediction Head
````

### Output Artifacts

* Attention matrices
* Fused embeddings
* Prediction outputs
* Confidence scores

---

## 4.6 Visualization Layer

### Responsibilities

* Display stream health.
* Render DTW heatmaps.
* Render alignment paths.
* Display attention diagnostics.
* Display latency metrics.
* Display prediction confidence.
* Present research-oriented dashboards.

### Primary Technology

* Next.js frontend
* shadcn/ui
* Plotly / Recharts

### Design Philosophy

The visualization layer shall remain:

* diagnostic,
* observational,
* read-only.

---

# 5. System Boundary Decisions

The following architectural boundaries are fixed to prevent implementation drift.

## Fixed Boundaries

* The mobile client shall not perform DTW computation.
* The mobile client shall not perform AI inference.
* The backend shall own all alignment logic.
* The backend shall own all fusion logic.
* The backend shall own persistence and session management.
* The dashboard shall remain a read-only consumer.
* Visualization logic shall not modify alignment state.
* Visualization logic shall not modify model state.

## Ownership Isolation

| Layer               | Ownership Scope         |
| ------------------- | ----------------------- |
| Mobile Layer        | Sensor acquisition only |
| Streaming Layer     | Transport and buffering |
| Storage Layer       | Persistence only        |
| Temporal Layer      | Alignment logic         |
| AI Layer            | Fusion and prediction   |
| Visualization Layer | Display and diagnostics |

---

# 6. Session Lifecycle

ETA-Sync operates using session-oriented processing.

## Session States

| State       | Description                      |
| ----------- | -------------------------------- |
| Initialized | Session created                  |
| Streaming   | Sensor packets actively received |
| Processing  | Alignment and fusion active      |
| Completed   | Session finalized                |
| Archived    | Session persisted for replay     |

## Session Responsibilities

Each session shall maintain:

* packet buffers,
* temporal windows,
* matrix artifacts,
* prediction outputs,
* diagnostic metadata.

---

# 7. Data Flow Architecture

## 7.1 High-Level Flow

```text
Mobile Sensors
      ↓
Packet Serialization
      ↓
REST/WebSocket Ingestion
      ↓
Session Buffer
      ↓
DTW Alignment
      ↓
Bias Matrix Generation
      ↓
Cross-Attention Fusion
      ↓
Prediction + Diagnostics
      ↓
Visualization Dashboard
```

---

## 7.2 AI Processing Flow

```text
Sensor Streams
      ↓
Feature Extraction
      ↓
Embedding Generation
      ↓
DTW Temporal Alignment
      ↓
Bias Matrix Construction
      ↓
Cross-Attention Fusion
      ↓
Prediction Generation
```

---

# 8. Storage and Artifact Model

## 8.1 Raw Artifacts

| Artifact         | Description                          |
| ---------------- | ------------------------------------ |
| Camera Frames    | Raw visual input                     |
| IMU Streams      | Accelerometer and gyroscope readings |
| Session Metadata | Session descriptors                  |

---

## 8.2 Derived Artifacts

| Artifact          | Description                   |
| ----------------- | ----------------------------- |
| DTW Cost Matrix   | Temporal alignment matrix     |
| Alignment Path    | DTW optimal path              |
| Bias Matrix       | Normalized temporal prior     |
| Attention Matrix  | Cross-modal attention weights |
| Fused Embeddings  | Final aligned representations |
| Prediction Output | Classification results        |
| Latency Metrics   | Timing diagnostics            |

---

# 9. Major Interfaces

## 9.1 Mobile to Backend Interfaces

### Interfaces

* Health check endpoint
* Session initialization endpoint
* Sensor stream endpoint
* Camera frame endpoint
* Session metadata endpoint

### Communication Protocol

* REST
* WebSocket

---

## 9.2 Backend to Dashboard Interfaces

### Interfaces

* Session status feed
* DTW matrix feed
* Attention diagnostics feed
* Prediction feed
* Latency metrics feed
* Confidence metrics feed

### Communication Protocol

* WebSocket

---

# 10. Windowing Strategy

ETA-Sync operates using short sliding temporal windows.

## Window Characteristics

| Parameter     | Strategy       |
| ------------- | -------------- |
| Window Type   | Sliding        |
| Window Length | Fixed duration |
| Advancement   | Time-based     |
| Overlap       | 50% overlap    |

## Design Objective

Windowing reduces:

* memory overhead,
* DTW complexity,
* inference latency.

---

# 11. Failure Handling Strategy

The system shall gracefully handle unstable streaming conditions.

## Failure Handling Rules

* Malformed packets shall be discarded.
* Temporary stream interruption shall not terminate sessions immediately.
* Missing frames shall be tolerated.
* Invalid timestamps shall trigger packet rejection.
* Inactive sessions shall expire after timeout.
* Backend failures shall not corrupt persisted artifacts.

## Recovery Goals

The implementation shall prioritize:

* deterministic recovery,
* session consistency,
* artifact integrity.

---

# 12. Design Constraints

The implementation shall:

* use lightweight edge-compatible processing,
* maintain modular architecture,
* avoid tightly coupled subsystems,
* preserve stable request/response contracts,
* support deterministic diagnostic outputs,
* prioritize explainability over infrastructure complexity.

The first implementation shall avoid:

* distributed systems,
* cloud orchestration,
* large-scale deployment infrastructure,
* production-grade scaling complexity.

---

# 13. Anti-Drift Rules

The following rules exist to prevent architectural drift during implementation.

## Rule Set

* Every new API must map to a documented use case.
* Every new module must belong to exactly one layer.
* Every output artifact must map to a requirement or diagnostic purpose.
* Every model change affecting packet structure must update backend contracts first.
* Visualization logic must remain observational only.
* Alignment logic must remain deterministic and independently testable.

---

# 14. Traceability Snapshot

| Requirement Group | Mapping                       |
| ----------------- | ----------------------------- |
| FR-1 to FR-6      | Mobile acquisition            |
| FR-7 to FR-11     | Streaming and buffering       |
| FR-12 to FR-15    | DTW alignment                 |
| FR-16 to FR-20    | Fusion and prediction         |
| FR-21 to FR-29    | Visualization and diagnostics |

---

# 15. Deliverable Outcome

This High-Level Design establishes the architectural shape of ETA-Sync before implementation begins.

The purpose of this document is to:

* stabilize system boundaries,
* reduce implementation drift,
* define ownership responsibilities,
* preserve modularity,
* improve research reproducibility,
* support maintainable implementation.

Future implementation work shall be evaluated against this architecture rather than against ad hoc design decisions.

---

# End of Document

```
```
