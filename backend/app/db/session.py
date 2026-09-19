from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _engine_kwargs(url: str) -> dict:
    """Return kwargs for create_async_engine.

    Always enables ``pool_pre_ping`` for resilience. Adds ``connect_args``
    ``timeout`` only for PostgreSQL (postgresql+asyncpg / postgresql+psycopg);
    SQLite (sqlite+aiosqlite) needs no extra connect_args.
    """
    kwargs: dict = {"echo": False, "future": True, "pool_pre_ping": True}
    # Detect postgres by URL prefix — covers postgresql+asyncpg and postgresql+psycopg
    if url.startswith("postgresql") or url.startswith("postgres"):
        kwargs["connect_args"] = {"timeout": 10}
    elif url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))


def get_engine() -> AsyncEngine:
    """Return the shared async engine (for reuse e.g. in Alembic or tests)."""
    return engine

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
