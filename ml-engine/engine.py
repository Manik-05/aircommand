"""
GestureEngine — the ONLY class the backend is allowed to import from
ml-engine. Everything else in this package (capture/, features/, models/,
training/, inference/) is private implementation detail owned by Dev A.

Dev B (backend) calls these methods directly (in-process, same Python
process) and passes a callback to `subscribe()` to receive events. The
event payloads this emits must match the shapes in shared/schemas.py.

This file currently contains STUBS so both devs can build against a fixed
interface before the real implementation lands. Replace bodies, keep
signatures stable — signature changes need a heads-up to Dev B since the
backend will already be calling these.
"""
from __future__ import annotations

from typing import Callable, Literal

GestureType = Literal["static", "dynamic"]


class GestureEngine:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self._event_callback: Callable[[dict], None] | None = None
        self._recording_gesture_id: str | None = None
        self._inference_running = False

    # ---- subscription -------------------------------------------------
    def subscribe(self, callback: Callable[[dict], None]) -> None:
        """Backend registers a callback here. Engine calls it with dicts
        shaped like the ServerMessage variants in shared/protocol.md
        (e.g. {"type": "landmark_frame", ...}, {"type": "gesture_detected", ...}).
        """
        self._event_callback = callback

    def _emit(self, event: dict) -> None:
        if self._event_callback:
            self._event_callback(event)

    # ---- recording ------------------------------------------------------
    def start_recording(self, gesture_name: str, gesture_type: GestureType) -> str:
        """Create a draft gesture, start streaming landmark_frame events,
        return the new gesture_id."""
        raise NotImplementedError  # TODO(Dev A)

    def capture_sample(self) -> None:
        """Capture current buffer as one training sample for the gesture
        currently being recorded. Emits sample_captured."""
        raise NotImplementedError  # TODO(Dev A)

    def stop_recording(self, gesture_id: str) -> None:
        raise NotImplementedError  # TODO(Dev A)

    # ---- training ---------------------------------------------------
    def train(self, gesture_id: str) -> dict:
        """Fit a model for this gesture from its stored samples, persist it,
        and return a TrainingResult-shaped dict. Emits training_complete
        (and optionally training_progress) via the subscribed callback."""
        raise NotImplementedError  # TODO(Dev A)

    # ---- inference ----------------------------------------------------
    def start_inference(self) -> None:
        """Begin the real-time recognition loop. Emits gesture_detected
        events via the subscribed callback as gestures are recognized."""
        self._inference_running = True
        raise NotImplementedError  # TODO(Dev A)

    def stop_inference(self) -> None:
        self._inference_running = False

    # ---- housekeeping ---------------------------------------------------
    def delete_gesture(self, gesture_id: str) -> None:
        raise NotImplementedError  # TODO(Dev A)
