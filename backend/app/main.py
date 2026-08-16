"""
AirCommand backend entrypoint.

Owns: WebSocket/REST surface, gesture+action persistence, wiring
GestureEngine events -> broadcast -> action execution. Imports ml-engine
ONLY through GestureEngine's public methods (see ml-engine/engine.py).

Run: uvicorn app.main:app --reload --port 8000   (from backend/ dir)
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# make ml-engine and shared importable without packaging them yet (MVP shortcut)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml-engine"))

from app.ws.router import router as ws_router  # noqa: E402
from app.api.routes import router as rest_router  # noqa: E402

app = FastAPI(title="AirCommand Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(rest_router)


@app.get("/health")
def health():
    return {"status": "ok"}
