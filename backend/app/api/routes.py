from fastapi import APIRouter, HTTPException

from app.storage.store import GestureStore

router = APIRouter()
store = GestureStore()


@router.get("/gestures")
def list_gestures():
    return store.list_gestures()


@router.get("/gestures/{gesture_id}")
def get_gesture(gesture_id: str):
    gesture = store.get_gesture(gesture_id)
    if gesture is None:
        raise HTTPException(status_code=404, detail="gesture not found")
    return gesture


@router.delete("/gestures/{gesture_id}", status_code=204)
def delete_gesture(gesture_id: str):
    store.delete_gesture(gesture_id)


@router.get("/models/{gesture_id}/status")
def model_status(gesture_id: str):
    gesture = store.get_gesture(gesture_id)
    if gesture is None:
        raise HTTPException(status_code=404, detail="gesture not found")
    return {"trained": gesture.get("model_ref") is not None, "accuracy": gesture.get("accuracy")}
