import logging

from fastapi import APIRouter, Body, Depends, Query, Response, WebSocket, WebSocketDisconnect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import authenticate_websocket, require_backend_access
from app.core.errors import AppAPIError
from app.db.models import CallSession, SpeakerProfile, utc_now
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.contracts import (
    CallSessionCreate,
    CallSessionDetailRead,
    CallSessionEndRequest,
    CallSessionRead,
    ErrorResponse,
    EvidenceCheckType,
    EvidenceItemCreate,
    EvidenceItemRead,
    PaginatedCallSessionsResponse,
    PaginatedEvidenceResponse,
    PaginatedTrustAssessmentsResponse,
    TrustAssessmentCreate,
    TrustAssessmentRead,
)
from app.services.call_session_service import CallSessionService
from app.services.detectif_stream import DetectifStreamError, relay_browser_audio_to_detectif
from app.services.events import (
    EventPublisher,
    get_event_publisher,
    publish_evidence_added,
    publish_status_changed,
    publish_trust_updated,
)
from app.services.evidence_mapper import EvidenceMappingError, map_detectif_websocket_message
from app.services.evidence_repository import EvidenceRepository
from app.services.trust_assessment_repository import TrustAssessmentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["calls"])

StartCallRequest = CallSessionCreate


def _upsert_enrollment_consent(
    profile: SpeakerProfile | None,
    *,
    speaker_id: str,
    display_name: str | None,
    now,
) -> SpeakerProfile | None:
    if profile is None:
        return SpeakerProfile(
            speaker_id=speaker_id,
            display_name=display_name,
            consent_confirmed=True,
            consent_recorded_at=now,
            enrollment_status="pending",
        )
    profile.consent_confirmed = True
    profile.consent_recorded_at = now
    if profile.enrollment_status == "deleted":
        profile.enrollment_status = "pending"
        profile.sample_count = 0
    if display_name is not None:
        profile.display_name = display_name
    return None


def _build_call_session(payload: StartCallRequest, now) -> CallSession:
    return CallSession(
        call_id=payload.call_id,
        speaker_id=payload.speaker_id,
        checks_mode=payload.checks_mode,
        consent_confirmed=payload.consent_confirmed,
        consent_recorded_at=now if payload.consent_confirmed else None,
        status="created",
    )


@router.post("/sessions", dependencies=[Depends(require_backend_access)])
async def create_call_session(
    payload: StartCallRequest,
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
):
    now = utc_now()
    for attempt in range(2):
        existing = await db.get(CallSession, payload.call_id)
        if existing:
            raise AppAPIError(
                status_code=409,
                code="call_session_already_exists",
                message="call_id already exists",
                details={"call_id": payload.call_id},
            )

        if payload.checks_mode == "deepfake,enroll" and payload.speaker_id and payload.consent_confirmed:
            profile = await db.get(SpeakerProfile, payload.speaker_id)
            created_profile = _upsert_enrollment_consent(
                profile,
                speaker_id=payload.speaker_id,
                display_name=payload.display_name,
                now=now,
            )
            if created_profile is not None:
                db.add(created_profile)

        db.add(_build_call_session(payload, now))
        try:
            await db.commit()
            break
        except IntegrityError as exc:
            await db.rollback()
            if await db.get(CallSession, payload.call_id) is not None:
                raise AppAPIError(
                    status_code=409,
                    code="call_session_already_exists",
                    message="call_id already exists",
                    details={"call_id": payload.call_id},
                ) from exc
            # Retry once if simultaneous new SpeakerProfile creation caused the conflict.
            if (
                attempt == 0
                and payload.checks_mode == "deepfake,enroll"
                and payload.speaker_id
                and await db.get(SpeakerProfile, payload.speaker_id) is not None
            ):
                continue
            raise

    await publish_status_changed(
        publisher,
        call_id=payload.call_id,
        previous_status=None,
        status="created",
    )
    return {
        "call_id": payload.call_id,
        "speaker_id": payload.speaker_id,
        "checks_mode": payload.checks_mode,
        "status": "created",
    }


@router.get(
    "/sessions",
    response_model=PaginatedCallSessionsResponse,
    dependencies=[Depends(require_backend_access)],
)
async def list_call_sessions(
    status: str | None = Query(default=None),
    speaker_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await CallSessionService.list_sessions(
        db,
        status=status,
        speaker_id=speaker_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedCallSessionsResponse(
        items=[CallSessionRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sessions/{call_id}",
    response_model=CallSessionDetailRead,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_backend_access)],
)
async def get_call_session(call_id: str, db: AsyncSession = Depends(get_db)):
    return await CallSessionService.get_session_detail(db, call_id=call_id)


@router.post(
    "/sessions/{call_id}/end",
    response_model=CallSessionRead,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_backend_access)],
)
async def end_call_session(
    call_id: str,
    payload: CallSessionEndRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
):
    reason = payload.reason if payload is not None else None
    session, previous_status = await CallSessionService.end_session(
        db,
        call_id=call_id,
        reason=reason,
    )
    if previous_status is not None:
        await publish_status_changed(
            publisher,
            call_id=session.call_id,
            previous_status=previous_status,
            status=session.status,
            ended_reason=session.ended_reason,
        )
    return CallSessionRead.model_validate(session)


@router.get(
    "/sessions/{call_id}/evidence",
    response_model=PaginatedEvidenceResponse,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_backend_access)],
)
async def list_call_evidence(
    call_id: str,
    check_type: EvidenceCheckType | None = Query(default=None),
    provider: str | None = Query(default=None),
    is_final: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await EvidenceRepository.list_for_call(
        db,
        call_id=call_id,
        check_type=check_type,
        provider=provider,
        is_final=is_final,
        limit=limit,
        offset=offset,
    )
    return PaginatedEvidenceResponse(
        items=[EvidenceItemRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/sessions/{call_id}/evidence",
    response_model=EvidenceItemRead,
    status_code=201,
    responses={
        200: {"model": EvidenceItemRead, "description": "Duplicate source_event_key returned existing evidence"},
        201: {"model": EvidenceItemRead, "description": "Evidence created"},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_backend_access)],
)
async def append_call_evidence(
    call_id: str,
    payload: EvidenceItemCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
):
    item, created = await EvidenceRepository.create(
        db,
        call_id=call_id,
        payload=payload,
        commit=True,
    )
    read_item = EvidenceItemRead.model_validate(item)
    if created:
        response.status_code = 201
        await publish_evidence_added(publisher, item=read_item)
    else:
        response.status_code = 200
    return read_item


@router.post(
    "/sessions/{call_id}/trust-assessments",
    response_model=TrustAssessmentRead,
    status_code=201,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_backend_access)],
)
async def create_trust_assessment(
    call_id: str,
    payload: TrustAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    publisher: EventPublisher = Depends(get_event_publisher),
):
    assessment = await TrustAssessmentRepository.create(
        db,
        call_id=call_id,
        payload=payload,
        commit=True,
    )
    read_assessment = TrustAssessmentRead.model_validate(assessment)
    await publish_trust_updated(publisher, assessment=read_assessment)
    return read_assessment


@router.get(
    "/sessions/{call_id}/trust-assessments/latest",
    response_model=TrustAssessmentRead,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_backend_access)],
)
async def get_latest_trust_assessment(call_id: str, db: AsyncSession = Depends(get_db)):
    assessment = await TrustAssessmentRepository.get_latest_for_call(db, call_id=call_id)
    return TrustAssessmentRead.model_validate(assessment)


@router.get(
    "/sessions/{call_id}/trust-assessments",
    response_model=PaginatedTrustAssessmentsResponse,
    responses={404: {"model": ErrorResponse}},
    dependencies=[Depends(require_backend_access)],
)
async def list_trust_assessments(
    call_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await TrustAssessmentRepository.list_for_call(
        db,
        call_id=call_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedTrustAssessmentsResponse(
        items=[TrustAssessmentRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.websocket("/ws/{call_id}")
async def live_call_websocket(websocket: WebSocket, call_id: str):
    await websocket.accept()
    if not await authenticate_websocket(websocket):
        await websocket.send_json({"type": "error", "code": "unauthorized"})
        await websocket.close(code=4401)
        return
    publisher = get_event_publisher()
    async with AsyncSessionLocal() as db:
        session = await db.get(CallSession, call_id)
        if not session:
            await websocket.send_json({"type": "error", "code": "call_session_not_found"})
            await websocket.close(code=4404)
            return
        speaker_id = session.speaker_id
        previous_status = session.status
        session.status = "connecting"
        await db.commit()
    if previous_status != "connecting":
        await publish_status_changed(
            publisher,
            call_id=call_id,
            previous_status=previous_status,
            status="connecting",
        )

    async def persist_provider_message(payload: dict) -> None:
        created_evidence: list[EvidenceItemRead] = []
        status_transition: tuple[str, str] | None = None
        async with AsyncSessionLocal() as db:
            current = await db.get(CallSession, call_id)
            if not current:
                return
            prior_status = current.status
            message_type = payload.get("type")
            if payload.get("stream_id"):
                current.provider_stream_id = payload["stream_id"]
            if message_type == "ready" and current.status != "completed":
                current.status = "active"
            elif message_type == "completed":
                current.status = "completed"
            seq_val = payload.get("sequence")
            if type(seq_val) is int and seq_val > current.last_deepfake_sequence:
                current.last_deepfake_sequence = seq_val
            current.last_provider_event_at = utc_now()
            if current.status != prior_status:
                status_transition = (prior_status, current.status)

            try:
                mapped_items = map_detectif_websocket_message(
                    payload,
                    call_id=call_id,
                    speaker_id=current.speaker_id,
                    provider_stream_id=current.provider_stream_id,
                )
            except EvidenceMappingError as exc:
                logger.warning("Skipping unmapped WS message for call %s: %s", call_id, exc)
                mapped_items = []

            for mapped in mapped_items:
                saved_item, created = await EvidenceRepository.create(
                    db,
                    call_id=call_id,
                    payload=mapped,
                    commit=False,
                )
                if created:
                    created_evidence.append(EvidenceItemRead.model_validate(saved_item))

            await db.commit()

        if status_transition is not None:
            await publish_status_changed(
                publisher,
                call_id=call_id,
                previous_status=status_transition[0],
                status=status_transition[1],
            )
        for read_item in created_evidence:
            await publish_evidence_added(publisher, item=read_item)

    try:
        await relay_browser_audio_to_detectif(
            browser_ws=websocket,
            call_id=call_id,
            speaker_id=speaker_id,
            on_provider_message=persist_provider_message,
        )
        ended_transition: tuple[str, str] | None = None
        async with AsyncSessionLocal() as db:
            session = await db.get(CallSession, call_id)
            if session and session.status != "completed":
                ended_transition = (session.status, "ended")
                session.status = "ended"
                await db.commit()
        if ended_transition is not None:
            await publish_status_changed(
                publisher,
                call_id=call_id,
                previous_status=ended_transition[0],
                status=ended_transition[1],
            )
    except DetectifStreamError as exc:
        try:
            await websocket.send_json({"type": "error", "code": "detectif_stream_error", "message": str(exc)})
            await websocket.close(code=1011)
        except RuntimeError:
            pass
    except WebSocketDisconnect:
        disc_transition: tuple[str, str] | None = None
        async with AsyncSessionLocal() as db:
            session = await db.get(CallSession, call_id)
            if session and session.status != "disconnected":
                disc_transition = (session.status, "disconnected")
                session.status = "disconnected"
                await db.commit()
        if disc_transition is not None:
            await publish_status_changed(
                publisher,
                call_id=call_id,
                previous_status=disc_transition[0],
                status=disc_transition[1],
            )
