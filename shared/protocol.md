# AirCommand Protocol (v1)

Source of truth for the WebSocket + REST contract between `backend` and any
client (`dashboard`, later `browser-extension`). Changing this file requires
a PR reviewed by both Dev A and Dev B.

WebSocket endpoint: `ws://localhost:8000/ws`

## Client → Server messages

| type | fields | notes |
|---|---|---|
| `start_recording` | `gesture_name: str`, `gesture_type: "static"\|"dynamic"` | begins a new recording session, server creates a draft gesture and returns its id via `recording_started` |
| `capture_sample` | — | tells server to capture the current buffered frame(s) as one sample |
| `stop_recording` | `gesture_id: str` | ends the session |
| `start_training` | `gesture_id: str` | kicks off training/fitting for that gesture |
| `assign_action` | `gesture_id: str`, `action: Action` | binds an action to a trained gesture |
| `start_inference` | — | begin real-time recognition loop |
| `stop_inference` | — | stop real-time recognition loop |
| `delete_gesture` | `gesture_id: str` | removes gesture + its model/samples |

## Server → Client messages

| type | fields | notes |
|---|---|---|
| `recording_started` | `gesture_id: str` | ack for `start_recording` |
| `landmark_frame` | `landmarks: number[21][3]`, `timestamp: float` | live preview stream while camera is active |
| `sample_captured` | `gesture_id: str`, `count: int`, `target: int` | progress during recording |
| `training_progress` | `gesture_id: str`, `status: "training"`, `progress: float(0-1)` | optional, may just jump straight to complete for MVP |
| `training_complete` | `gesture_id: str`, `accuracy: float`, `model_path: str` | |
| `gesture_detected` | `gesture_id: str`, `confidence: float`, `timestamp: float` | fired during inference |
| `action_executed` | `gesture_id: str`, `action: Action` | fired after the executor runs an action |
| `error` | `code: str`, `message: str` | see error codes below |

## Error codes

- `LOW_CONFIDENCE_SAMPLE` — recorded sample rejected (missing/low-confidence landmarks)
- `NOT_ENOUGH_SAMPLES` — training requested before minimum sample count reached
- `TRAINING_FAILED`
- `UNKNOWN_GESTURE_ID`
- `INVALID_MESSAGE` — malformed/unrecognized message type or payload

## REST endpoints (non-realtime)

- `GET /gestures` → `Gesture[]`
- `GET /gestures/{id}` → `Gesture`
- `DELETE /gestures/{id}` → `204`
- `GET /models/{id}/status` → `{ trained: bool, accuracy: float|null }`

## Constants

- `MIN_SAMPLES_PER_GESTURE = 10`
- `DEFAULT_TARGET_SAMPLES = 15`
- `DEFAULT_CONFIDENCE_THRESHOLD = 0.85`
- `INFERENCE_COOLDOWN_MS = 700`

See `shared/schemas.py` (Python) and `shared/types.ts` (TypeScript) for the
exact data shapes referenced above (`Gesture`, `Action`, `Sample`, etc).
Keep those two files in sync by hand at this project's scale.
