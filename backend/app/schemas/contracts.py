from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    environment: str
    database: Literal["connected", "unavailable"]
    detectif_configured: bool


class ProviderOperationResponse(BaseModel):
    provider: Literal["detectifai"] = "detectifai"
    operation: str
    request_id: str | None = None
    operation_id: str | None = None
    raw: dict[str, Any]


class WebhookAcceptedResponse(BaseModel):
    accepted: bool = True
    duplicate: bool = False
    delivery_id: str


class EvidenceItem(BaseModel):
    """Internal, provider-neutral evidence contract shared with Member 3."""
    model_config = ConfigDict(extra="allow")

    call_id: str
    provider: str
    model: str
    check_type: Literal["deepfake", "speaker_verification", "transcription", "context"]
    status: Literal["pending", "completed", "failed", "inconclusive"]
    verdict: str | None = None
    raw_score: float | None = None
    score_type: str | None = None
    is_final: bool = False
    provider_operation_id: str | None = None
    observed_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)
