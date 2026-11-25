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
- Development-only AI analysis and simulated transaction routes; these are disabled in production.
- Basic tests for health and webhook signature validation.

## Important limitations in this first milestone

- This is a development foundation, not a production banking security system.
- Full customer authentication, role-based access control, rate limiting and complete audit history still need implementation before public deployment.
- The browser WebSocket expects binary PCM16LE, mono, 16 kHz audio frames and a JSON `{"type":"stop"}` control message. A frontend recorder must be configured to produce that format.
- The provider's live stream is one stream per call and can run `deepfake,verify` OR `deepfake,enroll`, not both simultaneously.
- Webhook events are signature-checked and persisted. A durable worker and complete cross-channel event reconciliation are later tasks.
- Audio duration and speech-quality requirements are enforced by DetectifAI; test with recordings meeting the current provider documentation and hackathon account limits.
- Do not store real customer recordings during development. The provider's own retention rules still apply to uploaded/enrolled audio.
- Demo intelligence and transaction routes accept caller-supplied evidence/identity and are not safe for real banking use. They are disabled when `APP_ENV=production`.

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

For transcript intelligence, add the provider keys to `.env`:

```env
GEMINI_API_KEY=your_gemini_key_here
SARVAM_API_KEY=your_sarvam_key_here
```

Gemini and Sarvam are optional for local startup. Without their keys, the related
services return failed evidence rather than making provider requests. Model names
and Sarvam audio settings can be overridden with `GEMINI_MODEL`,
`GEMINI_MAX_OUTPUT_TOKENS`, `SARVAM_MODEL`, `SARVAM_BASE_URL`,
`SARVAM_TIMEOUT_SECONDS`, `SARVAM_SAMPLE_RATE`, and `SARVAM_ENCODING`.

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

## Development-only AI and transaction demo routes

These routes are for local integration/testing only and return an explicit demo-only warning. They are disabled when `APP_ENV=production`. The routes accept caller-supplied voice evidence, trust decisions, and customer IDs, so none of those inputs prove identity or authorization.

- `POST /api/v1/intelligence/analyze` — multipart `file`, `call_id`, and optional `voice_evidence_json` (a JSON array containing only DetectifAI deepfake/speaker evidence). Calls Sarvam/Gemini when configured and returns the transcript, evidence, and Trust Engine decision. Evidence passed by the caller is untrusted; only use synthetic or test data.
- `POST /api/v1/transactions/challenges` — creates a short-lived, one-use approval challenge for a policy-approved sensitive action on an existing call session. The response includes the demo token; this is not delivery through an independent trusted banking channel.
- `POST /api/v1/transactions/simulate` — validates policy and any challenge, then records a simulated action. It never executes a real financial operation.

Configure `BACKEND_ACCESS_TOKEN` before exposing these endpoints through a development tunnel. Do not send real customer identity, audio, or transaction data.

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
