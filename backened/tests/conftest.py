"""Session-scoped boot: create schema + seed before any test runs.

The app creates tables and seeds in app.main's lifespan, which only executes
inside `with TestClient(app)`. Most tests instantiate TestClient(app) bare, so
on a fresh checkout (no pre-existing database) every DB-backed test would fail
with `no such table`.

The engine is pointed at a disposable test database by `TEST_DATABASE_URL`
(app/database.py resolves it at import time), so this fixture boots the same
schema, on the same engine, that the API, worker and tests all share.

API dependency override guarantees every TestClient request routes through the
same test engine (no sibling caller silently using a different default DB).
Worker uses the same SessionLocal, so the same file underpins worker checks.
"""
import pytest

import app.models_db  # noqa: F401,F403 - register all tables on Base
from app.database import Base, SessionLocal, engine, get_db
from app.seed import seed


@pytest.fixture(scope="session", autouse=True)
def _boot_schema_once():
    # Ensure every ORM model is registered before create_all

    Base.metadata.create_all(bind=engine)
    # API must use the same test DB as fixtures/worker — override get_db
    from app.main import app

    def _get_test_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield
    # Teardown: remove override and dispose engine
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_schema_requires_expected_tables():

    from app.database import Base

    required = {
        "zones",
        "sensors",
        "ingestion_runs",
        "audit_logs",
        "risk_scores",
    }
    present = set(Base.metadata.tables.keys())
    missing = sorted(t for t in required if t not in present)
    assert missing == [], f"schema missing required tables: {missing}"