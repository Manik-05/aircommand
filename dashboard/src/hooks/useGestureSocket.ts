import { useEffect, useRef, useState, useCallback } from "react";
import type { ClientMessage, ServerMessage, Gesture } from "../types/protocol";

/**
 * Thin WebSocket client for shared/protocol.md. Owns connection state and
 * reconnect logic only — never reaches into ml-engine internals, only
 * speaks the JSON protocol.
 */
export function useGestureSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [gestures, setGestures] = useState<Gesture[]>([]);
  const [lastEvent, setLastEvent] = useState<ServerMessage | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);
      setLastEvent(msg);
      // TODO(Dev B): update `gestures` state properly based on msg.type
      // (training_complete, gesture_detected, etc.)
    };

    return () => ws.close();
  }, [url]);

  const send = useCallback((msg: ClientMessage) => {
    wsRef.current?.send(JSON.stringify(msg));
  }, []);

  return { connected, gestures, lastEvent, send };
}
