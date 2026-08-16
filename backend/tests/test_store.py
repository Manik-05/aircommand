import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.storage.store import GestureStore


def test_store_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = GestureStore(data_dir=tmp)
        assert store.list_gestures() == []

        gesture = {"id": "g1", "name": "Next Tab", "gesture_type": "dynamic"}
        store.upsert_gesture(gesture)

        assert store.get_gesture("g1") == gesture
        assert len(store.list_gestures()) == 1

        store.delete_gesture("g1")
        assert store.get_gesture("g1") is None
