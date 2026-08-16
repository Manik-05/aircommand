# AirCommand

Real-time, customizable, ML-powered touchless computer interaction via webcam
hand gestures — including user-defined gestures.

Full architecture and rationale: [`docs/architecture.md`](docs/architecture.md)
Protocol contract: [`shared/protocol.md`](shared/protocol.md)

## Repo layout

```
ml-engine/          Dev A — MediaPipe, feature extraction, training, inference
backend/            FastAPI + WebSocket server, storage, action execution
dashboard/          Dev B — React + Vite + TS UI
browser-extension/  Phase 2
shared/             Protocol + data model contract (both devs)
docs/               Architecture doc
```

## Setup

**Python (ml-engine + backend), one env for both:**
```bash
conda env create -f environment.yml
conda activate aircommand
```

**Dashboard:**
```bash
cd dashboard
npm install
```

## Run everything locally

```bash
# terminal 1
conda activate aircommand
cd backend
uvicorn app.main:app --reload --port 8000

# terminal 2
cd dashboard
npm run dev
```

Dashboard: http://localhost:5173 — Backend: http://localhost:8000/health

## Contributing

See `docs/architecture.md` sections F (Git workflow) and J (integration
strategy). Short version: branch off `develop`, changes touching
`shared/` need both devs' review.
