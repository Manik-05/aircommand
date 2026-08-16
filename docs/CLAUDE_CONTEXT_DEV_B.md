# Claude context — Developer B (Backend + Dashboard)

Paste this whole file as your first message to Claude in your own session
to get it up to speed, then attach/paste the files it references.

---

## Project

**AirCommand** — real-time, ML-powered touchless computer control via
webcam hand gestures, with a killer feature: users can teach it their own
custom gestures (record ~15 reps, system trains a model, user assigns an
action).

Two developers, working independently on different machines, GitHub repo
`aircommand`. **I am Developer B.**

## My ownership

- `backend/`: FastAPI app, WebSocket endpoint implementing
  `shared/protocol.md`, REST endpoints, gesture/action JSON storage
  (`app/storage/store.py`), action execution (`app/actions/executor.py` —
  keyboard via `pynput` for MVP).
- `dashboard/`: React + Vite + TS. Gesture list, create-gesture wizard
  with webcam preview, recording UI, live recognition/confidence panel,
  action assignment form. WebSocket client hook
  (`dashboard/src/hooks/useGestureSocket.ts`).
- Later (Phase 2): `browser-extension/`, subscribing to the same
  WebSocket events for tab/scroll control.

## What I must NOT do

Never import anything from `ml-engine/` except `GestureEngine` (from
`ml-engine/engine.py`), and only call its documented public methods
(`start_recording`, `capture_sample`, `stop_recording`, `train`,
`start_inference`, `stop_inference`, `subscribe`, `delete_gesture`). I
never reach into `ml-engine/capture`, `features`, `models`, `training`,
or `inference` directly — those are Developer A's internals and can
change shape without warning me, as long as `GestureEngine`'s interface
stays stable.

## The contract I build against

`shared/protocol.md` defines every WebSocket message type in both
directions, plus REST endpoints and error codes. `shared/schemas.py`
(Python, used directly by backend) and `shared/types.ts` (TypeScript,
copied into `dashboard/src/types/protocol.ts`) define the data shapes.
I don't own `GestureEngine`'s internals, but I do co-own `shared/` with
Dev A — changes there need both our review.

## Files to give Claude in your session

1. This file.
2. `docs/architecture.md` (full architecture — sections D, E, I, J
   matter most for me).
3. `shared/protocol.md`, `shared/schemas.py`, `shared/types.ts`.
4. `backend/app/main.py`, `backend/app/ws/router.py`,
   `backend/app/api/routes.py`, `backend/app/storage/store.py`,
   `backend/app/actions/executor.py` (current scaffold).
5. `dashboard/src/App.tsx`, `dashboard/src/hooks/useGestureSocket.ts`
   (current scaffold).
6. `ml-engine/engine.py` — I need to see this to know what I'm calling,
   but I never edit it.

## My task list (in order)

1. Confirm backend scaffold runs: `uvicorn app.main:app --reload --port
   8000` from `backend/`, hit `GET /health`.
2. `app/ws/router.py`: the current version calls `GestureEngine`
   synchronously and has a TODO about bridging sync callbacks into the
   async WebSocket send — resolve this properly (likely an `asyncio.Queue`
   the callback pushes into, consumed by a loop that sends over the
   socket) once Dev A's real implementation lands. Coordinate with Dev A
   before changing `GestureEngine`'s calling convention.
3. `app/storage/store.py`: already functional (JSON file index). Extend
   as needed (e.g. storing accuracy alongside `model_ref`).
4. `app/actions/executor.py`: keyboard done for MVP; leave
   mouse/browser/app as `NotImplementedError` until Phase 2.
5. Dashboard: gesture list (wire real state updates in
   `useGestureSocket`'s `onmessage` handler — currently just stores
   `lastEvent`), create-gesture wizard with webcam preview (`<video>` +
   canvas overlay for landmarks, using `landmark_frame` events), record
   button → `capture_sample` messages, train button → `start_training`,
   live recognition panel showing `gesture_detected` events + confidence,
   action assignment form → `assign_action`.
6. Build a mock WebSocket server (or a small script replaying canned
   protocol messages) so I can build/test the dashboard without Dev A's
   ML implementation being finished.
7. Tests: contract tests asserting WS messages match `shared/schemas.py`;
   dashboard component tests; one Playwright/Cypress happy-path test
   against the mock server.

## Working agreement

- Branch naming: `feature/backend-<topic>` / `feature/dashboard-<topic>`.
- I don't touch `shared/protocol.md`/`schemas.py`/`types.ts` without a PR
  both of us review — those are the contract.
- I don't need Dev A's real ML implementation to make progress — build
  against the mock server and `GestureEngine`'s stub interface.
