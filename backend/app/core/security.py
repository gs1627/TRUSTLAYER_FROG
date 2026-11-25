import base64
import binascii
import hashlib
import hmac
import time
from collections.abc import Mapping


class WebhookSignatureError(ValueError):
    """Raised when a DetectifAI webhook signature is invalid or stale."""


def verify_detectif_webhook_signature(
    *,
    secret: str,
    headers: Mapping[str, str],
    raw_body: bytes,
    tolerance_seconds: int = 300,
    now: float | None = None,
) -> None:
    """Verify the Standard Webhooks signature used by DetectifAI.

    The HMAC input is: webhook-id + '.' + webhook-timestamp + '.' + raw_body.
    The key is the base64-decoded portion of the whsec_ secret.
    Raises WebhookSignatureError rather than returning a permissive default.
    """
    lowered = {key.lower(): value for key, value in headers.items()}
    message_id = lowered.get("webhook-id")
    timestamp = lowered.get("webhook-timestamp")
    signatures = lowered.get("webhook-signature")

    if not message_id or not timestamp or not signatures:
        raise WebhookSignatureError("Required webhook signature headers are missing")

    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise WebhookSignatureError("Webhook timestamp is invalid") from exc

    current_time = time.time() if now is None else now
    if abs(current_time - timestamp_value) > tolerance_seconds:
        raise WebhookSignatureError("Webhook timestamp is outside the allowed time window")

    encoded_secret = secret.removeprefix("whsec_")
    try:
        key = base64.b64decode(encoded_secret, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise WebhookSignatureError("Webhook signing secret is malformed") from exc

    signed_content = f"{message_id}.{timestamp}.".encode("utf-8") + raw_body
    expected = base64.b64encode(
        hmac.new(key, signed_content, hashlib.sha256).digest()
    ).decode("ascii")

    valid = False
    for part in signatures.split():
        version, separator, supplied = part.partition(",")
        if version == "v1" and separator and supplied:
            valid = hmac.compare_digest(expected, supplied) or valid

    if not valid:
        raise WebhookSignatureError("Webhook signature does not match")
