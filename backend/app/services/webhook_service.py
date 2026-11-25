from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CallSession, WebhookEvent


async def store_webhook_event(
    db: AsyncSession,
    *,
    delivery_id: str,
    payload: dict[str, Any],
) -> bool:
    """Persist a verified webhook delivery; return True if it was a duplicate.

    Event persistence and the small call-session lifecycle update are committed
    together so the webhook row cannot be accepted while its state update is lost.
    """
    existing = await db.scalar(
        select(WebhookEvent).where(WebhookEvent.delivery_id == delivery_id)
    )
    if existing:
        return True

    event = WebhookEvent(
        delivery_id=delivery_id,
        event_id=payload.get("id"),
        event_type=payload.get("type", "unknown"),
        event_created_at=payload.get("created_at"),
        payload=payload,
        status="received",
    )
    db.add(event)

    event_type = payload.get("type")
    data = payload.get("data") or {}
    reference = data.get("reference")
    if reference and event_type in {"stream.started", "stream.completed", "stream.deepfake.updated"}:
        session = await db.get(CallSession, reference)
        if session:
            incoming_at = payload.get("created_at")
            current_at = session.last_provider_event_at
            is_newer = True
            if incoming_at and current_at:
                try:
                    incoming_dt = datetime.fromisoformat(incoming_at.replace("Z", "+00:00"))
                    current_dt = datetime.fromisoformat(current_at.replace("Z", "+00:00"))
                    is_newer = incoming_dt >= current_dt
                except (ValueError, TypeError):
                    # If timestamps cannot be parsed, preserve existing state rather
                    # than risk moving a completed session backwards.
                    is_newer = False
            if is_newer:
                if data.get("stream_id"):
                    session.provider_stream_id = data["stream_id"]
                if event_type == "stream.started" and session.status != "completed":
                    session.status = "active"
                elif event_type == "stream.completed":
                    session.status = "completed"
                elif event_type == "stream.deepfake.updated":
                    sequence = int(data.get("sequence") or 0)
                    if sequence > session.last_deepfake_sequence:
                        session.last_deepfake_sequence = sequence
                session.last_provider_event_at = incoming_at or current_at

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return True
    return False
