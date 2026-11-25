# TRUSTLAYER — Member 1 Backend

FastAPI backend foundation for the TRUSTLAYER Track 03 project.

## Implemented in this starter

- FastAPI application and OpenAPI docs.
- SQLite local development database; PostgreSQL URL supported.
- DetectifAI REST adapters for Aletheia detection, Eidos enrollment and Eidos verification.
- DetectifAI combined live stream relay (`deepfake,verify`) for browser-originated raw PCM16LE 16 kHz mono frames.
- DetectifAI webhook receiver with raw-body HMAC-SHA256 verification and 5-minute timestamp tolerance.
- Webhook delivery deduplication and basic call-session state updates.
- Shared provider-neutral `EvidenceItem` schema for coordination with Member 3.
- Basic tests for health and webhook signature validation.

## Important limitations in this first milestone

- This is a development foundation, not a production banking security system.
- Full customer authentication, role-based access control, rate limiting and complete audit history still need implementation before public deployment.
- The browser WebSocket expects binary PCM16LE, mono, 16 kHz audio frames and a JSON `{"type":"stop"}` control message. A frontend recorder must be configured to produce that format.
- The provider's live stream is one stream per call and can run `deepfake,verify` OR `deepfake,enroll`, not both simultaneously.
- Webhook events are signature-checked and persisted. A durable worker and complete cross-channel event reconciliation are later tasks.
- Audio duration and speech-quality requirements are enforced by DetectifAI; test with recordings meeting the current provider documentation and hackathon account limits.
- Do not store real customer recordings during development. The provider's own retention rules still apply to uploaded/enrolled audio.

## Windows PowerShell setup

From the `backend` directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and add the DetectifAI API key:

```env
DETECTIF_API_KEY=your_key_here
```

To configure webhooks, add the endpoint signing secret supplied by the DetectifAI dashboard:

```env
DETECTIF_WEBHOOK_SECRET=whsec_your_secret_here
```

Before exposing the backend through a development tunnel, set a strong shared development token in `.env`:

```env
BACKEND_ACCESS_TOKEN=generate_a_long_random_value
```

Protected REST routes then require `Authorization: Bearer <token>`. If configured, the browser WebSocket must send a first JSON frame `{"type":"auth","token":"..."}` after connecting. This is only a temporary development gate, not a replacement for customer authentication and role-based access control.

Start the backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/v1/health

## Run tests

```powershell
pytest -q
```

## DetectifAI API routes

- `POST /api/v1/detectif/deepfake`
- `POST /api/v1/detectif/speakers/enroll`
- `POST /api/v1/detectif/speakers/verify`
- `POST /api/v1/webhooks/detectifai`
- `POST /api/v1/calls/sessions`
- `WS /api/v1/calls/ws/{call_id}`

Enrollment requires `consent_confirmed=true` and a 15–60 second recording containing at least 10 seconds of speech. Verification requires a 3–60 second recording containing at least 2 seconds of speech. The DetectifAI API may return provider-specific validation and credit errors.

## Webhook setup

1. Run the backend locally.
2. Expose it through a trusted HTTPS development tunnel (never expose a production secret in a public repository).
3. Register `https://YOUR-TUNNEL/api/v1/webhooks/detectifai` in the DetectifAI dashboard.
4. Copy the signing secret into `DETECTIF_WEBHOOK_SECRET`.
5. Use the dashboard's test event and confirm HTTP 202.

DetectifAI requires a public HTTPS host for webhook registration. Localhost is not accepted.

## Contract ownership

- Person 1 owns backend API and provider adapters.
- Person 2 consumes the documented routes and WebSocket events.
- Person 3 consumes `EvidenceItem` and will own Sarvam, Gemini and the Trust Engine.

Coordinate schema changes before merging shared changes.

## One-command Windows start

From the `backend` directory, run:

```powershell
.\scripts\start.ps1
```

The script creates the virtual environment, installs requirements, creates `.env` if missing, and starts Uvicorn. Edit `.env` and restart the server after adding provider credentials.
