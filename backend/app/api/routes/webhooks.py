import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import WebhookSignatureError, verify_detectif_webhook_signature
from app.db.session import get_db
from app.schemas.contracts import WebhookAcceptedResponse
from app.services.webhook_service import store_webhook_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/detectifai", response_model=WebhookAcceptedResponse, status_code=202)
async def receive_detectifai_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    webhook_id: str | None = Header(default=None, alias="webhook-id"),
    webhook_timestamp: str | None = Header(default=None, alias="webhook-timestamp"),
    webhook_signature: str | None = Header(default=None, alias="webhook-signature"),
):
    settings = get_settings()
    if not settings.detectif_webhook_secret:
        raise HTTPException(status_code=503, detail="DETECTIF_WEBHOOK_SECRET is not configured")

    raw_body = await request.body()
    signature_headers = {
        "webhook-id": webhook_id or "",
        "webhook-timestamp": webhook_timestamp or "",
        "webhook-signature": webhook_signature or "",
    }
    try:
        verify_detectif_webhook_signature(
            secret=settings.detectif_webhook_secret,
            headers=signature_headers,
            raw_body=raw_body,
            tolerance_seconds=settings.webhook_tolerance_seconds,
        )
    except WebhookSignatureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc

    if not isinstance(payload, dict) or not payload.get("type"):
        raise HTTPException(status_code=400, detail="Webhook event must be a JSON object containing type")

    duplicate = await store_webhook_event(db, delivery_id=webhook_id or "", payload=payload)
    return WebhookAcceptedResponse(
        accepted=True,
        duplicate=duplicate,
        delivery_id=webhook_id or "",
    )
