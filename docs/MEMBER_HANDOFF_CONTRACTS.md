# TRUSTLAYER Member Handoff Contracts

These contracts are the shared interface between Member 1 (backend infrastructure & provider integration), Member 2 (frontend dashboard), and Member 3 (AI pipeline & Trust Engine). Coordinate before changing field names.

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
| GET | `/calls/sessions` | List call sessions (paginated, filterable by `status` and `speaker_id`) |
| GET | `/calls/sessions/{call_id}` | Retrieve call session details, evidence summary counts, and latest trust assessment |
| POST | `/calls/sessions/{call_id}/end` | Idempotently terminate a call session with optional `reason` |
| GET | `/calls/sessions/{call_id}/evidence` | List append-only evidence for a call (paginated, filterable) |
| POST | `/calls/sessions/{call_id}/evidence` | Append normalized evidence (with `source_event_key` deduplication) |
| POST | `/calls/sessions/{call_id}/trust-assessments` | Persist an immutable Trust Engine evaluation snapshot |
| GET | `/calls/sessions/{call_id}/trust-assessments/latest` | Retrieve the most recent Trust Assessment for a call |
| GET | `/calls/sessions/{call_id}/trust-assessments` | List paginated immutable Trust Assessment history for a call |
| POST | `/webhooks/detectifai` | Receive signed DetectifAI event and normalize call evidence |
| WS | `/calls/ws/{call_id}` | Browser PCM audio relay to DetectifAI and live evidence normalization |

OpenAPI docs: `/docs`.

## Authentication requirements

- **Protected REST routes** (all `/detectif/*` and `/calls/sessions*` endpoints):
  - When `BACKEND_ACCESS_TOKEN` is configured, requests must send `Authorization: Bearer <BACKEND_ACCESS_TOKEN>`. Invalid or missing headers return `401`.
  - When `APP_ENV=production` and `BACKEND_ACCESS_TOKEN` is unset, protected routes fail closed with `503`.
  - In `development`/`test` without `BACKEND_ACCESS_TOKEN`, protected routes remain accessible locally.
- **Health endpoint** (`GET /api/v1/health`): unauthenticated.
- **Webhooks** (`POST /api/v1/webhooks/detectifai`): verified via Standard Webhooks HMAC-SHA256 (`webhook-id`, `webhook-timestamp`, `webhook-signature`) against `DETECTIF_WEBHOOK_SECRET` (`503` if secret unset, `400` on invalid/stale signatures).
- **Live Browser WebSocket** (`WS /api/v1/calls/ws/{call_id}`): expects initial JSON frame `{"type": "auth", "token": "<BACKEND_ACCESS_TOKEN>"}` when configured (`4401` close code on failure).

## Pagination & ordering conventions

All paginated `GET` collection endpoints accept query parameters:
- `limit` (integer, default `50`, min `1`, max `200`)
- `offset` (integer, default `0`, min `0`)

Responses use the standard envelope:
```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Deterministic sort orders:
- `GET /calls/sessions`: `(created_at DESC, call_id ASC)`
- `GET /calls/sessions/{call_id}/evidence`: `(created_at ASC, evidence_id ASC)`
- `GET /calls/sessions/{call_id}/trust-assessments`: `(created_at DESC, assessment_id DESC)`
- `TrustAssessment.evidence_ids`: `(EvidenceItem.created_at ASC, EvidenceItem.evidence_id ASC)` regardless of input list order.

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

## Call session & browser WebSocket contract

1. Create a session using `POST /api/v1/calls/sessions`:
   - Default (backward-compatible) payload: `{ "call_id": "CALL_001", "speaker_id": "CUSTOMER_001" }` (defaults `checks_mode` to `"deepfake,verify"`). Returns `200`:
     ```json
     {
       "call_id": "CALL_001",
       "speaker_id": "CUSTOMER_001",
       "checks_mode": "deepfake,verify",
       "status": "created"
     }
     ```
   - Deepfake-only call (`speaker_id` optional/nullable): `{ "call_id": "CALL_002", "checks_mode": "deepfake" }`.
   - Enrollment call (`speaker_id` and `consent_confirmed=true` required): `{ "call_id": "CALL_003", "speaker_id": "CUSTOMER_001", "checks_mode": "deepfake,enroll", "consent_confirmed": true }`.
2. Retrieve session detail using `GET /api/v1/calls/sessions/{call_id}`:
   ```json
   {
     "call_id": "CALL_001",
     "speaker_id": "CUSTOMER_001",
     "checks_mode": "deepfake,verify",
     "consent_confirmed": false,
     "consent_recorded_at": null,
     "provider_stream_id": "str_123",
     "status": "active",
     "last_deepfake_sequence": 2,
     "last_provider_event_at": "2026-11-25T10:00:05Z",
     "ended_at": null,
     "ended_reason": null,
     "created_at": "2026-11-25T10:00:00Z",
     "updated_at": "2026-11-25T10:00:05Z",
     "evidence_summary": {
       "total": 2,
       "final_count": 0,
       "provisional_count": 2,
       "by_check_type": { "deepfake": 2 },
       "by_status": { "pending": 2 },
       "by_provider": { "detectifai": 2 }
     },
     "latest_trust_assessment": null
   }
   ```
3. Terminate a session idempotently using `POST /api/v1/calls/sessions/{call_id}/end`:
   - Optional body: `{ "reason": "caller_hangup" }` (or omit body).
   - First call sets `status="ended"`, `ended_at`, and `ended_reason`, returning `200` `CallSessionRead`.
   - Repeated calls preserve the initial `ended_at` and `ended_reason` unchanged and return `200` `CallSessionRead`.
4. Live WebSocket `WS /api/v1/calls/ws/{call_id}`:
   - If `BACKEND_ACCESS_TOKEN` is set, send `{ "type": "auth", "token": "YOUR_TOKEN" }` as the first JSON frame.
   - Send binary PCM16LE 16 kHz mono frames (max 64 KB each) and `{ "type": "stop" }` when ending.
   - Provider messages are forwarded with `source: "detectifai"` and normalized/persisted asynchronously when matching a session.

## Member 3 evidence contracts

### Evidence semantics: `is_early` vs `is_final` and append-only guarantees

- `is_early` and `is_final` represent **independent** provider flags and are never derived from one another (e.g., a live update with `early: false` may still have `final: false`).
- `stream.deepfake.updated` webhook events are **always provisional** (`is_final=false`).
- Only explicit provider-final outcomes (`completed` stream messages, `deepfake.completed`, `stream.completed`, completed verification webhooks, or synchronous completed REST results) produce `is_final=true`.
- Evidence storage is **strictly append-only**: a provisional/early result never overwrites an existing final record.
- Provider raw scores (`synthetic_score`, `cosine_similarity`, etc.) are preserved verbatim in `raw_score` + `score_type` and never re-interpreted as calibrated probabilities.

### Evidence deduplication behavior

- Deduplication key: `(call_id, provider, check_type, source_event_key)` enforced in both repository logic and DB unique constraint (`uq_evidence_items_source_event`).
- Sending a repeated `POST /api/v1/calls/sessions/{call_id}/evidence` with the same `source_event_key` returns HTTP `200` with the previously stored `EvidenceItemRead` instead of creating a duplicate row or emitting a duplicate `evidence.added` domain event.
- Newly created evidence returns HTTP `201` with backend-generated `evidence_id` (`ev_...`) and `created_at`.
- Concurrent duplicate requests are handled safely via DB constraint + rollback/lookup without failing or duplicating rows.
- `details` are recursively sanitized to strip credentials, bearer tokens, raw audio payloads, and unnecessary PII.

### Evidence submission examples (`POST /api/v1/calls/sessions/{call_id}/evidence`)

**Sarvam transcription (Member 3 -> Backend):**
```json
{
  "call_id": "CALL_001",
  "speaker_id": "CUSTOMER_001",
  "provider": "sarvam",
  "model": "saaras:v4",
  "check_type": "transcription",
  "status": "completed",
  "raw_score": 0.96,
  "score_type": "language_probability",
  "is_final": true,
  "source_channel": "internal",
  "source_event_key": "sarvam:CALL_001:turn_1",
  "sequence": 1,
  "provider_request_id": "req_sarvam_123",
  "observed_at": "2026-11-25T10:00:08Z",
  "details": {
    "transcript": "Please reset my netbanking password urgently.",
    "language": "en-IN",
    "language_probability": 0.96,
    "timestamps": {
      "words": ["Please", "reset"],
      "start_time_seconds": [0.1, 0.5],
      "end_time_seconds": [0.4, 0.9]
    }
  }
}
```

**Gemini contextual analysis (Member 3 -> Backend):**
```json
{
  "call_id": "CALL_001",
  "speaker_id": "CUSTOMER_001",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "check_type": "context",
  "status": "completed",
  "verdict": "high_urgency_credential_reset",
  "raw_score": 0.82,
  "score_type": "contextual_risk_score",
  "is_final": true,
  "source_channel": "internal",
  "source_event_key": "gemini:CALL_001:ctx_1",
  "observed_at": "2026-11-25T10:00:09Z",
  "details": {
    "risk_label": "high_urgency_credential_reset",
    "cues": ["urgency_pressure", "credential_reset_request"],
    "reasoning_summary": "Caller demands immediate credential reset under time pressure.",
    "model_metadata": { "prompt_version": "ctx-v1" }
  }
}
```
*(Inconclusive/failed Sarvam or Gemini evaluations preserve `status="inconclusive"` or `"failed"` and omit missing optional fields rather than inventing values.)*

Filterable query parameters on `GET /api/v1/calls/sessions/{call_id}/evidence`:
- `check_type`: `deepfake | speaker_verification | transcription | context`
- `provider`: e.g. `detectifai`, `sarvam`, `gemini`
- `is_final`: `true | false`
- `limit`, `offset`

## Trust assessment submission and retrieval

Member 3 computes trust scores and risk classifications and submits snapshots via:
`POST /api/v1/calls/sessions/{call_id}/trust-assessments` (returns `201 Created`):

```json
{
  "trust_score": 0.28,
  "risk_level": "high",
  "recommended_action": "step_up_verify",
  "summary": "Deepfake anomaly and high-urgency social engineering cues.",
  "reasons": ["aletheia:synthetic_score_elevated", "gemini:urgency_pressure"],
  "evidence_ids": ["ev_01...", "ev_02..."],
  "is_final": true,
  "model_version": "trust-v1"
}
```

Validation & immutability rules:
- Backend generates `assessment_id` (`ta_...`) and `created_at` (client-supplied `assessment_id` or `created_at` is rejected with `422`).
- `trust_score` must be finite (`NaN`/`Infinity` rejected) and in `[0.0, 1.0]` (`trust_score` is a bounded model score, not automatically a calibrated probability).
- Duplicate `evidence_ids` fail `422`; unknown `evidence_ids` fail `422` (`evidence_not_found`); evidence belonging to another `call_id` fails `422` (`cross_call_evidence_not_allowed`).
- Assessments are **immutable and append-only**: repeated submissions append new historical versions returned newest-first from `GET /trust-assessments` and at `GET /trust-assessments/latest`.

## Internal event-publishing interface (Priority 4/5 foundation)

`app/services/events.py` defines an in-memory `EventPublisher` (`InMemoryEventBus`) decoupled from DB repositories and REST routes. Successful state transitions publish `DomainEvent` envelopes after DB commit:
- `call.status_changed`
- `evidence.added` (only when newly created, not on deduplicated repeats)
- `trust.updated`

## Standardized errors & HTTP status behavior

Priority 3 and domain errors return the `ErrorResponse` envelope (keeping Top-level `detail` for FastAPI compatibility):
```json
{
  "detail": "Evidence 'ev_missing' not found",
  "error": {
    "code": "evidence_not_found",
    "message": "Evidence 'ev_missing' not found",
    "provider": null,
    "request_id": null,
    "retryable": false,
    "details": { "missing_evidence_ids": ["ev_missing"] }
  }
}
```

| HTTP Status | Error `code` examples | Trigger |
|---|---|---|
| `401` | *(FastAPI detail)* | Missing/invalid `Authorization: Bearer ...` when `BACKEND_ACCESS_TOKEN` is set |
| `404` | `call_session_not_found`, `trust_assessment_not_found`, `evidence_not_found` | Target call session or latest trust assessment does not exist |
| `409` | `call_session_already_exists` | Duplicate `call_id` in `POST /calls/sessions` |
| `422` | `cross_call_mismatch`, `evidence_not_found`, `cross_call_evidence_not_allowed`, Pydantic validation errors | Payload validation failure, non-finite scores, missing or cross-call `evidence_ids` |
| `503` | *(FastAPI detail)* | Production mode missing `BACKEND_ACCESS_TOKEN` or missing DetectifAI config |

*(Planned endpoints deferred beyond Priority 3: `POST /calls/sessions/{call_id}/transactions/simulate` and `WS /calls/ws/{call_id}/events`.)*

## Database migrations

Schema management uses **Alembic** (`backend/alembic.ini`, `backend/alembic/`). Run `alembic upgrade head` from `backend/` (or rely on single-process development/test startup via `init_db()`). In production (`APP_ENV=production`) or multi-worker deployments, run `alembic upgrade head` once before starting application workers.

## Member 2 frontend contract

- Use REST endpoints for enrollment, file checks, speaker management, call listing/details/termination, evidence timelines, and trust assessment retrieval.
- Use `WS /api/v1/calls/ws/{call_id}` for live call audio and live DetectifAI messages.
- Never call DetectifAI directly from browser code; the API key is backend-only.
- Treat `is_early: true` and `is_final: false` evidence/assessments as provisional.
- Display `inconclusive`, `failed`, and `unavailable` distinctly from `real` or `match`.

## Important boundaries

- `BACKEND_ACCESS_TOKEN` is only a shared development gate, not customer login/RBAC.
- Member 3 owns Sarvam/Gemini pipelines and the trust-scoring algorithm; Member 1 owns evidence normalization, persistence, REST/WebSocket transport, and event publishing.
- No real bank transaction execution is implemented.
