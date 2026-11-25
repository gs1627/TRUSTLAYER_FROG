from pathlib import Path

import httpx
import pytest
from sqlalchemy import inspect, select, text

from app.core.config import get_settings
from app.db import session as db_session
from app.db.models import CallSession
from app.main import app


@pytest.mark.asyncio
async def test_sqlite_init_and_close_creates_tables_and_disposes(
    isolated_sqlite_url: str,
    tmp_path: Path,
):
    db_session.set_database_url(isolated_sqlite_url)
    await db_session.init_db()
    try:
        async with db_session.engine.connect() as conn:
            table_names = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
        assert {"webhook_events", "call_sessions"}.issubset(table_names)

        async with db_session.AsyncSessionLocal() as session:
            session.add(CallSession(call_id="CALL_TEST_001", speaker_id="SPK_TEST_001"))
            await session.commit()

        async with db_session.AsyncSessionLocal() as session:
            stored = await session.scalar(
                select(CallSession).where(CallSession.call_id == "CALL_TEST_001")
            )
            assert stored is not None
            assert stored.speaker_id == "SPK_TEST_001"
            assert stored.status == "created"
    finally:
        await db_session.close_db()
        assert db_session.engine.pool.checkedout() == 0
        db_session.set_database_url("sqlite+aiosqlite:///:memory:")

    assert (tmp_path / "test_trustlayer.db").exists()


@pytest.mark.asyncio
async def test_get_db_yields_working_async_session(async_db):
    async for session in db_session.get_db():
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
        break


@pytest.mark.asyncio
async def test_app_lifespan_initializes_and_closes_database(
    isolated_sqlite_url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setenv("DATABASE_URL", isolated_sqlite_url)
    get_settings.cache_clear()
    db_session.set_database_url(isolated_sqlite_url)

    try:
        async with app.router.lifespan_context(app):
            async with db_session.AsyncSessionLocal() as session:
                val = (await session.execute(text("SELECT 1"))).scalar_one()
                assert val == 1
        assert db_session.engine.pool.checkedout() == 0
        assert (tmp_path / "test_trustlayer.db").exists()
    finally:
        await db_session.close_db()
        db_session.set_database_url("sqlite+aiosqlite:///:memory:")


@pytest.mark.asyncio
async def test_async_client_health_uses_isolated_database(async_client: httpx.AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert payload["detectif_configured"] is False


def test_set_database_url_normalizes_postgresql_for_asyncpg():
    try:
        engine = db_session.set_database_url("postgresql://trustlayer:secret@localhost:5432/trustlayer")
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "asyncpg"
    finally:
        db_session.set_database_url("sqlite+aiosqlite:///:memory:")
