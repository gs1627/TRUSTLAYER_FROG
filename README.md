# TRUSTLAYER — Member 1 Backend

FastAPI backend infrastructure, DetectifAI resilience & webhook reconciliation, authentication/RBAC, transaction policy gate, real-time event streaming, and persistence for TRUSTLAYER Track 03.

## Quick Links

1. [backend/README.md](backend/README.md) — setup, environment variables, PostgreSQL & Alembic migrations, DetectifAI webhooks, auth/RBAC, transaction policy, and curl examples.
2. [docs/MEMBER_HANDOFF_CONTRACTS.md](docs/MEMBER_HANDOFF_CONTRACTS.md) — complete Member 1 / Member 2 / Member 3 HTTP, WebSocket, evidence, assessment, and simulation contracts.
3. [docs/MEMBER1_FIRST_MILESTONE.md](docs/MEMBER1_FIRST_MILESTONE.md) — initial onboarding and verification checklist.

## Security Reminder

- Never commit `.env`, `*.db` / `trustlayer.db`, virtual environments, or real API keys / webhook secrets / JWT secrets.
- Always configure strong values for `BACKEND_ACCESS_TOKEN` and `JWT_SECRET_KEY` when `APP_ENV=production` (production startup and endpoints fail closed without authentication configured).
