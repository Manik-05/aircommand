# AirCommand — Architecture & Development Plan

## A. Architecture Overview

Single-machine, local-first system. One Python process hosts the ML engine and a FastAPI/WebSocket server; the React dashboard and (later) browser extension are clients that talk to it over a well-defined event protocol. No direct coupling between ML code and UI code — ever.

```
Webcam → MediaPipe → Feature Extraction → Gesture Engine (train/infer)
                                              │
                                       Python function calls (in-process)
                                              │
                                     FastAPI + WebSocket Server
                                              │
                              JSON event protocol over WebSocket/REST
                              ┌───────────────┴───────────────┐
                       React Dashboard                Browser Extension (Phase 2)
                              │
                     Desktop Action Executor (keyboard/mouse, via pynput)
```

Two boundaries matter:
1. **ml-engine ↔ backend**: an in-process Python API (a class with documented methods). Backend never reaches into MediaPipe/model internals.
2. **backend ↔ dashboard/extension**: a JSON WebSocket/REST protocol. Dashboard never imports Python; backend never touches React state.

This gives Developer A and Developer B a hard contract to build against independently.

## B. Repository Structure

```
aircommand/
├── ml-engine/              # Dev A — pure Python package, no server code
│   ├── capture/            # webcam + MediaPipe wrapper
│   ├── features/           # landmark normalization, static + trajectory features
│   ├── models/             # classifiers (static MLP/kNN, dynamic DTW/1D-CNN)
│   ├── training/           # training pipeline, persistence
│   ├── inference/           # real-time loop, smoothing, cooldown
│   ├── engine.py           # GestureEngine — the public interface
│   └── tests/
├── backend/                # Dev A+B shared, mostly Dev B
│   ├── api/                # REST routes
│   ├── ws/                 # WebSocket server, event router
│   ├── storage/            # gesture/action persistence (SQLite/JSON)
│   ├── actions/            # keyboard/mouse/browser action executors
│   └── tests/
├── dashboard/               # Dev B — React + Vite + TS
│   ├── src/components/
│   ├── src/hooks/           # useGestureSocket, etc.
│   └── src/types/           # TS mirrors of shared schema
├── browser-extension/       # Dev B — Phase 2, empty at MVP
├── shared/                  # SOURCE OF TRUTH for the contract
│   ├── protocol.md          # event/message definitions
│   ├── schemas.py           # Pydantic models (backend uses these directly)
│   └── types.ts             # hand-mirrored TS types (dashboard uses these)
├── tests/                   # integration/e2e tests spanning modules
└── docs/
```

Why not nest ml-engine inside backend? Keeping it a standalone package means Dev A can develop and test it headlessly (CLI harness, no server needed) while Dev B builds against a mock — this is the main source of merge-conflict avoidance.

## C. Component Responsibilities

- **ml-engine**: capture frames, extract hand landmarks, normalize/extract features, record samples, train per-gesture models, run real-time inference, apply temporal smoothing + cooldown, emit `GestureEvent` objects. Owns nothing about actions, storage schema for users, or UI.
- **backend**: owns the WebSocket/REST surface, gesture + action persistence, wiring `GestureEvent → assigned Action → executor`. Imports `ml-engine` only through `GestureEngine`'s public methods.
- **dashboard**: gesture CRUD UI, recording wizard (webcam preview + capture UI), training trigger + progress, action assignment, live recognition view. Talks only to backend over the protocol.
- **browser-extension** (Phase 2): subscribes to the same WebSocket events to trigger tab/scroll actions.
- **shared**: the only place both devs must agree on before changing. Pydantic (Python) and TS types kept in sync manually at MVP scale — not worth codegen tooling yet.

## D. API / Event Contract (WebSocket, JSON)

**Client → Server**
```json
{ "type": "start_recording", "gesture_name": "Next Tab", "gesture_type": "dynamic" }
{ "type": "capture_sample" }
{ "type": "stop_recording", "gesture_id": "g_123" }
{ "type": "start_training", "gesture_id": "g_123" }
{ "type": "assign_action", "gesture_id": "g_123", "action": { "type": "keyboard", "keys": ["ctrl","tab"] } }
{ "type": "start_inference" }
{ "type": "stop_inference" }
{ "type": "delete_gesture", "gesture_id": "g_123" }
```

**Server → Client**
```json
{ "type": "landmark_frame", "landmarks": [[x,y,z], ...], "timestamp": 1234 }
{ "type": "sample_captured", "gesture_id": "g_123", "count": 7, "target": 15 }
{ "type": "training_progress", "gesture_id": "g_123", "status": "training", "progress": 0.6 }
{ "type": "training_complete", "gesture_id": "g_123", "accuracy": 0.94 }
{ "type": "gesture_detected", "gesture_id": "g_123", "confidence": 0.91, "timestamp": 1234 }
{ "type": "action_executed", "gesture_id": "g_123", "action": {...} }
{ "type": "error", "code": "LOW_CONFIDENCE_SAMPLE", "message": "..." }
```

REST is used only for bulk/non-realtime operations: `GET /gestures`, `GET /gestures/{id}`, `DELETE /gestures/{id}`, `GET /models/{id}/status`.

## E. Data Models (shared/schemas.py, mirrored in shared/types.ts)

```python
class Sample(BaseModel):
    landmarks_sequence: list[list[list[float]]]  # frames × 21 points × (x,y,z)
    duration_ms: int
    recorded_at: datetime

class Gesture(BaseModel):
    id: str
    name: str
    gesture_type: Literal["static", "dynamic"]
    samples: list[Sample]
    model_ref: str | None          # path to trained model artifact
    action: Action | None
    confidence_threshold: float = 0.85
    created_at: datetime

class Action(BaseModel):
    type: Literal["keyboard", "mouse", "browser", "app"]
    payload: dict                  # e.g. {"keys": ["ctrl","tab"]}

class GestureEvent(BaseModel):
    gesture_id: str
    confidence: float
    timestamp: float

class TrainingResult(BaseModel):
    gesture_id: str
    accuracy: float
    model_path: str
    trained_at: datetime
```

## F. Custom Gesture Storage

MVP: no database server. Per-user profile folder on disk:
```
data/
  gestures.json           # Gesture metadata + actions (no raw landmark blobs)
  samples/{gesture_id}/*.json
  models/{gesture_id}/model.bin (+ scaler/template files)
```
`gestures.json` is the single index the backend loads at startup and rewrites on change. This avoids setting up SQLite/Postgres for the MVP; migrating to SQLite later only touches `backend/storage/`, nothing else.

## Training/Inference Model Choice (important — no default LSTM)

With ~15 reps per user-defined gesture, an LSTM/1D-CNN trained from scratch will overfit and generalize poorly. Recommended approach:

- **Static gestures** (a held pose): normalize landmarks relative to wrist + scale by hand bounding box → flatten to a fixed-length vector → classify with a shallow MLP or even simple k-NN/SVM against class centroids. Trains instantly, works fine with 15 samples.
- **Dynamic gestures** (a motion, e.g. swipe): resample each recorded sequence to a fixed number of frames (e.g. 30) via interpolation, extract trajectory + velocity features, and match new attempts using **DTW (Dynamic Time Warping)** against stored templates, or k-NN over DTW distance. No training step needed, robust to few samples, handles variable-length input naturally, and is fast enough for a handful of gesture classes.
- **Upgrade path** (Phase 2+): once usage logs accumulate more corrected samples per gesture, move to a small 1D-CNN or GRU per gesture family, or a shared embedding network (few-shot/Siamese style) trained once across all users' gestures. Transformers are unnecessary at this scale — added complexity with no accuracy benefit given short sequences and few classes.

Real-time inference: continuous sliding window buffer of recent frames; a motion-start heuristic (velocity/displacement threshold) triggers a matching attempt rather than matching every frame (saves compute); confidence threshold + a cooldown period after a firing (e.g. 700ms) prevents duplicate/false-positive triggers; optional majority vote over last k inference results for stability.

## F/G. Git Workflow

- `main`: protected, always demo-able.
- `develop`: integration branch, merged into `main` at milestones.
- Feature branches: `feature/mlengine-<topic>` (Dev A), `feature/dashboard-<topic>` / `feature/backend-<topic>` (Dev B).
- Any change to `shared/protocol.md` or `shared/schemas.py`/`types.ts` requires a PR reviewed by **both** developers before merge — this is the one place conflicts actually matter.
- Small, frequent PRs; conventional commit messages; CI runs each package's own tests independently (ml-engine tests don't need Node, dashboard tests don't need Python).

## G. MVP Roadmap

**MVP includes:**
- Static gesture creation, recording (15 samples), training, real-time recognition.
- One dynamic gesture type (e.g., swipe left/right) via DTW.
- Dashboard: gesture list, create-gesture wizard with webcam preview, train button, live recognition panel showing detected gesture + confidence.
- Action assignment limited to keyboard shortcuts.
- Local JSON-file storage.

**Explicitly NOT built initially:**
- Browser extension.
- Mouse gesture control.
- Application-specific per-app action profiles.
- Two-hand gestures.
- Cloud sync / multi-user accounts.
- Model versioning/rollback UI, gesture marketplace/sharing.
- Transformer or GPU-trained deep models.
- Active learning / continual retraining loop.

## H. Developer A Task Breakdown (ML)

1. Conda env + MediaPipe/OpenCV capture pipeline (webcam → landmarks).
2. Feature extraction: static normalization; dynamic resampling + trajectory features.
3. Recording/session module (collects N samples, validates quality, e.g. rejects samples with missing landmarks).
4. Static classifier (MLP/k-NN) + dynamic matcher (DTW).
5. Training pipeline: fit + persist model artifact, return `TrainingResult`.
6. Real-time inference loop: sliding window, motion-start trigger, confidence threshold, cooldown, emits `GestureEvent`.
7. Public interface: `GestureEngine` class (`start_recording`, `capture_sample`, `stop_recording`, `train`, `start_inference`, `stop_inference`, `subscribe(callback)`), documented in `ml-engine/README.md`.
8. Unit tests for feature extraction determinism + classifier accuracy on held-out reps.

## I. Developer B Task Breakdown (App)

1. FastAPI scaffold + WebSocket server implementing the protocol in `shared/protocol.md`.
2. Wire `GestureEngine` callbacks into WebSocket broadcast (backend-side only — no ML logic here).
3. Gesture/action storage layer (`gestures.json` read/write).
4. Action executor: keyboard shortcuts via `pynput`.
5. React dashboard: gesture list, create-gesture wizard, webcam recording UI, live confidence/landmark visualization, action assignment form.
6. WebSocket client hook (`useGestureSocket`) with reconnect/error handling.
7. (Phase 2) Browser extension subscribing to the same WebSocket.

## J. Integration Strategy

- Agree on `shared/protocol.md` and data models **before** either dev writes substantial code — this is step one for both.
- Dev A builds a CLI harness (`python -m ml_engine.demo`) to test the engine headlessly without the server.
- Dev B builds against a **mock WebSocket server** that replays canned `gesture_detected`/`training_progress` events, so dashboard work doesn't block on ML being finished.
- Weekly integration checkpoint: plug the real ml-engine into the real backend and real dashboard, run the full record→train→recognize→action loop.

## K. Testing Strategy

- ml-engine: unit tests on feature extraction (deterministic given fixed input) and classifier accuracy on held-out repetitions of recorded samples.
- backend: contract tests asserting every WebSocket message matches `shared/schemas.py`.
- dashboard: component tests + one Playwright/Cypress happy-path test (create → record → train → see live recognition) run against the mock server.
- Manual end-to-end checklist before any demo: record gesture → train → assign action → perform gesture → correct action fires within acceptable latency.

## L. Future Expansion (post-MVP)

- Active learning: log inference confirmations/corrections, retrain gestures with accumulated real usage data; revisit 1D-CNN/GRU once per-gesture sample counts are larger.
- Two-hand gestures, mouse cursor control mode.
- Per-application gesture profiles (foreground window detection).
- Browser extension: tab/scroll/navigation actions.
- Confidence calibration, continuous (non-segmented) gesture detection via motion-energy analysis.
- Cloud sync, multi-device profiles, gesture sharing/marketplace.
- Quantized/optimized model export for lower CPU latency.

## Conda Environment Setup

```bash
conda create -n aircommand python=3.11 -y
conda activate aircommand

# ml-engine / backend dependencies
pip install mediapipe opencv-python numpy scikit-learn
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU is fine at this scale
pip install dtaidistance                # DTW implementation
pip install fastapi uvicorn[standard] websockets pydantic
pip install pynput                      # keyboard/mouse action execution
pip install pytest pytest-asyncio       # testing

# export for reproducibility
conda env export --no-builds > environment.yml
```

Dashboard (Node, outside conda):
```bash
cd dashboard
npm create vite@latest . -- --template react-ts
npm install
```
