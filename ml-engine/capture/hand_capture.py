"""
Webcam capture + MediaPipe hand landmark extraction.

Owned by Dev A. Produces raw per-frame hand landmarks; normalization and
feature extraction happen downstream in `features/`. This module knows
nothing about gestures, classifiers, or GestureEngine — it's a thin,
independently-testable wrapper around OpenCV + MediaPipe.

NOTE ON MEDIAPIPE API VERSION: MediaPipe deprecated the old
`mp.solutions.hands` API (removed entirely in current pip releases —
only `mediapipe.tasks` and a couple of Image classes remain at the
top level now). This module uses the current, supported **Tasks API**
(`mp.tasks.vision.HandLandmarker`) instead. It requires a small model
file (`hand_landmarker.task`, ~8MB) which `ensure_model_downloaded()`
fetches automatically on first run and caches locally — no manual step
needed, but it does need network access the first time.
"""
from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

NUM_LANDMARKS = 21  # fixed by the MediaPipe hand model

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
# Cached alongside this file so every dev/machine gets its own copy without
# committing an 8MB binary to the repo.
DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"


def ensure_model_downloaded(model_path: Path = DEFAULT_MODEL_PATH) -> Path:
    """Download the hand_landmarker.task model bundle if it isn't already
    cached locally. Safe to call every time — no-ops if the file exists."""
    if model_path.exists():
        return model_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(_MODEL_URL, model_path)
    return model_path


@dataclass
class HandFrame:
    """One frame's worth of hand-landmark data.

    landmarks: 21 x 3 list of (x, y, z) in MediaPipe's normalized image
        coordinates — x, y in [0, 1] relative to image width/height, z is
        a rough depth relative to the wrist on the same scale as x. This
        is the raw format; `features/` does wrist-relative, bbox-scaled
        normalization on top of this for the classifiers.
    handedness: "Left" or "Right" as reported by MediaPipe.
    landmark_confidence: the handedness classification score for this
        detection, in [0, 1]. Downstream code (recording/training) should
        reject frames below a threshold rather than feed noisy data in —
        this is where `LOW_CONFIDENCE_SAMPLE` decisions get made.
    timestamp: time.monotonic() at capture, seconds. Monotonic (not
        wall-clock) since it's only ever used for relative timing
        (dynamic-gesture trajectories, motion-start heuristics).
    """

    landmarks: list[list[float]]
    handedness: str
    landmark_confidence: float
    timestamp: float

    def is_confident(self, min_confidence: float = 0.5) -> bool:
        return self.landmark_confidence >= min_confidence


class HandCapture:
    """Wraps a webcam + MediaPipe's HandLandmarker task.

    Usage:
        with HandCapture() as cap:
            for frame in cap.frames():
                if frame is None:
                    continue  # no hand in view this frame — not an error
                ...
                if done:
                    break  # cleanup happens on context exit

    Single-hand only for MVP (two-hand gestures are explicitly post-MVP
    per the architecture doc). If MediaPipe detects more than one hand,
    the one with the highest handedness confidence is returned.

    Runs the landmarker in VIDEO mode (synchronous, but frame-sequence
    aware — required over IMAGE mode for smooth per-frame tracking of a
    live feed). VIDEO mode requires strictly increasing timestamps, which
    this class manages internally.
    """

    def __init__(
        self,
        camera_index: int = 0,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
        model_path: Optional[Path] = None,
    ) -> None:
        self.camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._detector: Optional[mp_vision.HandLandmarker] = None
        self._model_path = model_path or DEFAULT_MODEL_PATH
        self._max_num_hands = max_num_hands
        self._min_detection_confidence = min_detection_confidence
        self._min_tracking_confidence = min_tracking_confidence
        self._last_timestamp_ms = -1

    def __enter__(self) -> "HandCapture":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def open(self) -> None:
        if self._cap is not None:
            return  # already open

        model_path = ensure_model_downloaded(self._model_path)
        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=self._max_num_hands,
            min_hand_detection_confidence=self._min_detection_confidence,
            min_tracking_confidence=self._min_tracking_confidence,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        self._detector = mp_vision.HandLandmarker.create_from_options(options)

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self._detector.close()
            self._detector = None
            raise RuntimeError(f"Could not open webcam at index {self.camera_index}")
        self._cap = cap
        self._last_timestamp_ms = -1

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._detector is not None:
            self._detector.close()
            self._detector = None

    def read_frame(self) -> Optional[HandFrame]:
        """Grab one frame from the webcam and run hand detection on it.

        Returns None if the frame couldn't be read, or no hand was
        detected — both are normal conditions the caller should skip
        past, not errors to raise on.
        """
        if self._cap is None or self._detector is None:
            raise RuntimeError(
                "HandCapture not opened — use `with HandCapture() as cap:` or call open() first"
            )

        ok, image = self._cap.read()
        if not ok:
            return None

        # MediaPipe expects RGB; OpenCV reads frames as BGR.
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        # VIDEO mode requires strictly increasing millisecond timestamps.
        timestamp_ms = max(int(time.monotonic() * 1000), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms

        result = self._detector.detect_for_video(mp_image, timestamp_ms)

        if not result.hand_landmarks:
            return None

        best_idx = 0
        if result.handedness and len(result.handedness) > 1:
            best_idx = max(
                range(len(result.handedness)),
                key=lambda i: result.handedness[i][0].score,
            )

        hand_landmarks = result.hand_landmarks[best_idx]
        landmarks = [[lm.x, lm.y, lm.z] for lm in hand_landmarks]

        handedness = "Unknown"
        confidence = 0.0
        if result.handedness:
            category = result.handedness[best_idx][0]
            handedness = category.category_name
            confidence = category.score

        return HandFrame(
            landmarks=landmarks,
            handedness=handedness,
            landmark_confidence=confidence,
            timestamp=time.monotonic(),
        )

    def frames(self) -> Iterator[Optional[HandFrame]]:
        """Infinite generator, one HandFrame (or None) per webcam frame.

        The caller drives the loop — `break` to stop; cleanup still runs
        on `with` block exit. Kept as a generator (rather than returning
        a list) since this needs to run indefinitely during recording
        and inference, not buffer unboundedly.
        """
        while True:
            yield self.read_frame()