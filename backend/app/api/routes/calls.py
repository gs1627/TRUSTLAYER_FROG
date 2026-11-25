from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import authenticate_websocket, require_backend_access
from app.db.models import CallSession
from app.db.session import AsyncSessionLocal
from app.services.detectif_stream import DetectifStreamError, relay_browser_audio_to_detectif

router = APIRouter(prefix="/calls", tags=["calls"])


class StartCallRequest(BaseModel):
    call_id: str = Field(min_length=3, max_length=128)
    speaker_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]{1,64}$")


@router.post("/sessions", dependencies=[Depends(require_backend_access)])
async def create_call_session(payload: StartCallRequest):
    async with AsyncSessionLocal() as db:
        existing = await db.get(CallSession, payload.call_id)
        if existing:
            raise HTTPException(status_code=409, detail="call_id already exists")
        session = CallSession(call_id=payload.call_id, speaker_id=payload.speaker_id, status="created")
        db.add(session)
        await db.commit()
    return {"call_id": payload.call_id, "speaker_id": payload.speaker_id, "status": "created"}


@router.websocket("/ws/{call_id}")
async def live_call_websocket(websocket: WebSocket, call_id: str):
    await websocket.accept()
    if not await authenticate_websocket(websocket):
        await websocket.send_json({"type": "error", "code": "unauthorized"})
        await websocket.close(code=4401)
        return
    async with AsyncSessionLocal() as db:
        session = await db.get(CallSession, call_id)
        if not session:
            await websocket.send_json({"type": "error", "code": "call_session_not_found"})
            await websocket.close(code=4404)
            return
        speaker_id = session.speaker_id
        session.status = "connecting"
        await db.commit()

    async def persist_provider_message(payload: dict) -> None:
        async with AsyncSessionLocal() as db:
            current = await db.get(CallSession, call_id)
            if not current:
                return
            message_type = payload.get("type")
            if payload.get("stream_id"):
                current.provider_stream_id = payload["stream_id"]
            if message_type == "ready":
                current.status = "active"
            elif message_type == "completed":
                current.status = "completed"
            await db.commit()

    try:
        await relay_browser_audio_to_detectif(
            browser_ws=websocket,
            call_id=call_id,
            speaker_id=speaker_id,
            on_provider_message=persist_provider_message,
        )
        async with AsyncSessionLocal() as db:
            session = await db.get(CallSession, call_id)
            if session and session.status != "completed":
                session.status = "ended"
                await db.commit()
    except DetectifStreamError as exc:
        try:
            await websocket.send_json({"type": "error", "code": "detectif_stream_error", "message": str(exc)})
            await websocket.close(code=1011)
        except RuntimeError:
            pass
    except WebSocketDisconnect:
        async with AsyncSessionLocal() as db:
            session = await db.get(CallSession, call_id)
            if session:
                session.status = "disconnected"
                await db.commit()
