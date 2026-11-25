import hmac

from fastapi import Header, HTTPException, WebSocket

from app.core.config import get_settings


async def require_backend_access(authorization: str | None = Header(default=None)) -> None:
    """Optional shared development gate; not a replacement for production user auth/RBAC."""
    settings = get_settings()
    token = settings.backend_access_token
    if not token:
        if settings.app_env == "production":
            raise HTTPException(status_code=503, detail="BACKEND_ACCESS_TOKEN or production auth is not configured")
        return
    supplied = authorization or ""
    if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:], token):
        raise HTTPException(status_code=401, detail="Missing or invalid backend access token")


def require_demo_mode() -> None:
    """Prevent demo-only endpoints from being enabled in production."""
    if get_settings().app_env == "production":
        raise HTTPException(
            status_code=403,
            detail="This demo-only endpoint is disabled in production",
        )


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """Validate the first WebSocket JSON frame when a shared token is configured."""
    settings = get_settings()
    token = settings.backend_access_token
    if not token:
        return settings.app_env != "production"
    try:
        message = await websocket.receive_json()
    except Exception:
        return False
    supplied = message.get("token", "") if isinstance(message, dict) else ""
    return message.get("type") == "auth" and hmac.compare_digest(str(supplied), token)
