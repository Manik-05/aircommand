# dashboard (Developer B)

React + Vite + TypeScript.

## Run

```bash
cd dashboard
npm install
npm run dev
```

Talks to the backend only via `src/hooks/useGestureSocket.ts`, which
speaks the JSON protocol defined in `shared/protocol.md`. `src/types/protocol.ts`
is a copy of `shared/types.ts` — if you change the shared one, copy it here
again (or symlink if your OS/editor handles that fine).

## Layout

- `src/hooks/useGestureSocket.ts` — WebSocket connection + protocol types
- `src/components/` — gesture list, recording wizard, live recognition panel, action form (TODO)
