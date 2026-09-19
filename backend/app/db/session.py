from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

try:
    from app.core.config import get_settings
except ModuleNotFoundError:
    from backend.app.core.config import get_settings

settings = get_settings()

# Ensure sqlite directory exists (Voroa /tmp/test.db may need /tmp)
if settings.DATABASE_URL.startswith("sqlite"):
    try:
        from pathlib import Path
        # handle sqlite+aiosqlite:////tmp/test.db and sqlite+aiosqlite:///./test.db
        url_path = settings.DATABASE_URL.split("://", 1)[-1]
        # url_path like "///tmp/test.db" or "//./test.db" — strip leading slashes
        # for aiosqlite, "sqlite+aiosqlite:////tmp/test.db" -> "/tmp/test.db"
        # "sqlite+aiosqlite:///./test.db" -> "./test.db"
        if url_path.startswith("///"):
            db_file = "/" + url_path.lstrip("/")
            # Actually "///tmp/test.db" -> "/tmp/test.db"
            db_file = url_path[2:]  # "///tmp/test.db" -> "/tmp/test.db"
            if db_file.startswith("//"):
                db_file = db_file[1:]
        else:
            db_file = url_path
        # handle relative
        p = Path(db_file)
        if not p.is_absolute():
            # try relative to cwd
            p = Path.cwd() / db_file
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[db] sqlite dir create skipped: {e}")


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


try:
    engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))
except Exception as e:
    print(f"[db] engine create failed for {settings.DATABASE_URL}: {e}, fallback to sqlite /tmp/test.db")
    engine = create_async_engine("sqlite+aiosqlite:////tmp/test.db", **_engine_kwargs("sqlite+aiosqlite:////tmp/test.db"))


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
