import uuid
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class DetectifNotConfiguredError(RuntimeError):
    pass


class DetectifAPIError(RuntimeError):
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"DetectifAI returned HTTP {status_code}")


class DetectifClient:
    """Async adapter for documented DetectifAI REST endpoints.

    Live streaming is implemented separately in detectif_stream.py.
    Audio bytes are sent to DetectifAI and are not written to local disk.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        if not self.settings.detectif_api_key:
            raise DetectifNotConfiguredError("DETECTIF_API_KEY is not configured")
        headers = {"Authorization": f"Bearer {self.settings.detectif_api_key}"}
        headers["Idempotency-Key"] = idempotency_key or str(uuid.uuid4())
        return headers

    async def _post_audio(
        self,
        *,
        path: str,
        filename: str,
        content: bytes,
        content_type: str,
        data: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = self._headers(idempotency_key)
        url = f"{self.settings.detectif_base_url.rstrip('/')}{path}"
        timeout = httpx.Timeout(self.settings.detectif_timeout_seconds, connect=20.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data or {},
                    files={"file": (filename, content, content_type)},
                )
        except httpx.TimeoutException as exc:
            raise DetectifAPIError(504, {"code": "provider_timeout", "message": "DetectifAI request timed out"}) from exc
        except httpx.HTTPError as exc:
            raise DetectifAPIError(502, {"code": "provider_connection_error", "message": "Could not connect to DetectifAI"}) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text[:1000]}

        if not response.is_success:
            raise DetectifAPIError(response.status_code, payload)
        return payload

    async def detect_deepfake(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self._post_audio(
            path="/v1/deepfake/detect",
            filename=filename,
            content=content,
            content_type=content_type,
            idempotency_key=idempotency_key,
        )

    async def enroll_speaker(
        self,
        *,
        speaker_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        display_name: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        data = {"speaker_id": speaker_id}
        if display_name:
            data["display_name"] = display_name
        return await self._post_audio(
            path="/v1/speakers/enroll",
            filename=filename,
            content=content,
            content_type=content_type,
            data=data,
            idempotency_key=idempotency_key,
        )

    async def verify_speaker(
        self,
        *,
        speaker_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        detect_deepfake: bool = True,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "speaker_id": speaker_id,
            "detect_deepfake": "true" if detect_deepfake else "false",
        }
        return await self._post_audio(
            path="/v1/speakers/verify",
            filename=filename,
            content=content,
            content_type=content_type,
            data=data,
            idempotency_key=idempotency_key,
        )
    async def _request_json(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        if not self.settings.detectif_api_key:
            raise DetectifNotConfiguredError("DETECTIF_API_KEY is not configured")
        url = f"{self.settings.detectif_base_url.rstrip('/')}{path}"
        timeout = httpx.Timeout(60.0, connect=20.0)
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.settings.detectif_api_key}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise DetectifAPIError(504, {"code": "provider_timeout", "message": "DetectifAI request timed out"}) from exc
        except httpx.HTTPError as exc:
            raise DetectifAPIError(502, {"code": "provider_connection_error", "message": "Could not connect to DetectifAI"}) from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text[:1000]}
        if not response.is_success:
            raise DetectifAPIError(response.status_code, payload)
        return payload

    async def get_operation(self, operation_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/v1/operations/{operation_id}")

    async def list_speakers(self, limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return await self._request_json("GET", "/v1/speakers", params=params)

    async def delete_speaker(self, speaker_id: str) -> dict[str, Any]:
        return await self._request_json("DELETE", f"/v1/speakers/{speaker_id}")

    async def get_stream(self, stream_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/v1/streams/{stream_id}")

