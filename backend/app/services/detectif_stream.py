import asyncio
import json
from collections.abc import Awaitable, Callable
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import get_settings


class DetectifStreamError(RuntimeError):
    pass


async def relay_browser_audio_to_detectif(
    *,
    browser_ws,
    call_id: str,
    speaker_id: str,
    on_provider_message: Callable[[dict], Awaitable[None]] | None = None,
) -> None:
    """Relay raw 16 kHz mono PCM16 browser frames to a DetectifAI live stream.

    The browser must send binary PCM16LE frames and a JSON text message
    {"type":"stop"} when recording ends. One DetectifAI stream is opened per call.
    This first implementation is for the app's own browser client; telephony
    providers may need their documented media-message/relay adapters.
    """
    settings = get_settings()
    if not settings.detectif_api_key:
        raise DetectifStreamError("DETECTIF_API_KEY is not configured")
    if not speaker_id:
        raise DetectifStreamError("speaker_id is required for Track 03 verification")

    query = urlencode(
        {
            "checks": "deepfake,verify",
            "speaker_id": speaker_id,
            "encoding": "pcm_s16le",
            "sample_rate": "16000",
            "reference": call_id,
        }
    )
    url = f"wss://platform.detectif.ai/v1/stream?{query}"
    headers = {"Authorization": f"Bearer {settings.detectif_api_key}"}

    try:
        async with websockets.connect(
            url,
            additional_headers=headers,
            max_size=2 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
        ) as provider_ws:
            async def provider_to_browser() -> None:
                async for raw_message in provider_ws:
                    if isinstance(raw_message, bytes):
                        continue
                    try:
                        payload = json.loads(raw_message)
                    except json.JSONDecodeError:
                        payload = {"type": "provider_message", "raw": raw_message}
                    if on_provider_message:
                        await on_provider_message(payload)
                    await browser_ws.send_json({"source": "detectifai", **payload})
                    if payload.get("type") == "completed":
                        return

            async def browser_to_provider() -> str:
                while True:
                    message = await browser_ws.receive()
                    if message.get("type") == "websocket.disconnect":
                        return "disconnect"
                    if message.get("bytes") is not None:
                        chunk = message["bytes"]
                        if len(chunk) > 64 * 1024:
                            await browser_ws.send_json({"type": "error", "code": "audio_frame_too_large"})
                            continue
                        await provider_ws.send(chunk)
                    elif message.get("text"):
                        try:
                            control = json.loads(message["text"])
                        except json.JSONDecodeError:
                            control = {}
                        if control.get("type") == "stop":
                            await provider_ws.send(json.dumps({"type": "stop"}))
                            return "stop"

            receive_task = asyncio.create_task(provider_to_browser())
            send_task = asyncio.create_task(browser_to_provider())
            done, _ = await asyncio.wait(
                {receive_task, send_task}, return_when=asyncio.FIRST_COMPLETED
            )

            if receive_task in done:
                await receive_task
                if not send_task.done():
                    send_task.cancel()
                    await asyncio.gather(send_task, return_exceptions=True)
            else:
                reason = await send_task
                if reason == "stop":
                    # Do not cancel the result reader immediately: DetectifAI sends
                    # its final `completed` message after receiving the stop signal.
                    try:
                        await asyncio.wait_for(receive_task, timeout=45)
                    except asyncio.TimeoutError:
                        receive_task.cancel()
                        await asyncio.gather(receive_task, return_exceptions=True)
                else:
                    receive_task.cancel()
                    await asyncio.gather(receive_task, return_exceptions=True)
    except ConnectionClosed:
        return
    except Exception as exc:
        raise DetectifStreamError(str(exc)) from exc
