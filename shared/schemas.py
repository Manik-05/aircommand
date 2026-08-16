"""
Single source of truth for AirCommand data shapes (Python side).
Mirrored by hand in shared/types.ts — keep both in sync.
See shared/protocol.md for the message contract these are used in.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

GestureType = Literal["static", "dynamic"]
ActionType = Literal["keyboard", "mouse", "browser", "app"]


class Sample(BaseModel):
    landmarks_sequence: list[list[list[float]]]  # frames x 21 points x (x, y, z)
    duration_ms: int
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class Action(BaseModel):
    type: ActionType
    payload: dict
    # examples:
    #   keyboard: {"keys": ["ctrl", "tab"]}
    #   mouse:    {"action": "click", "button": "left"}
    #   browser:  {"command": "new_tab"}
    #   app:      {"app": "spotify", "command": "next_track"}


class Gesture(BaseModel):
    id: str
    name: str
    gesture_type: GestureType
    samples: list[Sample] = Field(default_factory=list)
    model_ref: Optional[str] = None
    action: Optional[Action] = None
    confidence_threshold: float = 0.85
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GestureEvent(BaseModel):
    gesture_id: str
    confidence: float
    timestamp: float


class TrainingResult(BaseModel):
    gesture_id: str
    accuracy: float
    model_path: str
    trained_at: datetime = Field(default_factory=datetime.utcnow)


# --- Constants (must match shared/protocol.md) ---
MIN_SAMPLES_PER_GESTURE = 10
DEFAULT_TARGET_SAMPLES = 15
DEFAULT_CONFIDENCE_THRESHOLD = 0.85
INFERENCE_COOLDOWN_MS = 700
