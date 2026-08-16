import { useGestureSocket } from "./hooks/useGestureSocket";

export default function App() {
  const { connected, gestures, lastEvent, send } = useGestureSocket("ws://localhost:8000/ws");

  return (
    <div style={{ fontFamily: "sans-serif", padding: 24 }}>
      <h1>AirCommand</h1>
      <p>Backend: {connected ? "connected" : "disconnected"}</p>

      <h2>Gestures</h2>
      <ul>
        {gestures.map((g) => (
          <li key={g.id}>{g.name}</li>
        ))}
      </ul>
      {/* TODO(Dev B): create-gesture wizard, webcam recording UI,
          live confidence panel, action assignment form */}

      <button
        onClick={() =>
          send({ type: "start_recording", gesture_name: "Test Gesture", gesture_type: "static" })
        }
      >
        Start Recording (test)
      </button>

      <pre>{lastEvent ? JSON.stringify(lastEvent, null, 2) : "no events yet"}</pre>
    </div>
  );
}
