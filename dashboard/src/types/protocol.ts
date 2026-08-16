/**
 * Single source of truth for AirCommand data shapes (TypeScript side).
 * Mirrors shared/schemas.py by hand — keep both in sync.
 * See shared/protocol.md for the message contract these are used in.
 */

export type GestureType = "static" | "dynamic";
export type ActionType = "keyboard" | "mouse" | "browser" | "app";

export interface Sample {
  landmarks_sequence: number[][][]; // frames x 21 points x (x, y, z)
  duration_ms: number;
  recorded_at: string; // ISO datetime
}

export interface Action {
  type: ActionType;
  payload: Record<string, unknown>;
  // keyboard: { keys: string[] }
  // mouse:    { action: string; button?: string }
  // browser:  { command: string }
  // app:      { app: string; command: string }
}

export interface Gesture {
  id: string;
  name: string;
  gesture_type: GestureType;
  samples: Sample[];
  model_ref: string | null;
  action: Action | null;
  confidence_threshold: number;
  created_at: string;
}

export interface GestureEvent {
  gesture_id: string;
  confidence: number;
  timestamp: number;
}

export interface TrainingResult {
  gesture_id: string;
  accuracy: number;
  model_path: string;
  trained_at: string;
}

// --- Client -> Server message payloads ---
export type ClientMessage =
  | { type: "start_recording"; gesture_name: string; gesture_type: GestureType }
  | { type: "capture_sample" }
  | { type: "stop_recording"; gesture_id: string }
  | { type: "start_training"; gesture_id: string }
  | { type: "assign_action"; gesture_id: string; action: Action }
  | { type: "start_inference" }
  | { type: "stop_inference" }
  | { type: "delete_gesture"; gesture_id: string };

// --- Server -> Client message payloads ---
export type ServerMessage =
  | { type: "recording_started"; gesture_id: string }
  | { type: "landmark_frame"; landmarks: number[][]; timestamp: number }
  | { type: "sample_captured"; gesture_id: string; count: number; target: number }
  | { type: "training_progress"; gesture_id: string; status: "training"; progress: number }
  | { type: "training_complete"; gesture_id: string; accuracy: number; model_path: string }
  | { type: "gesture_detected"; gesture_id: string; confidence: number; timestamp: number }
  | { type: "action_executed"; gesture_id: string; action: Action }
  | { type: "error"; code: string; message: string };

// --- Constants (must match shared/protocol.md) ---
export const MIN_SAMPLES_PER_GESTURE = 10;
export const DEFAULT_TARGET_SAMPLES = 15;
export const DEFAULT_CONFIDENCE_THRESHOLD = 0.85;
export const INFERENCE_COOLDOWN_MS = 700;
