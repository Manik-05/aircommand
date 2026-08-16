"""
Simple JSON-file-backed gesture storage for the MVP. No DB server needed.
File layout (see docs/architecture.md section F):

  data/
    gestures.json          # index of Gesture metadata + actions
    samples/{gesture_id}/  # raw sample files (written by ml-engine)
    models/{gesture_id}/   # trained model artifacts (written by ml-engine)
"""
import json
from pathlib import Path


class GestureStore:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.index_path = self.data_dir / "gestures.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write({})

    def _read(self) -> dict:
        return json.loads(self.index_path.read_text())

    def _write(self, data: dict) -> None:
        self.index_path.write_text(json.dumps(data, indent=2, default=str))

    def list_gestures(self) -> list[dict]:
        return list(self._read().values())

    def get_gesture(self, gesture_id: str) -> dict | None:
        return self._read().get(gesture_id)

    def upsert_gesture(self, gesture: dict) -> None:
        data = self._read()
        data[gesture["id"]] = gesture
        self._write(data)

    def delete_gesture(self, gesture_id: str) -> None:
        data = self._read()
        data.pop(gesture_id, None)
        self._write(data)
