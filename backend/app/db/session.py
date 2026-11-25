from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings, normalize_database_url
from app.db.base import Base
from app.db import models  # noqa: F401 - register ORM models


def _build_engine(database_url: str) -> AsyncEngine:
    normalized_url = normalize_database_url(database_url)
    return create_async_engine(normalized_url, pool_pre_ping=True)


engine: AsyncEngine = _build_engine(get_settings().database_url)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def set_database_url(database_url: str, *, dispose_existing: bool = True) -> AsyncEngine:
    """Rebind the shared async engine and sessionmaker in place."""
    global engine
    previous_engine = engine
    new_engine = _build_engine(database_url)
    engine = new_engine
    AsyncSessionLocal.configure(bind=new_engine)
    if dispose_existing and previous_engine is not None:
        previous_engine.sync_engine.dispose()
    return new_engine


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
