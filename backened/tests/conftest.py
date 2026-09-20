"""Session-scoped boot: create schema + seed before any test runs.

The app creates tables and seeds in app.main's lifespan, which only executes
inside `with TestClient(app)`. Most tests instantiate TestClient(app) bare, so
on a fresh checkout (no pre-existing geo_sentinel.db) every DB-backed test
would fail with `no such table`. This mirrors the lifespan boot once per
session so any clone/CI runner passes regardless of a local db file.
"""
import pytest

import app.models_db  # noqa: F401,F403 - register all tables on Base
from app.database import Base, SessionLocal, engine
from app.seed import seed


@pytest.fixture(scope="session", autouse=True)
def _boot_schema_once():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield