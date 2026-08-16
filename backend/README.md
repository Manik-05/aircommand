# backend (Developer B, with GestureEngine calls from Dev A's package)

FastAPI + WebSocket server implementing `shared/protocol.md`. Imports
`GestureEngine` from `ml-engine` only through its public methods.

## Run

```bash
conda activate aircommand
cd backend
uvicorn app.main:app --reload --port 8000
```

## Layout

- `app/ws/router.py` — WebSocket endpoint, protocol message routing
- `app/api/routes.py` — REST endpoints (non-realtime)
- `app/storage/store.py` — JSON-file gesture persistence
- `app/actions/executor.py` — runs the assigned Action (keyboard for MVP)
