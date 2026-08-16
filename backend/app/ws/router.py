"""
WebSocket endpoint implementing shared/protocol.md.

This routes ClientMessage payloads to GestureEngine calls, and forwards
GestureEngine's emitted events back down the socket as ServerMessage
payloads. It should NOT contain any ML/feature logic — that all lives in
ml-engine and is reached only through GestureEngine's public methods.
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engine import GestureEngine  # from ml-engine/, added to sys.path in main.py

router = APIRouter()
gesture_engine = GestureEngine(data_dir="./data")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def send_event(event: dict):
        await websocket.send_text(json.dumps(event))

    # NOTE: GestureEngine.subscribe expects a sync callback in the current
    # stub. Once Dev A's real implementation exists, decide together
    # whether this needs to go through an asyncio queue instead of calling
    # `send_event` directly from a non-async context. Flag this in review.
    gesture_engine.subscribe(lambda event: None)  # TODO(Dev A+B): wire real bridging

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_event({"code": "INVALID_MESSAGE", "type": "error", "message": "not valid JSON"})
                continue

            msg_type = msg.get("type")

            try:
                if msg_type == "start_recording":
                    gesture_id = gesture_engine.start_recording(
                        msg["gesture_name"], msg["gesture_type"]
                    )
                    await send_event({"type": "recording_started", "gesture_id": gesture_id})

                elif msg_type == "capture_sample":
                    gesture_engine.capture_sample()

                elif msg_type == "stop_recording":
                    gesture_engine.stop_recording(msg["gesture_id"])

                elif msg_type == "start_training":
                    result = gesture_engine.train(msg["gesture_id"])
                    await send_event({"type": "training_complete", **result})

                elif msg_type == "assign_action":
                    # TODO(Dev B): persist action via app/storage
                    pass

                elif msg_type == "start_inference":
                    gesture_engine.start_inference()

                elif msg_type == "stop_inference":
                    gesture_engine.stop_inference()

                elif msg_type == "delete_gesture":
                    gesture_engine.delete_gesture(msg["gesture_id"])

                else:
                    await send_event(
                        {"type": "error", "code": "INVALID_MESSAGE", "message": f"unknown type {msg_type}"}
                    )

            except NotImplementedError:
                await send_event(
                    {"type": "error", "code": "TRAINING_FAILED", "message": f"{msg_type} not implemented yet"}
                )

    except WebSocketDisconnect:
        gesture_engine.stop_inference()
