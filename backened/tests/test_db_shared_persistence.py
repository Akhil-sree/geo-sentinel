"""P0 regression: API and worker share one persistence layer.

Covers the compose sqlite split-brain: a record written through one session
(worker) must be visible through another session (API), and relative sqlite
URLs must resolve to one absolute path independent of CWD.
"""
import os


def test_resolve_relative_sqlite_is_absolute_and_cwd_independent():
    from app.database import BACKEND_DIR, resolve_database_url
    resolved = resolve_database_url("sqlite:///./geo_sentinel.db")
    assert resolved.startswith("sqlite:///")
    path = resolved[len("sqlite:///"):]
    assert os.path.isabs(path)
    assert os.path.normpath(path) == os.path.normpath(
        os.path.join(BACKEND_DIR, "geo_sentinel.db"))


def test_resolve_absolute_sqlite_passes_through():
    import posixpath
    from app.database import resolve_database_url
    resolved = resolve_database_url("sqlite:////data/geo_sentinel.db")
    path = resolved[len("sqlite:///"):]
    # Same absolute location (posix form on Linux containers; the compose path).
    assert posixpath.normpath(path.replace("\\", "/")) == "/data/geo_sentinel.db"


def test_resolve_postgres_passes_through():
    from app.database import resolve_database_url
    url = "postgresql+psycopg2://u:p@postgres/db"
    assert resolve_database_url(url) == url


def test_worker_write_api_read_same_record():
    """Simulate worker write -> API read with two independent sessions."""
    from app.database import SessionLocal
    from app.models_db import Sensor
    worker_db = SessionLocal()
    api_db = SessionLocal()
    sid = "TEST-SHARED-PERSISTENCE-01"
    try:
        worker_db.query(Sensor).filter(Sensor.id == sid).delete()
        worker_db.commit()
        worker_db.add(Sensor(id=sid, sensor_type="rainfall",
                             zone_id=None, status="ONLINE"))
        worker_db.commit()
        seen = api_db.query(Sensor).filter(Sensor.id == sid).first()
        assert seen is not None
        assert seen.id == sid
        assert seen.status == "ONLINE"
    finally:
        worker_db.query(Sensor).filter(Sensor.id == sid).delete()
        worker_db.commit()
        worker_db.close()
        api_db.close()
