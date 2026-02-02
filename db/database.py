from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_config
from db.models import Base

_engine = None
_async_session_maker = None


def get_async_engine():
    global _engine
    if _engine is None:
        config = get_config()
        # Convert to async driver URL
        db_url = config.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(db_url, echo=False)
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    Startup hook.

    We intentionally do NOT auto-create tables here because production schema
    should be managed via Alembic migrations.
    """
    engine = get_async_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db():
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
