# Claude context — Developer A (ML / Gesture Recognition)

Paste this whole file as your first message to Claude in your own session
to get it up to speed, then attach/paste the files it references.

---

## Project

**AirCommand** — real-time, ML-powered touchless computer control via
webcam hand gestures, with a killer feature: users can teach it their own
custom gestures (record ~15 reps, system trains a model, user assigns an
action).

Two developers, working independently on different machines, GitHub repo
`aircommand`. **I am Developer A.**

## My ownership

Everything in `ml-engine/`:
- Webcam capture + MediaPipe hand landmark extraction (`capture/`)
- Feature extraction: static pose normalization, dynamic trajectory/resampling (`features/`)
- Static gesture classifier (MLP or k-NN) + dynamic gesture matcher (DTW) (`models/`)
- Training pipeline: fit + persist model artifacts (`training/`)
- Real-time inference: sliding window, motion-start trigger, confidence
  threshold, cooldown/debounce for false-positive prevention (`inference/`)
- The public interface: `ml-engine/engine.py::GestureEngine` — this is the
  ONLY thing Developer B's backend imports from my code. I must keep its
  method signatures stable; if I need to change one, flag it to Dev B.

## What I must NOT do

Never write React code, never touch `dashboard/` or `backend/app/ws` /
`backend/app/api`. My package has zero networking code — no FastAPI, no
WebSocket, no HTTP. `GestureEngine` is called in-process by the backend;
I just implement its methods and call `self._emit(event_dict)` when
something happens (a landmark frame, a sample captured, training done, a
gesture detected). Event dict shapes must match `shared/schemas.py` /
`shared/protocol.md` — I don't own that file but must follow it.

## Key design decision — don't default to LSTM

With ~15 samples per user-defined gesture, an LSTM/CNN trained from
scratch will overfit badly. Approach:
- **Static gestures**: normalize landmarks relative to wrist + hand
  bounding-box scale → flatten to fixed vector → shallow MLP or k-NN.
- **Dynamic gestures**: resample sequence to fixed length (e.g. 30
  frames) via interpolation, extract trajectory/velocity features, match
  via **DTW** against stored templates (k-NN over DTW distance). No
  training step needed, robust to few samples.
- Upgrade path later (not now): 1D-CNN/GRU once usage data accumulates;
  transformers are not justified at this scale.

## Files to give Claude in your session

1. This file.
2. `docs/architecture.md` (full architecture — read section "Training/Inference
   Model Choice" and section H closely).
3. `shared/protocol.md` and `shared/schemas.py` (the contract I must satisfy).
4. `ml-engine/engine.py` (my stub interface — implement these methods).
5. `ml-engine/README.md`.

## My task list (in order)

1. Conda env verification (`environment.yml` at repo root, already set up
   by whoever scaffolded the repo — just `conda env create -f
   environment.yml && conda activate aircommand`).
2. `capture/`: webcam → MediaPipe → 21 hand landmarks per frame.
3. `features/`: static normalization function; dynamic resampling +
   trajectory feature extraction.
4. `training/` + `models/`: recording/session capture (validate sample
   quality, reject low-confidence landmark frames), static classifier fit,
   DTW template storage for dynamic gestures, persist to
   `data/models/{gesture_id}/`.
5. `inference/`: real-time loop — sliding window buffer, motion-start
   heuristic to trigger a match attempt (don't match every frame),
   confidence threshold, cooldown (~700ms) after a firing.
6. Wire all of the above into `GestureEngine`'s stub methods in
   `ml-engine/engine.py`, replacing `raise NotImplementedError`.
7. Build a CLI harness (`python -m ml_engine.demo`) so I can test the full
   record→train→recognize loop without the backend or dashboard running.
8. Unit tests in `ml-engine/tests/` — feature extraction determinism,
   classifier accuracy on held-out repetitions (use recorded fixture
   sequences, not a live webcam, so tests run in CI).

## Working agreement

- Branch naming: `feature/mlengine-<topic>`.
- I don't touch `shared/protocol.md`/`schemas.py` without a PR both of us
  review — those are the contract.
- I test headlessly via the CLI harness; I don't need the dashboard or
  backend running to develop or test my code.
