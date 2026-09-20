"""Versioned migration entrypoint (Phase 9B/10/17).

Runs against DATABASE_URL (SQLite demo default; Postgres/PostGIS in prod).
Steps are numbered, idempotent, recorded in schema_versions, and never
destructive. Docker backend runs this before uvicorn. Alembic remains the
roadmap for complex schema evolution; this ledger is the real mechanism
in use (not bare create_all).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, engine, SessionLocal  # noqa: E402
import app.models_db as M  # noqa: E402,F401 — register all tables
from app.seed import seed  # noqa: E402

SCHEMA_VERSION = 9


def _v1_create_all(db):
    Base.metadata.create_all(engine)
    return "core tables ensured"


def _v2_media_hashes(db):
    M.MediaHash.__table__.create(engine, checkfirst=True)
    n = db.query(M.MediaHash).count()
    return f"media_hashes ensured ({n} rows kept)"


def _v3_reference_data(db):
    seed(db)
    zones = db.query(M.Zone).count()
    return f"reference data ensured ({zones} zones)"


def _v4_terrain_dem(db):
    M.TerrainDEM.__table__.create(engine, checkfirst=True)
    n = db.query(M.TerrainDEM).count()
    return f"terrain_dem ensured ({n} rows kept; fetch via scripts/fetch_dem.py)"


def _v5_sat_scenes(db):
    M.SatScene.__table__.create(engine, checkfirst=True)
    n = db.query(M.SatScene).count()
    return f"sat_scenes ensured ({n} rows kept; metadata only, no risk use)"


def _v6_postgis(db):
    """PostGIS enhancement (postgresql only): extension + geography columns
    + GIST indexes. On sqlite: explicit skip (no-op, still stamped)."""
    from app.geo.postgis import ensure_postgis
    out = ensure_postgis(db)
    if out.get("applied"):
        return f"postgis enabled ({out['statements']} statements)"
    return f"postgis skipped: {out.get('reason')}"


def _v7_sensors_exposure(db):
    for t in (M.Sensor.__table__, M.SensorReading.__table__,
              M.Village.__table__, M.Infrastructure.__table__):
        t.create(engine, checkfirst=True)
    seed(db)  # idempotent backfill of villages/infrastructure
    return (f"sensors+exposure ensured "
            f"({db.query(M.Sensor).count()} sensors, "
            f"{db.query(M.Village).count()} villages, "
            f"{db.query(M.Infrastructure).count()} infra)")


def _v8_sat_inventory(db):
    for t in (M.SpatialInventory.__table__, M.SatelliteFeature.__table__):
        t.create(engine, checkfirst=True)
    return "satellite_features+spatial_inventory ensured"


def _v9_ner_pipeline(db):
    for t in (M.NerInventory.__table__, M.DatasetVersion.__table__,
              M.TrainingSample.__table__):
        t.create(engine, checkfirst=True)
    return "ner_inventory+dataset_versions+training_samples ensured"


STEPS = {1: _v1_create_all, 2: _v2_media_hashes, 3: _v3_reference_data,
         4: _v4_terrain_dem, 5: _v5_sat_scenes, 6: _v6_postgis,
         7: _v7_sensors_exposure, 8: _v8_sat_inventory, 9: _v9_ner_pipeline}


def current_version(db) -> int:
    try:
        rows = db.query(M.SchemaVersion).all()
        return max([r.version for r in rows], default=0)
    except Exception:
        db.rollback()
        return 0


def main() -> None:
    print(f"[migrate] DATABASE_URL={os.getenv('DATABASE_URL', 'sqlite default')}")
    db = SessionLocal()
    try:
        cur = current_version(db)
        for v in range(cur + 1, SCHEMA_VERSION + 1):
            note = STEPS[v](db)
            db.add(M.SchemaVersion(version=v, note=note))
            db.commit()
            print(f"[migrate] v{v} applied: {note}")
        if cur >= SCHEMA_VERSION:
            print(f"[migrate] already at v{SCHEMA_VERSION}, nothing to do")
    finally:
        db.close()
    from app.ml.rf_model import MODEL_DIR, VERSION
    if not os.path.exists(os.path.join(MODEL_DIR, VERSION, "model.joblib")):
        from app.ml.train_rf import main as train_main
        train_main()
    print("[migrate] done")


if __name__ == "__main__":
    main()
