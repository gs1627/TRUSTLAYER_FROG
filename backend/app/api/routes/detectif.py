import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile

from app.api.audio import read_audio
from app.core.config import get_settings
from app.core.auth import require_backend_access
from app.schemas.contracts import ProviderOperationResponse
from app.services.detectif_client import (
    DetectifAPIError,
    DetectifClient,
    DetectifNotConfiguredError,
)

router = APIRouter(prefix="/detectif", tags=["DetectifAI"], dependencies=[Depends(require_backend_access)])
settings = get_settings()
client = DetectifClient(settings)

def provider_error(exc: DetectifAPIError) -> HTTPException:
    # Preserve provider status and stable error details while avoiding credential leakage.
    status_code = exc.status_code if 400 <= exc.status_code < 600 else 502
    return HTTPException(status_code=status_code, detail={"provider": "detectifai", "error": exc.detail})


@router.post("/deepfake", response_model=ProviderOperationResponse)
async def detect_deepfake(
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    content = await read_audio(file)
    try:
        result = await client.detect_deepfake(
            filename=file.filename or "audio-upload",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc
    return ProviderOperationResponse(
        operation="deepfake_detection",
        request_id=result.get("request_id"),
        operation_id=result.get("operation_id"),
        raw=result,
    )


@router.post("/speakers/enroll", response_model=ProviderOperationResponse)
async def enroll_speaker(
    speaker_id: str = Form(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]{1,64}$"),
    display_name: str | None = Form(default=None, max_length=128),
    consent_confirmed: bool = Form(...),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Explicit speaker consent is required before enrollment")
    content = await read_audio(file)
    try:
        result = await client.enroll_speaker(
            speaker_id=speaker_id,
            display_name=display_name,
            filename=file.filename or "enrollment-audio",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc
    return ProviderOperationResponse(
        operation="speaker_enrollment",
        request_id=result.get("request_id"),
        operation_id=result.get("operation_id"),
        raw=result,
    )


@router.post("/speakers/verify", response_model=ProviderOperationResponse)
async def verify_speaker(
    speaker_id: str = Form(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]{1,64}$"),
    detect_deepfake: bool = Form(default=True),
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    content = await read_audio(file)
    try:
        result = await client.verify_speaker(
            speaker_id=speaker_id,
            detect_deepfake=detect_deepfake,
            filename=file.filename or "verification-audio",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        )
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc
    return ProviderOperationResponse(
        operation="speaker_verification",
        request_id=result.get("request_id"),
        operation_id=result.get("operation_id"),
        raw=result,
    )


@router.get("/operations/{operation_id}")
async def get_operation(operation_id: str):
    try:
        return await client.get_operation(operation_id)
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc


@router.get("/speakers")
async def list_speakers(limit: int = 20, cursor: str | None = None):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try:
        return await client.list_speakers(limit=limit, cursor=cursor)
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc


@router.delete("/speakers/{speaker_id}")
async def delete_speaker(speaker_id: str):
    if not __import__("re").fullmatch(r"[A-Za-z0-9_.:-]{1,64}", speaker_id):
        raise HTTPException(status_code=422, detail="Invalid speaker_id format")
    try:
        return await client.delete_speaker(speaker_id)
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc


@router.get("/streams/{stream_id}")
async def get_stream(stream_id: str):
    if not stream_id or len(stream_id) > 64:
        raise HTTPException(status_code=422, detail="Invalid stream_id")
    try:
        return await client.get_stream(stream_id)
    except DetectifNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectifAPIError as exc:
        raise provider_error(exc) from exc
