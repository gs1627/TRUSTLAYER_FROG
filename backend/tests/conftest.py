from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.db import session as db_session
from app.main import app
from app.services.events import reset_event_publisher

_ISOLATED_ENV_VARS = (
    "APP_NAME",
    "APP_ENV",
    "API_V1_PREFIX",
    "LOG_LEVEL",
    "DATABASE_URL",
    "DETECTIF_API_KEY",
    "DETECTIF_BASE_URL",
    "DETECTIF_TIMEOUT_SECONDS",
    "DETECTIF_WEBHOOK_SECRET",
    "WEBHOOK_TOLERANCE_SECONDS",
    "CORS_ORIGINS",
    "MAX_UPLOAD_MB",
    "BACKEND_ACCESS_TOKEN",
)


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Prevent tests from reading developer shell env vars or backend/.env."""
    for key in _ISOLATED_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    reset_event_publisher()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        reset_event_publisher()


@pytest.fixture
def isolated_sqlite_url(tmp_path) -> str:
    """Provide an isolated per-test SQLite database URL."""
    db_file = (tmp_path / "test_trustlayer.db").as_posix()
    return f"sqlite+aiosqlite:///{db_file}"


@pytest.fixture
def client(
    isolated_sqlite_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Provide a synchronous FastAPI TestClient bound to an isolated SQLite DB."""
    monkeypatch.setenv("DATABASE_URL", isolated_sqlite_url)
    get_settings.cache_clear()
    db_session.set_database_url(isolated_sqlite_url)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        db_session.set_database_url("sqlite+aiosqlite:///:memory:")


@pytest_asyncio.fixture
async def async_db(
    isolated_sqlite_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Initialize an isolated SQLite database for async DB tests and dispose cleanly."""
    monkeypatch.setenv("DATABASE_URL", isolated_sqlite_url)
    get_settings.cache_clear()
    db_session.set_database_url(isolated_sqlite_url)
    await db_session.init_db()
    try:
        yield db_session.AsyncSessionLocal
    finally:
        await db_session.close_db()
        db_session.set_database_url("sqlite+aiosqlite:///:memory:")


@pytest_asyncio.fixture
async def async_client(
    async_db: async_sessionmaker[AsyncSession],
) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an async HTTPX client wired via ASGITransport to an isolated DB."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
