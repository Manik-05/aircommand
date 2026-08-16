"""
Dynamic gesture feature extraction: turns a variable-length recorded
sequence of hand landmarks into a fixed-length trajectory feature
sequence for DTW-based matching (see architecture.md, "Training/
Inference Model Choice"). The DTW matcher itself lives in `models/` —
this module only prepares the per-frame feature vectors it will compare.
"""
from __future__ import annotations

import numpy as np

from capture import NUM_LANDMARKS
from features.static import MIDDLE_MCP_IDX, WRIST_IDX

DEFAULT_TARGET_LENGTH = 30  # matches architecture.md's suggested resample length

# Palm centroid = average of wrist + all four MCP knuckles (indices
# 0, 5, 9, 13, 17) — a more stable "hand position" reference than any
# single landmark, since it barely moves when fingers curl or extend
# (unlike, say, a fingertip).
_PALM_LANDMARK_IDXS = (0, 5, 9, 13, 17)

# Trajectory feature per timestep: (pos_x, pos_y, pos_z, vel_x, vel_y, vel_z)
TRAJECTORY_FEATURE_DIM = 6


def resample_sequence(
    landmarks_sequence: list[list[list[float]]],
    target_length: int = DEFAULT_TARGET_LENGTH,
) -> np.ndarray:
    """Resample a variable-length sequence of landmark frames to a fixed
    number of frames via linear interpolation along the time axis.

    Recorded gesture reps naturally vary in duration (a fast swipe vs a
    slow one) — resampling to a fixed length first means DTW only has
    to account for *shape* differences in the warping, not raw frame
    count, and template storage/comparison stays simple.

    Args:
        landmarks_sequence: list of frames, each 21x3 (x, y, z) — e.g.
            [frame.landmarks for frame in recorded_frames].
        target_length: number of frames to resample to.

    Returns:
        (target_length, 21, 3) float32 numpy array.
    """
    if len(landmarks_sequence) < 2:
        raise ValueError(
            f"Need at least 2 frames to resample a trajectory, got {len(landmarks_sequence)}"
        )

    sequence = np.asarray(landmarks_sequence, dtype=np.float32)  # (T, 21, 3)
    if sequence.shape[1:] != (NUM_LANDMARKS, 3):
        raise ValueError(
            f"Expected frames of shape ({NUM_LANDMARKS}, 3), got {sequence.shape[1:]}"
        )

    original_t = np.linspace(0.0, 1.0, num=sequence.shape[0])
    target_t = np.linspace(0.0, 1.0, num=target_length)

    # Interpolate each (landmark, coordinate) column independently —
    # np.interp is 1D-only, so we loop over the 21*3 = 63 columns rather
    # than reaching for a heavier multivariate interpolator we don't need.
    resampled = np.empty((target_length, NUM_LANDMARKS, 3), dtype=np.float32)
    for landmark_idx in range(NUM_LANDMARKS):
        for coord_idx in range(3):
            resampled[:, landmark_idx, coord_idx] = np.interp(
                target_t, original_t, sequence[:, landmark_idx, coord_idx]
            )

    return resampled


def _palm_centroid(frame: np.ndarray) -> np.ndarray:
    """frame: (21, 3) -> (3,) centroid of the palm reference landmarks."""
    return frame[list(_PALM_LANDMARK_IDXS)].mean(axis=0)


def extract_trajectory_features(
    resampled_sequence: np.ndarray, eps: float = 1e-6
) -> np.ndarray:
    """Turn a resampled (T, 21, 3) landmark sequence into a (T, 6)
    trajectory feature sequence — normalized palm position + velocity
    per timestep — ready for DTW comparison against stored templates.

    Uses the palm centroid rather than the full 21-point hand shape per
    frame, since dynamic gestures (swipes, waves) are defined by *where
    the hand moves*, not by fine finger shape at each instant. Keeping
    the per-frame feature low-dimensional also keeps DTW comparisons
    cheap and less prone to overfitting given only ~15 recorded samples
    per gesture.

    - Position is translation-invariant (relative to the first frame's
      centroid) and scale-invariant (divided by the average hand scale
      across the sequence, using the same wrist-to-middle-MCP reference
      as `static.normalize_static`) — so the same swipe shape matches
      regardless of where in frame, or how close to the camera, it was
      performed.
    - Velocity is the frame-to-frame delta of that normalized position,
      giving the matcher explicit motion-direction information — this
      is what actually distinguishes e.g. "swipe left" from "swipe
      right", which have near-identical *shape* but opposite direction.

    Args:
        resampled_sequence: (T, 21, 3) array, typically the output of
            `resample_sequence`.
        eps: floor for the scale denominator (see `normalize_static`).

    Returns:
        (T, 6) float32 numpy array; columns are
        (pos_x, pos_y, pos_z, vel_x, vel_y, vel_z).
    """
    if resampled_sequence.ndim != 3 or resampled_sequence.shape[1:] != (NUM_LANDMARKS, 3):
        raise ValueError(
            f"Expected (T, {NUM_LANDMARKS}, 3) array, got shape {resampled_sequence.shape}"
        )

    t = resampled_sequence.shape[0]

    # Per-frame hand-size scale (wrist-to-middle-MCP distance), averaged
    # across the sequence so one noisy frame doesn't skew the whole
    # trajectory's normalization.
    wrists = resampled_sequence[:, WRIST_IDX]
    middle_mcps = resampled_sequence[:, MIDDLE_MCP_IDX]
    per_frame_scale = np.linalg.norm(middle_mcps - wrists, axis=1)
    scale = float(max(per_frame_scale.mean(), eps))

    centroids = np.stack([_palm_centroid(resampled_sequence[i]) for i in range(t)])
    positions = (centroids - centroids[0]) / scale

    velocities = np.zeros_like(positions)
    velocities[1:] = positions[1:] - positions[:-1]

    return np.concatenate([positions, velocities], axis=1).astype(np.float32)