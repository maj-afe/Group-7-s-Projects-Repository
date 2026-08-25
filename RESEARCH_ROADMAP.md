# BUG: Hands-Free Browsing Assistant — Research Roadmap

## 🎯 Thesis Statement
Existing hands-free accessibility systems demonstrate head-based cursor control and facial or voice interaction, but practical desktop use remains challenged by individual variation in motor behavior, noisy inputs, unintended activations, and limited coordination between modalities. **BUG investigates an adaptive, offline, multimodal control architecture that personalizes interaction parameters and arbitrates between facial and voice inputs** while measuring accuracy, latency, false activations, and resource consumption.

---

## 📊 Current Status Summary
- **Phase 1 (Engineering Baseline):** Complete. Face tracking and voice recognition pipelines are running simultaneously.
- **Phase 2 (Research Implementation):** **In Progress (Focus: Adaptive Calibration)**
- **Phase 3 (Evaluation):** To Do.

---

## 🧪 Contribution 1: Adaptive Personal Calibration (Priority 1)
*Goal: Move away from fixed sensitivity thresholds and adapt dynamically to the user's natural motor range and behavior.*

- [x] Basic single-point anchor calibration (Center X/Y).
- [ ] Measure and log the user's maximum natural head range during calibration.
- [ ] Implement dynamic sensitivity: Small head movements = high precision, Large movements = high gain.
- [ ] Implement fatigue-aware interactions (e.g., automatically increasing cursor gain if movement amplitude decreases over a long session).
- [ ] Measure user's natural mouth-open resting distance and dynamically set the click threshold.

---

## 🧠 Contribution 2: Cross-modal Intent Arbitration (Priority 2)
*Goal: Stop running Face and Voice as completely independent silos. Merge them through a Multimodal Intent Manager.*

- [x] Both pipelines are running on separate threads without blocking.
- [ ] Build the **Multimodal Intent Manager**.
- [ ] *Contextual execution:* If voice says "click", check if the face cursor is currently stable on a target before executing.
- [ ] *Cross-modal control:* If voice says "scroll down", lock the mode so that vertical head movement maps directly to scroll speed instead of cursor movement.

---

## 🛡️ Contribution 3: False-Action & Safety Suppression (Priority 3)
*Goal: Prevent accidents by distinguishing between low-risk and high-risk actions.*

- [x] **Emergency Stop:** Implemented "emergency stop" command that disables all automation, and "enable control" to resume.
- [ ] **Risk Classification:** Categorize commands into low-risk (scroll, move) and high-risk (close window, delete).
- [ ] **Confirmation Policies:** If a high-risk voice command is detected (e.g. "Close Window"), the system must prompt "Close this window?" and wait for a "Yes" voice confirmation.
- [ ] **False Activation Suppression:** If the mouth opens *while* the user is talking (detected via VAD/Whisper), suppress the mouth-click action to prevent accidental clicking.

---

## ⚙️ Contribution 4: Offline Resource Efficiency (Priority 4)
*Goal: Ensure the system can run locally on commodity hardware without cloud reliance, ensuring privacy and zero network latency.*

- [x] Transitioned to Faster-Whisper for local offline transcription.
- [x] PyInstaller standalone `.exe` build process established for easy deployment.
- [ ] Benchmark Whisper.cpp vs. Vosk vs. Faster-Whisper for RAM, CPU usage, and latency.
- [ ] Benchmark quantized INT8 models for low-resource environments.
- [ ] Domain-constrained ASR correction: Map misheard commands (e.g. "scold down") to our command ontology via fuzzy matching. *(Partially implemented).*

---

## 📈 Contribution 5: User Evaluation (Priority 5)
*Goal: Validate the system with real-world testing.*

- [ ] Define metrics: target acquisition time, overshoot, path length, throughput, user workload.
- [ ] Compare "Fixed Threshold BUG" vs. "Adaptive Multimodal BUG" in user trials.
