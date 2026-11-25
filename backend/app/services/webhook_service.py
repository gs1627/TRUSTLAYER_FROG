import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CallSession, WebhookEvent, safe_parse_utc_datetime
from app.schemas.contracts import EvidenceItemRead
from app.services.events import get_event_publisher, publish_evidence_added, publish_status_changed
from app.services.evidence_mapper import EvidenceMappingError, map_detectif_webhook_event
from app.services.evidence_repository import EvidenceRepository

logger = logging.getLogger(__name__)

_WEBHOOK_EVIDENCE_EVENTS = {
    "stream.deepfake.updated",
    "deepfake.completed",
    "stream.completed",
    "speaker.verification.completed",
    "speaker.verified",
    "verification.completed",
    "stream.verification.completed",
}


async def store_webhook_event(
    db: AsyncSession,
    *,
    delivery_id: str,
    payload: dict[str, Any],
) -> bool:
    """Persist a verified webhook delivery, lifecycle state, and mapped evidence."""
    existing = await db.scalar(
        select(WebhookEvent).where(WebhookEvent.delivery_id == delivery_id)
    )
    if existing:
        return True

    incoming_dt = safe_parse_utc_datetime(payload.get("created_at"))
    event = WebhookEvent(
        delivery_id=delivery_id,
        event_id=payload.get("id"),
        event_type=payload.get("type", "unknown"),
        event_created_at=incoming_dt,
        payload=payload,
        status="received",
    )
    db.add(event)

    event_type = payload.get("type")
    data = payload.get("data") or {}
    reference = data.get("reference")
    status_transition: tuple[str, str] | None = None
    created_evidence: list[EvidenceItemRead] = []

    if reference and isinstance(data, dict):
        session = await db.get(CallSession, reference)
        if session:
            prior_status = session.status
            if event_type in {"stream.started", "stream.completed", "stream.deepfake.updated"}:
                current_dt = safe_parse_utc_datetime(session.last_provider_event_at)
                raw_incoming = payload.get("created_at")
                is_newer = True
                if raw_incoming is not None and current_dt is not None:
                    # Preserve state if incoming timestamp string cannot be parsed safely.
                    is_newer = incoming_dt is not None and incoming_dt >= current_dt
                if is_newer:
                    if data.get("stream_id"):
                        session.provider_stream_id = data["stream_id"]
                    if event_type == "stream.started" and session.status != "completed":
                        session.status = "active"
                    elif event_type == "stream.completed":
                        session.status = "completed"
                    elif event_type == "stream.deepfake.updated":
                        raw_seq = data.get("sequence")
                        if type(raw_seq) is int and raw_seq > session.last_deepfake_sequence:
                            session.last_deepfake_sequence = raw_seq
                    session.last_provider_event_at = incoming_dt or current_dt
                    if session.status != prior_status:
                        status_transition = (prior_status, session.status)

            if event_type in _WEBHOOK_EVIDENCE_EVENTS:
                try:
                    mapped_items = map_detectif_webhook_event(
                        payload,
                        call_id=session.call_id,
                        delivery_id=delivery_id,
                        speaker_id=session.speaker_id,
                    )
                except EvidenceMappingError as exc:
                    logger.warning("Skipping webhook evidence normalization for %s: %s", event_type, exc)
                    mapped_items = []

                for mapped in mapped_items:
                    saved_item, created = await EvidenceRepository.create(
                        db,
                        call_id=session.call_id,
                        payload=mapped,
                        commit=False,
                    )
                    if created:
                        created_evidence.append(EvidenceItemRead.model_validate(saved_item))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return True

    publisher = get_event_publisher()
    if status_transition is not None and reference:
        await publish_status_changed(
            publisher,
            call_id=reference,
            previous_status=status_transition[0],
            status=status_transition[1],
        )
    for read_item in created_evidence:
        await publish_evidence_added(publisher, item=read_item)
    return False
