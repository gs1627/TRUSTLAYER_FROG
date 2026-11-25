# TRUSTLAYER Member Handoff Contracts

These contracts are the initial shared interface between Member 1 (backend), Member 2 (frontend), and Member 3 (AI/Trust Engine). Coordinate before changing field names.

## Backend HTTP routes

Base prefix: `/api/v1`

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Backend and database status |
| POST | `/detectif/deepfake` | Upload audio for Aletheia detection |
| POST | `/detectif/speakers/enroll` | Eidos enrollment; requires `consent_confirmed=true` |
| POST | `/detectif/speakers/verify` | Eidos verification; can also request deepfake detection |
| GET | `/detectif/operations/{operation_id}` | Retrieve provider operation result |
| GET | `/detectif/speakers` | List enrolled speakers |
| DELETE | `/detectif/speakers/{speaker_id}` | Delete provider speaker profile |
| GET | `/detectif/streams/{stream_id}` | Retrieve provider stream record |
| POST | `/calls/sessions` | Create local call session |
| POST | `/webhooks/detectifai` | Receive signed DetectifAI event |
| WS | `/calls/ws/{call_id}` | Browser PCM audio relay to DetectifAI |

OpenAPI docs: `/docs`.

## REST audio contracts

### Aletheia
`multipart/form-data`: `file`
Optional header: `Idempotency-Key`

### Eidos enrollment
`multipart/form-data`: `speaker_id`, `file`, `consent_confirmed=true`, optional `display_name`.

Provider requirements: 15–60 seconds total audio and at least 10 seconds of speech. Up to five enrolled samples per speaker.

### Eidos verification
`multipart/form-data`: `speaker_id`, `file`, optional `detect_deepfake=true`.

Provider requirements: 3–60 seconds total audio and at least 2 seconds of speech.

## Browser WebSocket contract

1. Create a session using `POST /api/v1/calls/sessions` with `{ "call_id": "CALL_001", "speaker_id": "CUSTOMER_001" }`.
2. If `BACKEND_ACCESS_TOKEN` is set, send a first text frame `{ "type": "auth", "token": "YOUR_TOKEN" }`.
3. Connect to `ws://localhost:8000/api/v1/calls/ws/CALL_001`. (Browser WebSocket clients connect first, then send the auth frame.)
4. Send binary frames containing raw mono PCM16LE audio at 16 kHz. Each frame must be at most 64 KB.
5. Send a text frame `{ "type": "stop" }` to end the stream.
6. Backend forwards DetectifAI messages to the browser as JSON with `source: "detectifai"`.

Expected provider message types include `ready`, `deepfake`, `verification`, `completed`, and `error`. The final `completed` message contains final check results. The early verdict and live updates are provisional.

## Member 3 evidence contract

Use the provider-neutral `EvidenceItem` in `app/schemas/contracts.py`. Core fields:

- `call_id`: local call identifier.
- `provider`: provider name, e.g. `detectifai`, `sarvam`, `gemini`, `aasist`.
- `model`: model identifier.
- `check_type`: `deepfake`, `speaker_verification`, `transcription`, or `context`.
- `status`: `pending`, `completed`, `failed`, or `inconclusive`.
- `verdict`: provider decision such as `real`, `fake`, `match`, `no_match`; do not reinterpret a score as a probability.
- `raw_score`: provider-returned score where available.
- `score_type`: semantic label for the score.
- `is_final`: whether this is a final result rather than an early/live update.
- `provider_operation_id`: provider trace identifier where available.
- `details`: provider-specific metadata after removing secrets and unnecessary personal data.

Member 3 owns the Trust Engine. Member 1 owns provider transport and session infrastructure.

## Member 2 frontend contract

- Use REST endpoints for enrollment, file checks, speaker management and session creation.
- Use the browser WebSocket for live call audio and live DetectifAI messages.
- Never call DetectifAI directly from browser code; the API key is backend-only.
- Treat `early: true` and non-final stream updates as provisional. Display final results separately.
- Display `inconclusive`, `failed` and `unavailable` distinctly from `real` or `match`.

## Important boundaries

- The optional `BACKEND_ACCESS_TOKEN` is only a shared development gate, not customer login/RBAC. Do not deploy publicly until proper authentication, authorization, rate limiting and secure deployment configuration are added.
- The browser WebSocket is a development integration path. Production needs authenticated sessions and allowed-origin validation.
- No real bank transaction execution is implemented. The transaction interface must use simulated data until authorised integration exists.
