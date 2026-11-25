# TRUSTLAYER — Member 1 Backend

FastAPI backend for TRUSTLAYER (Track 03), covering:
- **Database & Migrations (Priorities 1–2.1)**: Async SQLAlchemy (`aiosqlite` for local dev/tests, `asyncpg` for PostgreSQL), UTC timestamp handling, and Alembic migrations (`0001`–`0003`) with startup lock serialization.
- **Evidence Normalization Engine (Priority 3)**: Provider mappers (`detectifai` Aletheia/Eidos, `sarvam`, `gemini`), append-only deduplicated `EvidenceItem` persistence, Call Session & Trust Assessment REST APIs.
- **DetectifAI Hardening (Priority 4)**: Connection-pooled `httpx.AsyncClient`, idempotent safe retries with jittered backoff, credit/rate-limit classification, full `ProviderOperation` lifecycle tracking, and live WebSocket support for `deepfake`, `deepfake,verify`, and `deepfake,enroll`.
- **Webhook Security & Reconciliation (Priority 5)**: Standard Webhooks HMAC-SHA256 verification (with 5-minute replay tolerance and secret rotation), out-of-order & duplicate delivery safety, unmatched/failed event reconciliation, and dead-letter queue handling/replay.
- **Security, RBAC, Rate Limits & Transaction Policy (Priority 6)**: HS256 JWT issuance/verification alongside legacy `BACKEND_ACCESS_TOKEN`, per-user call/speaker isolation, role-based access control, WebSocket first-frame JSON authentication + connection limits, sliding-window rate limiting, and the conservative `POST /calls/sessions/{call_id}/transactions/simulate` policy gate.
- **Full Integration & Live Dashboard Events (Priority 7)**: Real-time `WS /api/v1/calls/ws/{call_id}/events` broadcasting `evidence.added`, `trust.updated`, and `call.status_changed`.

---

## Windows PowerShell Local Setup (SQLite)

From `backend/`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Or use the one-command launcher:

```powershell
.\scripts\start.ps1
```

Edit `backend/.env` with placeholder-replaced local credentials, then start FastAPI:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI documentation: `http://127.0.0.1:8000/docs`

---

## PostgreSQL Setup and Alembic Migrations

1. Set a PostgreSQL URL in `backend/.env` (automatically normalized to `postgresql+asyncpg://` at runtime):

```env
DATABASE_URL=postgresql+asyncpg://trustlayer:CHANGE_ME@localhost:5432/trustlayer
```

2. Run Alembic migrations from `backend/`:

```powershell
alembic upgrade head
alembic current
alembic check
```

3. For **production** (`APP_ENV=production`) or multi-worker deployments:
   - Always run `alembic upgrade head` once **before** starting application workers.
   - Startup `init_db()` runs `verify_database_schema()` without implicit DDL in production.
   - Schema migrations use PostgreSQL advisory locks (`pg_advisory_lock`) when migrating under development startup.

---

## Environment Variables Reference

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `TRUSTLAYER Backend` | FastAPI application title |
| `APP_ENV` | `development` | `development`, `test`, or `production` |
| `API_V1_PREFIX` | `/api/v1` | REST/WebSocket URL prefix |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `DATABASE_URL` | `sqlite+aiosqlite:///./trustlayer.db` | SQLite or PostgreSQL database URL |
| `DETECTIF_API_KEY` | `None` | DetectifAI Bearer API key (`your_key_here` in local `.env`) |
| `DETECTIF_BASE_URL` | `https://platform.detectif.ai` | DetectifAI base URL |
| `DETECTIF_CONNECT_TIMEOUT_SECONDS` | `10.0` | Connect/pool timeout for DetectifAI |
| `DETECTIF_TIMEOUT_SECONDS` | `300.0` | Read/write timeout for audio uploads |
| `DETECTIF_MAX_RETRIES` | `2` | Retries on idempotent GET or `Idempotency-Key` requests |
| `DETECTIF_RETRY_BACKOFF_SECONDS` | `0.5` | Base backoff duration for transient provider retries |
| `DETECTIF_WS_MAX_CONNECTIONS_PER_CALL` | `2` | Maximum concurrent audio WebSocket relays per call |
| `DETECTIF_WEBHOOK_SECRET` | `None` | Primary `whsec_...` Standard Webhooks signing secret |
| `DETECTIF_WEBHOOK_SECRET_PREVIOUS` | `None` | Optional previous `whsec_...` secret during key rotation |
| `WEBHOOK_TOLERANCE_SECONDS` | `300` | Maximum clock skew/replay window in seconds |
| `WEBHOOK_MAX_ATTEMPTS` | `5` | Failed attempts before marking a webhook delivery `dead_letter` |
| `WEBHOOK_RETRY_BASE_SECONDS` | `30` | Exponential backoff base for failed webhook retries |
| `BACKEND_ACCESS_TOKEN` | `None` | Legacy shared development/service Bearer token |
| `JWT_SECRET_KEY` | `None` | HMAC-SHA256 signing secret for JWT bearer tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ISSUER` | `trustlayer-backend` | Expected `iss` claim |
| `JWT_AUDIENCE` | `trustlayer-api` | Expected `aud` claim |
| `JWT_ACCESS_TOKEN_TTL_SECONDS` | `3600` | Default token expiration TTL (60–86400s) |
| `RATE_LIMIT_ENABLED` | `true` | Enable in-process sliding-window rate limits |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding rate limit window duration |
| `RATE_LIMIT_AUTH_REQUESTS` | `30` | Max auth token requests per window per client |
| `RATE_LIMIT_CALL_CREATE_REQUESTS` | `30` | Max call session creations per window per client |
| `RATE_LIMIT_EVIDENCE_REQUESTS` | `120` | Max evidence/verification uploads per window |
| `RATE_LIMIT_ASSESSMENT_REQUESTS` | `60` | Max trust assessment posts per window |
| `RATE_LIMIT_WEBHOOK_REQUESTS` | `300` | High ceiling for webhook ingestion & retries |
| `RATE_LIMIT_WS_CONNECT_REQUESTS` | `20` | Max WebSocket handshake attempts per window |
| `RATE_LIMIT_WS_MESSAGES_PER_WINDOW` | `2400` | Max WebSocket audio/control frames per window |
| `TX_POLICY_MIN_ALLOW_TRUST_SCORE` | `0.75` | Minimum Trust Engine score to consider allowing |
| `TX_POLICY_BLOCK_TRUST_SCORE` | `0.35` | Trust Engine score below which requests block |
| `TX_POLICY_HIGH_VALUE_AMOUNT` | `50000.00` | Amount triggering stricter step-up/block rules |
| `TX_POLICY_REQUIRE_FINAL_DEEPFAKE` | `true` | Require finalized Aletheia evidence before allowing |
| `TX_POLICY_REQUIRE_FINAL_VERIFICATION_WHEN_CONFIGURED` | `true` | Require finalized Eidos match in `deepfake,verify` calls |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser CORS origins |
| `MAX_UPLOAD_MB` | `25` | Upload byte cap enforced before DetectifAI forwarding |

---

## DetectifAI Webhook Configuration & Reconciliation

- **Webhook receiver endpoint**: `/api/v1/webhooks/detectifai`
- **Local HTTPS tunnel setup**: DetectifAI requires a public HTTPS host (no `localhost` or raw IP). During local testing, expose `http://127.0.0.1:8000` with a temporary HTTPS tunnel (such as `cloudflared` or `ngrok`), then register `https://<your-tunnel-host>/api/v1/webhooks/detectifai` in the DetectifAI Dashboard under **Webhooks**.
- **Signing secret**: Copy the dashboard's `whsec_...` secret into `DETECTIF_WEBHOOK_SECRET` in `backend/.env` and restart the server. When rotating secrets, set the expiring secret in `DETECTIF_WEBHOOK_SECRET_PREVIOUS`.
- **Supported events**: `webhook.test`, `deepfake.completed`, `speaker.enrolled`, `speaker.verified`, `stream.started`, `stream.deepfake.updated`, and `stream.completed` (plus aliases such as `speaker.verification.completed`).
- **Expected HTTP response**: Valid signed events return HTTP `202 Accepted` (`{"accepted": true, "duplicate": false, "delivery_id": "msg_...", "status": "processed"|"unmatched"|"failed"}`). Re-deliveries with the same `webhook-id` return `duplicate: true` cleanly without creating duplicate evidence.
- **Inspecting & recovering failed / unmatched deliveries (Admin)**:
  - `GET /api/v1/webhooks/events?status=unmatched` or `?status=dead_letter`
  - `POST /api/v1/webhooks/reconcile` — replays unmatched and retryable failed deliveries.
  - `POST /api/v1/webhooks/events/{delivery_id}/reprocess` — force-replays a specific delivery (including `dead_letter`).

---

## Authentication, RBAC & Rate Limiting

- **Production fail-closed**: When `APP_ENV=production`, at least one of `JWT_SECRET_KEY` or `BACKEND_ACCESS_TOKEN` must be set; otherwise protected routes return `503`.
- **Migration path from `BACKEND_ACCESS_TOKEN` to JWT**:
  1. Keep `BACKEND_ACCESS_TOKEN` configured as the service bootstrap secret during migration and add a strong `JWT_SECRET_KEY`.
  2. Issue role-scoped JWTs via `POST /api/v1/auth/token` (`role`: `user`, `operator`, `service`, `admin`) using `Authorization: Bearer <BACKEND_ACCESS_TOKEN>`.
  3. Update frontend clients to authenticate callers with `role="user"` or `role="operator"` JWTs and update Member 3 pipeline services to use `role="service"` JWTs.
- **Permissions separation**:
  - `user`: Creates and views only calls/speakers matching their `sub` (`owner_id`). Accessing another user's `call_id` returns `403`. Cannot submit Member 3 evidence/assessments or inspect webhook admin routes (`403`).
  - `operator`: Views calls/evidence/assessments, ends sessions, runs DetectifAI checks and transaction simulations (`403` on Member 3 ingestion and webhook admin routes).
  - `service`: Member 3 AI pipeline role — submits `POST /evidence` and `POST /trust-assessments`, reads/simulates calls, polls operations (`403` on admin webhook routes).
  - `admin`: Full access including `GET /webhooks/events`, `POST /webhooks/reconcile`, and replay.
- **Rate limiter caveat**: The built-in `SlidingWindowRateLimiter` and `WebSocketConnectionTracker` are single-process in-memory stores. Multi-worker deployments must add a shared Redis-backed store.

---

## Transaction Policy Behaviour (`POST /api/v1/calls/sessions/{call_id}/transactions/simulate`)

- Strictly **simulated** (`simulated: true` persisted in `simulated_transactions`; never executes real money movement).
- Evaluates decision precedence **`block > hold > step_up_verify > allow`** without treating DetectifAI raw scores or Trust Engine scores as calibrated probabilities:
  - **`block`**: Final deepfake `fake`, final verification `no_match` (in `deepfake,verify` calls), TrustAssessment `block`/`critical`, `trust_score < TX_POLICY_BLOCK_TRUST_SCORE`, ended call session, or high-value action with high risk / context risk cues.
  - **`hold`**: Missing `TrustAssessment`, incomplete final deepfake or verification check, `failed`/`inconclusive` critical check, or failed `ProviderOperation` without recovery.
  - **`step_up_verify`**: Provisional evidence/assessment (`is_final=false`), medium/high risk, `trust_score < TX_POLICY_MIN_ALLOW_TRUST_SCORE`, or high-value transfer missing final Gemini context analysis.
  - **`allow`**: Only when finalized checks pass (`real`, `match`), no risk/failure flags exist, and latest `TrustAssessment` approves (`allow`, `low`, above threshold).

---

## Example `curl` Workflows (Use Placeholders Only)

```bash
# 1. Mint a user JWT and a Member 3 service JWT (development/bootstrap token shown as placeholder)
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H "Authorization: Bearer YOUR_SERVICE_BOOTSTRAP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subject":"cust_001","role":"user","expires_in_seconds":3600}'

# 2. Create a call session as that user
curl -s -X POST http://127.0.0.1:8000/api/v1/calls/sessions \
  -H "Authorization: Bearer YOUR_USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"call_id":"CALL_DEMO_01","speaker_id":"SPK_001","checks_mode":"deepfake,verify"}'

# 3. Member 3 submits normalized Sarvam transcription evidence
curl -s -X POST http://127.0.0.1:8000/api/v1/calls/sessions/CALL_DEMO_01/evidence \
  -H "Authorization: Bearer YOUR_SERVICE_JWT" \
  -H "Content-Type: application/json" \
  -d '{"call_id":"CALL_DEMO_01","provider":"sarvam","model":"saaras:v4","check_type":"transcription","status":"completed","is_final":true,"source_channel":"internal","source_event_key":"srv:CALL_DEMO_01:1","details":{"transcript":"Please transfer money now"}}'

# 4. Simulate transaction policy decision
curl -s -X POST http://127.0.0.1:8000/api/v1/calls/sessions/CALL_DEMO_01/transactions/simulate \
  -H "Authorization: Bearer YOUR_USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action_type":"fund_transfer","amount":"2500.00","currency":"INR","recipient_ref":"DEMO_ACC"}'
```

---

## Running Tests

From `backend/`:

```powershell
# SQLite & unit/integration suite
pytest -v -W error::sqlalchemy.exc.SAWarning

# Live PostgreSQL verification (against an isolated dedicated test PostgreSQL database)
$env:TEST_POSTGRES_URL = "postgresql+asyncpg://postgres:CHANGE_ME@127.0.0.1:5432/postgres"
pytest -v tests/test_postgresql_integration.py -W error::sqlalchemy.exc.SAWarning
```
