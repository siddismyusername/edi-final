# Working of the DTW-Guided Cross-Attention Layer in ETA-Sync

---

# 1. Introduction

The DTW-guided cross-attention layer forms the core computational component of the ETA-Sync framework. Its purpose is to perform robust multi-modal fusion under asynchronous sensing conditions by integrating temporal alignment priors directly into transformer attention.

Unlike conventional fusion mechanisms that assume synchronized sensor streams, the proposed layer explicitly incorporates temporal plausibility information derived from Dynamic Time Warping (DTW). This enables the model to preserve meaningful cross-modal relationships even when sensor streams exhibit timestamp jitter, frame drops, and varying sampling rates.

This document explains the internal working of the DTW-guided cross-attention mechanism implemented in ETA-Sync.

---

# 2. Problem with Conventional Cross-Attention

Traditional transformer cross-attention computes relationships between feature embeddings using semantic similarity.

The standard attention formulation is:

[
\mathrm{Attention}(Q,K,V)
=========================

\mathrm{Softmax}
\left(
\frac{QK^T}{\sqrt{d_k}}
\right)V
]

where:

| Symbol | Meaning                  |
| ------ | ------------------------ |
| (Q)    | Query embeddings         |
| (K)    | Key embeddings           |
| (V)    | Value embeddings         |
| (d_k)  | Attention scaling factor |

The attention mechanism calculates similarity between query and key vectors and uses the resulting attention weights to aggregate information from the value vectors.

In synchronized environments, this mechanism performs effectively because temporally corresponding events occur at approximately matching positions in both modalities.

However, asynchronous sensor streams introduce several problems:

* Different sensor frequencies
* Timestamp drift
* Frame drops
* Variable network latency
* Non-linear temporal offsets

Under these conditions, semantically similar but temporally unrelated events may receive high attention scores.

As a result:

* attention becomes unstable,
* feature interaction becomes noisy,
* fusion quality degrades.

---

# 3. Sensor Inputs in ETA-Sync

ETA-Sync processes two primary asynchronous modalities:

| Modality      | Description                    |
| ------------- | ------------------------------ |
| Camera Stream | Visual motion frames           |
| IMU Stream    | Accelerometer + Gyroscope data |

These sensor streams operate independently and therefore produce sequences with:

* unequal lengths,
* inconsistent timestamps,
* asynchronous event alignment.

The sensor streams are represented as:

[
V = {v_1, v_2, ..., v_m}
]

[
I = {i_1, i_2, ..., i_n}
]

where:

| Symbol | Meaning                      |
| ------ | ---------------------------- |
| (V)    | Visual feature sequence      |
| (I)    | IMU feature sequence         |
| (m)    | Number of visual timesteps   |
| (n)    | Number of inertial timesteps |

Generally:

[
m \neq n
]

which indicates asynchronous temporal sampling.

---

# 4. Feature Extraction

Before fusion, raw sensor signals are converted into learned embeddings.

## 4.1 Visual Feature Encoder

The visual encoder processes camera frames and extracts motion-aware embeddings.

The extracted representation is:

[
V_e = {e^v_1, e^v_2, ..., e^v_m}
]

where:

[
e^v_i \in \mathbb{R}^{d}
]

Each embedding captures:

* spatial motion,
* frame-level temporal context,
* visual activity patterns.

---

## 4.2 IMU Feature Encoder

The IMU encoder processes:

* accelerometer readings,
* gyroscope signals,
* motion magnitude features.

The inertial embedding sequence is represented as:

[
I_e = {e^i_1, e^i_2, ..., e^i_n}
]

where:

[
e^i_j \in \mathbb{R}^{d}
]

These embeddings capture temporal motion dynamics from inertial sensing.

---

# 5. Dynamic Time Warping (DTW)

Dynamic Time Warping is used to estimate elastic temporal correspondence between the two asynchronous sequences.

Instead of enforcing rigid timestamp synchronization, DTW computes the optimal alignment path between sequences while allowing:

* temporal stretching,
* compression,
* local misalignment.

---

## 5.1 DTW Cost Matrix

For every pair of visual and inertial embeddings, a local distance metric is computed.

The cumulative DTW cost matrix is defined as:

[
D(i,j)=d(v_i,i_j)+
\min
\left{
\begin{array}{l}
D(i-1,j) \
D(i,j-1) \
D(i-1,j-1)
\end{array}
\right.
]

where:

| Symbol       | Meaning                   |
| ------------ | ------------------------- |
| (D(i,j))     | Cumulative alignment cost |
| (d(v_i,i_j)) | Local feature distance    |

The DTW algorithm generates:

* a cost matrix,
* an optimal alignment path,
* temporal correspondence information.

---

## 5.2 Alignment Bias Matrix

The alignment path is converted into a normalized temporal bias matrix:

[
B_{DTW} \in \mathbb{R}^{m \times n}
]

Each element in the matrix represents the temporal plausibility between visual and inertial timesteps.

High values indicate:

* strong temporal correspondence,
* likely alignment.

Low values indicate:

* temporally implausible interactions.

This matrix acts as a soft temporal prior.

---

# 6. Query, Key, and Value Construction

The cross-attention layer operates using transformer-style query, key, and value embeddings.

## 6.1 Query Embeddings

Visual embeddings are projected into query space:

[
Q = V_e W_Q
]

where:

| Symbol | Meaning                 |
| ------ | ----------------------- |
| (W_Q)  | Query projection matrix |

---

## 6.2 Key Embeddings

IMU embeddings are projected into key space:

[
K = I_e W_K
]

---

## 6.3 Value Embeddings

IMU embeddings are additionally projected into value space:

[
V = I_e W_V
]

The projections allow the model to learn modality-specific interaction representations.

---

# 7. DTW-Guided Cross-Attention

This stage represents the core contribution of ETA-Sync.

Conventional attention computes interaction purely from feature similarity:

[
QK^T
]

However, semantic similarity alone is insufficient under asynchronous sensing.

ETA-Sync therefore introduces temporal guidance through DTW-derived priors.

The proposed attention formulation is:

[
\mathrm{Attention}(Q,K,V)=
\mathrm{Softmax}
\left(
\frac{QK^T}{\sqrt{d_k}}
+
\alpha B_{DTW}
\right)V
]

where:

| Symbol    | Meaning                         |
| --------- | ------------------------------- |
| (B_{DTW}) | DTW temporal alignment bias     |
| (\alpha)  | Alignment influence coefficient |

---

# 8. Interpretation of the Attention Equation

The equation consists of two major components.

## 8.1 Semantic Similarity Component

[
\frac{QK^T}{\sqrt{d_k}}
]

This term measures feature similarity between modalities.

It captures:

* semantic relationships,
* motion similarity,
* feature-level interaction.

---

## 8.2 Temporal Alignment Component

[
\alpha B_{DTW}
]

This term injects temporal plausibility.

Its purpose is to:

* reward temporally aligned interactions,
* suppress implausible correspondences,
* stabilize attention under asynchronous conditions.

The parameter:

[
\alpha
]

controls the strength of temporal influence.

---

# 9. Attention Weight Generation

After combining semantic similarity and temporal alignment priors, the softmax operation generates normalized attention weights.

[
A =
\mathrm{Softmax}
\left(
\frac{QK^T}{\sqrt{d_k}}
+
\alpha B_{DTW}
\right)
]

The resulting matrix:

[
A \in \mathbb{R}^{m \times n}
]

represents cross-modal interaction probabilities.

High attention weights correspond to:

* semantically meaningful,
* temporally plausible,
* cross-modal relationships.

---

# 10. Fused Representation Generation

The final fused representation is computed as:

[
F = AV
]

where:

| Symbol | Meaning              |
| ------ | -------------------- |
| (F)    | Fused representation |
| (A)    | Attention weights    |
| (V)    | Value embeddings     |

The fused embedding contains:

* aligned visual information,
* aligned inertial motion context,
* temporally stabilized feature interactions.

---

# 11. Why DTW Guidance Improves Fusion

The DTW-guided mechanism improves fusion because it combines:

* semantic similarity,
* temporal consistency.

Traditional attention mechanisms may incorrectly associate unrelated events under jitter and delay.

ETA-Sync reduces this problem by explicitly encoding:

* temporal plausibility,
* alignment confidence,
* elastic correspondence.

As a result:

* attention becomes sharper,
* alignment becomes more stable,
* robustness improves under asynchronous conditions.

---

# 12. Attention Behavior Comparison

## 12.1 Standard Cross-Attention

Characteristics:

* Diffuse attention
* Noisy correspondence
* Unstable alignment
* Sensitivity to jitter

---

## 12.2 DTW-Guided Cross-Attention

Characteristics:

* Sharper attention maps
* Temporally localized focus
* Improved alignment consistency
* Better robustness under delay and frame drops

---

# 13. Sliding Window Processing

The implementation operates using short temporal windows.

Advantages:

* reduced memory usage,
* lower DTW complexity,
* real-time inference capability,
* edge deployment feasibility.

Each window independently performs:

1. Feature extraction
2. DTW computation
3. Alignment matrix generation
4. Cross-attention fusion
5. Prediction generation

---

# 14. Computational Complexity

## 14.1 DTW Complexity

Standard DTW complexity:

[
\mathcal{O}(mn)
]

where:

| Symbol | Meaning                |
| ------ | ---------------------- |
| (m)    | Visual sequence length |
| (n)    | IMU sequence length    |

---

## 14.2 Attention Complexity

Attention computation complexity:

[
\mathcal{O}(mn d)
]

where:

| Symbol | Meaning             |
| ------ | ------------------- |
| (d)    | Embedding dimension |

The implementation reduces computational overhead using:

* lightweight embeddings,
* short windows,
* edge-compatible model sizes.

---

# 15. Final Processing Pipeline

The complete DTW-guided cross-attention workflow is summarized below.

```text
Camera Stream + IMU Stream
            ↓
Feature Extraction
            ↓
Embedding Generation
            ↓
DTW Temporal Alignment
            ↓
DTW Bias Matrix
            ↓
Query-Key-Value Projection
            ↓
DTW-Guided Cross-Attention
            ↓
Attention Weight Generation
            ↓
Fused Representation
            ↓
Prediction Output
```

---

# 16. Summary

The DTW-guided cross-attention layer enables ETA-Sync to perform robust asynchronous multi-modal fusion by integrating elastic temporal alignment priors directly into transformer attention.

Unlike traditional synchronization approaches that rely solely on preprocessing, ETA-Sync combines:

* temporal correspondence estimation,
* semantic feature interaction,
* learnable neural fusion.

This design allows the framework to maintain stable and temporally coherent fusion behavior under:

* timestamp jitter,
* variable latency,
* asynchronous sampling,
* frame inconsistency.

The DTW-guided attention layer therefore forms the central mechanism responsible for the robustness and alignment consistency demonstrated by ETA-Sync.

---

# End of Document
