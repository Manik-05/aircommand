"""
Static gesture feature extraction: turns one frame's raw hand landmarks
into a translation- and scale-invariant fixed-length vector, suitable
for a shallow MLP or k-NN classifier (see architecture.md, "Training/
Inference Model Choice").

Deliberately NOT rotation-invariant: gestures like a distinct "thumbs
up" vs "thumbs down" rely on hand orientation, and normalizing rotation
away would make visually distinct static gestures collide with each
other. Users record their own gestures against a roughly consistent
webcam setup, so raw orientation carries real, useful signal here.
"""
from __future__ import annotations

import numpy as np

from capture import NUM_LANDMARKS

WRIST_IDX = 0
MIDDLE_MCP_IDX = 9  # stable anatomical reference point for hand-size scale

STATIC_FEATURE_DIM = NUM_LANDMARKS * 3  # 63: flattened (x, y, z) per landmark


def normalize_static(landmarks: list[list[float]], eps: float = 1e-6) -> np.ndarray:
    """Normalize one frame of 21x3 landmarks into a translation- and
    scale-invariant flat feature vector.

    - Translation invariance: subtract the wrist position from every
      landmark, so the same hand shape produces the same features
      regardless of where the hand sits in the camera frame.
    - Scale invariance: divide by the wrist-to-middle-finger-MCP
      distance, so the same hand shape produces the same features
      regardless of hand size or distance from the camera. Middle MCP
      (landmark 9) is used rather than a bounding-box diagonal because
      it's a single stable anatomical point — a bounding box shifts
      depending on which fingers happen to be extended, which would
      make the "same" static pose scale differently frame to frame.

    Args:
        landmarks: 21 x 3 list of (x, y, z), as produced by HandFrame
            (see capture/hand_capture.py).
        eps: floor for the scale denominator, in case of a degenerate
            (near-zero) hand detection — avoids a divide-by-zero
            blowing the feature vector up into garbage.

    Returns:
        A (63,) float32 numpy array — the flattened, normalized
        landmarks, ready to feed to a classifier.
    """
    points = np.asarray(landmarks, dtype=np.float32)
    if points.shape != (NUM_LANDMARKS, 3):
        raise ValueError(
            f"Expected {NUM_LANDMARKS}x3 landmarks, got shape {points.shape}"
        )

    wrist = points[WRIST_IDX]
    translated = points - wrist

    scale = float(np.linalg.norm(translated[MIDDLE_MCP_IDX]))
    scale = max(scale, eps)

    normalized = translated / scale
    return normalized.flatten()