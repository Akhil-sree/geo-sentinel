import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import DATABASE_URL, TEST_DATABASE_URL

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_log = logging.getLogger("geo-sentinel")

# Single engine for the whole process (API, worker, scripts, tests). A test
# run points it at a disposable file via TEST_DATABASE_URL, resolved here at
# import time so every `from app.database import SessionLocal` consumer binds
# to the same writable test database.
_ACTIVE_URL = TEST_DATABASE_URL or DATABASE_URL


def backend_name(url: str = DATABASE_URL) -> str:
    """Explicit backend label — sqlite (demo/local) or postgresql (prod).

    Never silently fall back: a postgresql URL that cannot connect raises
    at first use (no sqlite substitution anywhere in this codebase).
    """
    u = (url or "").lower()
    if u.startswith(("postgresql://", "postgres://",
                     "postgresql+psycopg2://")):
        return "postgresql"
    return "sqlite"


DB_BACKEND = backend_name(_ACTIVE_URL)


def resolve_database_url(url: str = _ACTIVE_URL) -> str:
    """Resolve a sqlite URL to an absolute file path (P0 split-brain fix).

    Relative sqlite URLs (`sqlite:///./x.db`, `sqlite:///x.db`) used to
    resolve against the process working directory, so the API and the worker
    (different CWDs / container filesystems) silently used different files.
    Relative paths are now anchored at the backend directory; absolute paths
    (e.g. compose `sqlite:////data/geo_sentinel.db` on a shared volume) pass
    through unchanged. Postgres URLs pass through unchanged.

    In-memory sqlite (`sqlite:///:memory:`) performs no filesystem operation
    and is returned unchanged (caller must use StaticPool).
    """
    if backend_name(url) != "sqlite":
        return url
    # In-memory: no filesystem operation, preserve original URL intact
    if ":memory:" in url:
        return url
    # Use SQLAlchemy URL parsing where available for robust handling
    raw = None
    try:
        from sqlalchemy.engine.url import make_url

        u = make_url(url)
        # u.database is None for bare sqlite://, ":memory:" for memory
        if u.database is not None:
            raw = u.database
    except Exception:
        raw = None
    if raw is None:
        raw = url[len("sqlite:///"):] if url.startswith("sqlite:///") else url
    # A leading "/" is absolute-intent (Linux container path such as the
    # compose /data volume); os.path.isabs misses it on Windows dev hosts.
    if os.path.isabs(raw) or raw.startswith("/"):
        path = os.path.normpath(raw)
        # Absolute paths are host-specific (e.g. compose /data volume);
        # do NOT prepend BACKEND_DIR and do NOT mkdir /data on CI.
    else:
        while raw.startswith("./"):
            raw = raw[2:]
        path = os.path.normpath(os.path.join(BACKEND_DIR, raw))
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    return f"sqlite:///{path}"


RESOLVED_DATABASE_URL = resolve_database_url()
_log.warning("database backend=%s url=%s", DB_BACKEND, RESOLVED_DATABASE_URL)

# check_same_thread=False is safe here: demo uses a single uvicorn worker.
# MULTI-WORKER WARNING: SQLite does NOT support concurrent writers.
# For horizontal scaling (multiple uvicorn/worker processes), PostgreSQL is REQUIRED.
# The docker-compose production profile (--profile prod) uses Postgres+PostGIS.
# pool_pre_ping drops dead postgres connections instead of serving errors.
# In-memory sqlite requires StaticPool so every SessionLocal sees the same DB.
if ":memory:" in RESOLVED_DATABASE_URL:
    engine = create_engine(
        RESOLVED_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        RESOLVED_DATABASE_URL,
        connect_args=({"check_same_thread": False}
                      if DB_BACKEND == "sqlite" else {}),
        pool_pre_ping=(DB_BACKEND == "postgresql"),
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
