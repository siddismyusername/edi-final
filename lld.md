# Low-Level Design (LLD)

# ETA-Sync Research Prototype

---

# Revision History

| Version | Date | Description                | Author                     |
| ------- | ---- | -------------------------- | -------------------------- |
| 1.0     | 2026 | Initial Complete LLD Draft | Siddharth Chaudhary et al. |

---

# Table of Contents

1. Introduction
2. Design Objectives
3. Backend Architecture Breakdown
4. Frontend Architecture Breakdown
5. Runtime State Model
6. Core Data Structures
7. API Contracts
8. WebSocket Event Contracts
9. Persistence Design
10. Window Buffer Design
11. DTW Alignment Pipeline
12. Fusion Pipeline
13. Visualization Pipeline
14. Configuration Layer
15. Validation Rules
16. Error Handling Strategy
17. Observability and Metrics
18. Replay and Artifact Recovery
19. Testing Strategy
20. Anti-Drift Rules
21. Implementation Sequence
22. Deliverable Outcome

---

# 1. Introduction

This Low-Level Design (LLD) document defines the implementation-level structure of ETA-Sync, a DTW-guided asynchronous multi-modal sensor fusion research prototype.

The purpose of this document is to establish:

* module ownership,
* runtime behavior,
* interface contracts,
* persistence formats,
* processing pipelines,
* event flows,
* validation rules,
* operational constraints.

This document exists to reduce implementation drift between:

* requirements,
* architecture,
* and final code behavior.

The LLD intentionally focuses on implementation contracts and system behavior rather than mathematical derivations or research formulation.

---

# 2. Design Objectives

The implementation shall:

* support asynchronous camera and IMU streams,
* maintain deterministic DTW behavior,
* expose stable backend contracts,
* support replayable experiments,
* preserve session artifacts,
* maintain modular separation between layers,
* support real-time diagnostics,
* remain edge-compatible.

The implementation shall prioritize:

* reproducibility,
* observability,
* deterministic outputs,
* modular ownership.

---

# 3. Backend Architecture Breakdown

The backend is divided into seven implementation modules.

```text
API Layer
    ↓
Session Layer
    ↓
Validation Layer
    ↓
Buffer Layer
    ↓
DTW Layer
    ↓
Fusion Layer
    ↓
Persistence Layer
```

---

## 3.1 API Layer

### Responsibilities

* Expose REST endpoints.
* Expose WebSocket endpoints.
* Validate request schemas.
* Return standardized errors.
* Dispatch packets to downstream systems.

### Suggested Modules

```text
app/main.py
app/api/routes/health.py
app/api/routes/session.py
app/api/routes/stream.py
app/api/routes/export.py
```

### REST Endpoints

| Endpoint          | Purpose              |
| ----------------- | -------------------- |
| `/health`         | Backend health check |
| `/session/create` | Create session       |
| `/session/close`  | Close session        |
| `/session/export` | Export artifacts     |

### WebSocket Endpoints

| Endpoint          | Purpose            |
| ----------------- | ------------------ |
| `/ws/stream`      | Sensor ingestion   |
| `/ws/diagnostics` | Dashboard feed     |
| `/ws/alignment`   | DTW diagnostics    |
| `/ws/fusion`      | Fusion diagnostics |

---

## 3.2 Session Management Layer

### Responsibilities

* Create sessions.
* Maintain runtime state.
* Track packet statistics.
* Manage session lifecycle.
* Handle session expiration.

### Suggested Modules

```text
app/core/session_manager.py
app/models/session.py
```

### Core Entities

| Entity            | Purpose                      |
| ----------------- | ---------------------------- |
| `Session`         | Runtime session state        |
| `SessionMetadata` | Device and capture metadata  |
| `StreamState`     | Stream lifecycle tracking    |
| `WindowState`     | Active temporal window state |

---

## 3.3 Validation Layer

### Responsibilities

* Validate packet structure.
* Validate timestamps.
* Validate sensor modes.
* Sanitize payload sizes.
* Prevent malformed input propagation.

### Suggested Modules

```text
app/validators/sensor_validator.py
app/validators/session_validator.py
```

### Validation Categories

| Validation Type      | Purpose                         |
| -------------------- | ------------------------------- |
| Schema Validation    | Required field enforcement      |
| Timestamp Validation | Prevent invalid ordering        |
| Payload Validation   | Prevent oversized payloads      |
| Sensor Validation    | Validate supported sensor types |

---

## 3.4 Buffer Layer

### Responsibilities

* Maintain sliding temporal windows.
* Synchronize modality extraction.
* Evict stale packets.
* Prepare DTW-ready windows.

### Suggested Modules

```text
app/buffers/window_buffer.py
```

### Internal Buffers

| Buffer            | Purpose                   |
| ----------------- | ------------------------- |
| `imu_buffer`      | Stores inertial packets   |
| `video_buffer`    | Stores frame packets      |
| `active_window`   | Current processing window |
| `previous_window` | Overlap management        |

### Window Characteristics

| Parameter   | Value        |
| ----------- | ------------ |
| Window Type | Sliding      |
| Advancement | Time-based   |
| Overlap     | 50%          |
| Window Size | Configurable |

### Eviction Strategy

* FIFO eviction
* Timestamp-based cleanup
* Session timeout cleanup

---

## 3.5 DTW Layer

### Responsibilities

* Compute pairwise distances.
* Generate DTW cost matrices.
* Compute optimal alignment paths.
* Generate normalized DTW priors.

### Suggested Modules

```text
app/services/dtw.py
```

### Core Outputs

| Output         | Description              |
| -------------- | ------------------------ |
| Cost Matrix    | Temporal distance matrix |
| Alignment Path | Optimal temporal path    |
| Bias Matrix    | Normalized DTW prior     |

### Processing Steps

```text
Input Window
      ↓
Feature Distance Computation
      ↓
DTW Cost Matrix
      ↓
Alignment Path
      ↓
Bias Matrix Normalization
```

### DTW Design Constraints

The DTW layer shall:

* remain deterministic,
* remain stateless,
* avoid UI dependency,
* avoid mutation of session state.

---

## 3.6 Fusion Layer

### Responsibilities

* Generate embeddings.
* Project embeddings into Q/K/V spaces.
* Inject DTW priors.
* Compute cross-attention.
* Produce fused outputs.

### Suggested Modules

```text
app/services/fusion.py
app/models/attention.py
app/models/encoder.py
```

### Internal Pipeline

```text
Feature Extraction
      ↓
Embedding Projection
      ↓
Query-Key-Value Projection
      ↓
DTW-Guided Attention
      ↓
Fusion Output
```

### Tensor Shapes

| Tensor               | Shape           |
| -------------------- | --------------- |
| Visual Embedding     | `(B, T_v, D)`   |
| IMU Embedding        | `(B, T_i, D)`   |
| DTW Bias Matrix      | `(T_v, T_i)`    |
| Attention Matrix     | `(B, T_v, T_i)` |
| Fused Representation | `(B, T_v, D)`   |

Where:

| Symbol | Meaning             |
| ------ | ------------------- |
| `B`    | Batch size          |
| `T_v`  | Visual timesteps    |
| `T_i`  | IMU timesteps       |
| `D`    | Embedding dimension |

---

## 3.7 Persistence Layer

### Responsibilities

* Persist raw packets.
* Persist alignment outputs.
* Persist fusion outputs.
* Archive session artifacts.
* Support replay workflows.

### Suggested Modules

```text
app/storage/session_store.py
app/storage/artifact_store.py
```

### Session Directory Structure

```text
sessions/
 └── session_id/
      ├── metadata.json
      ├── sensor_data.jsonl
      ├── diagnostics.json
      ├── camera_frames/
      ├── alignment/
      │    ├── dtw_alignment.json
      │    ├── dtw_bias.npy
      │    └── cost_matrix.npy
      └── fusion/
           ├── attention_weights.npy
           ├── fused_vectors.npy
           └── predictions.json
```

---

# 4. Frontend Architecture Breakdown

## 4.1 Dashboard Layer

### Responsibilities

* Display stream health.
* Render DTW matrices.
* Display alignment paths.
* Display attention heatmaps.
* Display latency metrics.
* Display prediction outputs.

### Suggested Modules

```text
web/src/app/*
web/src/components/ui/*
web/src/components/dashboard/*
```

### Dashboard Sections

| Section          | Purpose                 |
| ---------------- | ----------------------- |
| Stream Monitor   | Connection status       |
| DTW Heatmap      | Alignment visualization |
| Attention Viewer | Attention diagnostics   |
| Metrics Panel    | Latency and confidence  |
| Session Viewer   | Artifact exploration    |

### Design Constraints

The dashboard shall:

* remain read-only,
* consume backend events only,
* avoid inference logic,
* avoid alignment mutation.

---

# 5. Runtime State Model

The backend shall maintain explicit runtime states.

## Runtime States

| State            | Description             |
| ---------------- | ----------------------- |
| `idle`           | No active session       |
| `session_active` | Session initialized     |
| `buffering`      | Window buffering active |
| `aligning`       | DTW computation active  |
| `fusing`         | Attention fusion active |
| `broadcasting`   | Dashboard output active |
| `error`          | Runtime failure state   |

## State Transition Rules

* All transitions shall be logged.
* Invalid transitions shall raise errors.
* State changes shall emit dashboard events.

---

# 6. Core Data Structures

## 6.1 Sensor Packet

```json
{
  "timestamp": 1712345678,
  "sensor": "imu",
  "ax": 0.12,
  "ay": 0.44,
  "az": 9.81,
  "gx": 0.01,
  "gy": 0.04,
  "gz": 0.07
}
```

---

## 6.2 Camera Packet

```json
{
  "timestamp": 1712345678,
  "sensor": "camera",
  "frame_id": "frame_001",
  "width": 640,
  "height": 480,
  "encoding": "jpeg"
}
```

---

## 6.3 Alignment Output

```json
{
  "session_id": "session_001",
  "window_id": "window_01",
  "cost_matrix": "cost_matrix.npy",
  "alignment_path": [[0,0],[1,1]],
  "dtw_bias_matrix": "bias.npy"
}
```

---

## 6.4 Fusion Output

```json
{
  "prediction": "walking",
  "confidence_score": 0.91,
  "attention_weights": "attention.npy",
  "fused_representation": "fusion.npy"
}
```

---

# 7. API Contracts

## 7.1 Session Creation Request

### Required Fields

| Field       | Type            |
| ----------- | --------------- |
| `device_id` | string          |
| `mode`      | string          |
| `notes`     | optional string |

---

## 7.2 Session Response

```json
{
  "session_id": "session_001",
  "status": "created"
}
```

---

## 7.3 Standard Error Response

```json
{
  "error": "INVALID_PACKET",
  "message": "Missing timestamp field",
  "session_id": "session_001"
}
```

---

# 8. WebSocket Event Contracts

## Dashboard Events

| Event                | Purpose             |
| -------------------- | ------------------- |
| `SESSION_STARTED`    | Session initialized |
| `PACKET_RECEIVED`    | Packet ingestion    |
| `WINDOW_READY`       | Buffer ready        |
| `DTW_COMPLETED`      | Alignment complete  |
| `FUSION_COMPLETED`   | Fusion complete     |
| `SESSION_TERMINATED` | Session closed      |
| `ERROR_EVENT`        | Runtime error       |

---

# 9. Persistence Design

## Persistence Objectives

The persistence layer exists for:

* reproducibility,
* debugging,
* replay,
* experiment traceability.

## Persistence Rules

* Raw packets shall be append-only.
* Alignment artifacts shall be immutable.
* Fusion outputs shall be versioned.
* Session archives shall remain isolated.

---

# 10. Window Buffer Design

## Window Flow

```text
Incoming Packet
      ↓
Validation
      ↓
Buffer Insert
      ↓
Window Completion Check
      ↓
DTW Trigger
```

## Window Completion Criteria

A processing window becomes valid when:

* sufficient IMU packets exist,
* sufficient frame packets exist,
* timestamps satisfy overlap constraints.

## Synchronization Policy

The system shall:

* align by timestamps,
* tolerate jitter,
* avoid strict timestamp equality.

---

# 11. DTW Alignment Pipeline

## Processing Sequence

```text
Sliding Window
      ↓
Feature Distance Computation
      ↓
Cumulative Cost Matrix
      ↓
Optimal Alignment Path
      ↓
Bias Matrix Generation
      ↓
Normalization
```

## Output Constraints

The DTW pipeline shall:

* generate deterministic outputs,
* avoid modifying source packets,
* preserve temporal traceability.

---

# 12. Fusion Pipeline

## Processing Sequence

```text
Embedding Generation
      ↓
Query-Key-Value Projection
      ↓
DTW Bias Injection
      ↓
Attention Weight Computation
      ↓
Fusion Output
      ↓
Prediction Generation
```

## Fusion Constraints

The fusion layer shall:

* support variable sequence lengths,
* tolerate asynchronous windows,
* preserve tensor consistency.

---

# 13. Visualization Pipeline

## Visualization Flow

```text
Backend Events
      ↓
Dashboard Event Listener
      ↓
Metric Parsing
      ↓
Heatmap Rendering
      ↓
Diagnostic Panels
```

## Supported Visualizations

| Visualization     | Purpose                 |
| ----------------- | ----------------------- |
| DTW Cost Matrix   | Temporal alignment      |
| Alignment Path    | Correspondence tracking |
| Attention Heatmap | Fusion diagnostics      |
| Latency Graph     | Runtime monitoring      |
| Confidence Plot   | Prediction stability    |

---

# 14. Configuration Layer

## Suggested Modules

```text
config/settings.py
```

## Configurable Parameters

| Parameter              | Purpose                    |
| ---------------------- | -------------------------- |
| Window Size            | Temporal processing length |
| Overlap Ratio          | Sliding window overlap     |
| Embedding Dimension    | Feature size               |
| Max Frame Size         | Payload limits             |
| Session Timeout        | Cleanup policy             |
| WebSocket Limits       | Throughput protection      |
| DTW Normalization Mode | Bias scaling               |

---

# 15. Validation Rules

## Packet Validation

* Reject missing timestamps.
* Reject invalid sensor types.
* Reject malformed payloads.
* Reject oversized packets.

## Session Validation

* Reject missing device IDs.
* Reject invalid modes.
* Reject expired sessions.

## Window Validation

* Bound maximum window size.
* Reject invalid overlap configuration.

---

# 16. Error Handling Strategy

## Error Categories

| Error Type        | Description            |
| ----------------- | ---------------------- |
| Validation Error  | Malformed input        |
| Session Error     | Invalid session state  |
| Buffer Error      | Window inconsistency   |
| DTW Error         | Alignment failure      |
| Fusion Error      | Tensor mismatch        |
| Persistence Error | Artifact write failure |

## Recovery Rules

* Invalid packets shall be discarded.
* Sessions shall remain recoverable.
* Errors shall be logged.
* Corrupted artifacts shall not overwrite valid outputs.

---

# 17. Observability and Metrics

## Runtime Metrics

| Metric               | Purpose                 |
| -------------------- | ----------------------- |
| Packet Rate          | Stream monitoring       |
| Dropped Packets      | Reliability diagnostics |
| DTW Latency          | Alignment timing        |
| Fusion Latency       | Inference timing        |
| WebSocket Throughput | Streaming health        |
| Confidence Score     | Prediction stability    |

## Logging Requirements

The backend shall log:

* state transitions,
* runtime errors,
* session lifecycle events,
* DTW completion events,
* fusion completion events.

---

# 18. Replay and Artifact Recovery

## Replay Objectives

The system shall support:

* archived session loading,
* offline DTW regeneration,
* offline fusion replay,
* artifact inspection.

## Replay Flow

```text
Archived Session
      ↓
Packet Reconstruction
      ↓
Window Rebuilding
      ↓
DTW Replay
      ↓
Fusion Replay
```

---

# 19. Testing Strategy

## Unit Tests

| Test                | Purpose                   |
| ------------------- | ------------------------- |
| Schema Validation   | Validate packet structure |
| DTW Cost Generation | Verify alignment matrix   |
| Bias Normalization  | Verify scaling            |
| Fusion Shape Test   | Verify tensor outputs     |

## Integration Tests

| Test                   | Purpose                |
| ---------------------- | ---------------------- |
| REST Endpoint Test     | API verification       |
| WebSocket Test         | Streaming verification |
| Session Lifecycle Test | Runtime validation     |

## End-to-End Tests

| Test                      | Purpose                        |
| ------------------------- | ------------------------------ |
| Full Session Replay       | Complete workflow verification |
| Artifact Recovery         | Persistence verification       |
| Dashboard Synchronization | Visualization validation       |

---

# 20. Anti-Drift Rules

The implementation shall follow these rules.

* Do not add undocumented payload fields.
* Do not change tensor shapes without contract updates.
* Do not allow UI-only runtime state.
* Do not bypass validation layers.
* Do not allow dashboard logic to modify backend state.
* Do not introduce hidden processing paths.
* Do not alter window semantics without updating tests.

---

# 21. Implementation Sequence

## Recommended Order

```text
1. Define schemas and contracts
2. Implement session management
3. Implement persistence layer
4. Implement validation layer
5. Implement window buffers
6. Implement DTW alignment
7. Implement fusion pipeline
8. Implement dashboard bindings
9. Add replay support
10. Add observability and tests
```

---

# 22. Deliverable Outcome

This Low-Level Design establishes the implementation contract for ETA-Sync.

The purpose of this document is to:

* reduce implementation ambiguity,
* stabilize runtime behavior,
* preserve architectural modularity,
* improve experiment reproducibility,
* maintain deterministic processing behavior.

If implementation diverges from this document, the document shall be updated before architectural divergence becomes systemic.

---

# End of Document
