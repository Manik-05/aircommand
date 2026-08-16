"""
Interface stability test — not testing ML correctness (there's nothing
implemented yet), just that GestureEngine exposes the methods the backend
depends on with the expected call signatures. Prevents accidental breaking
renames.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import GestureEngine


def test_gesture_engine_has_expected_public_methods():
    engine = GestureEngine(data_dir="/tmp/aircommand_test_data")
    for method in [
        "subscribe",
        "start_recording",
        "capture_sample",
        "stop_recording",
        "train",
        "start_inference",
        "stop_inference",
        "delete_gesture",
    ]:
        assert hasattr(engine, method), f"GestureEngine missing {method}"


def test_subscribe_registers_callback():
    engine = GestureEngine(data_dir="/tmp/aircommand_test_data")
    received = []
    engine.subscribe(lambda event: received.append(event))
    engine._emit({"type": "gesture_detected", "gesture_id": "g1", "confidence": 0.9, "timestamp": 0.0})
    assert received == [{"type": "gesture_detected", "gesture_id": "g1", "confidence": 0.9, "timestamp": 0.0}]
