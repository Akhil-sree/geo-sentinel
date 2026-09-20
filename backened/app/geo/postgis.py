"""PostGIS enhancement layer (raw SQL + func — no new dependency).

Canonical storage stays float lat/lng (works on every backend). On
postgresql, migration v6 adds `geog geography(Point,4326)` columns + GIST
indexes; these functions then query them with ST_DWithin. On sqlite the
same functions compute haversine in Python. Return shapes are identical;
`spatial_backend` says which path ran.
"""
import math

from sqlalchemy import func, text

from app.database import DB_BACKEND


def is_postgis(db) -> bool:
    try:
        db.execute(text("SELECT PostGIS_Version()")).scalar()
        return True
    except Exception:
        db.rollback()
        return False


def ensure_postgis(db) -> dict:
    """CREATE EXTENSION + geography columns + GIST indexes (pg only)."""
    if DB_BACKEND != "postgresql":
        return {"applied": False, "reason": "sqlite backend — nothing to do"}
    stmts = [
        "CREATE EXTENSION IF NOT EXISTS postgis",
        ("ALTER TABLE zones ADD COLUMN IF NOT EXISTS geog "
         "geography(Point,4326)"),
        ("UPDATE zones SET geog = ST_MakePoint(longitude, latitude)::geography "
         "WHERE geog IS NULL"),
        "CREATE INDEX IF NOT EXISTS ix_zones_geog ON zones USING GIST (geog)",
        ("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS geog "
         "geography(Point,4326)"),
        ("UPDATE citizen_reports SET geog = ST_MakePoint(longitude, latitude)::geography "
         "WHERE geog IS NULL AND latitude IS NOT NULL"),
        ("CREATE INDEX IF NOT EXISTS ix_reports_geog ON citizen_reports "
         "USING GIST (geog)"),
        ("ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS geog "
         "geography(Point,4326)"),
        ("UPDATE road_segments SET geog = ST_MakePoint(longitude, latitude)::geography "
         "WHERE geog IS NULL AND latitude IS NOT NULL"),
        ("CREATE INDEX IF NOT EXISTS ix_roads_geog ON road_segments "
         "USING GIST (geog)"),
    ]
    try:
        for s in stmts:
            db.execute(text(s))
        db.commit()
        return {"applied": True, "statements": len(stmts)}
    except Exception as e:
        db.rollback()
        return {"applied": False, "reason": str(e)[:200]}


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    d1, d2 = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = (math.sin(d1 / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(d2 / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _pg_point(lat: float, lng: float):
    """Geography literal without geoalchemy (pure func, no new dependency)."""
    return func.ST_GeogFromText(f"POINT({float(lng)} {float(lat)})")


def _geog_col(table_name: str):
    """Free (unbound) reference: compiles without the DDL applied, so the
    postgresql path is testable with no server and no migrated schema."""
    from sqlalchemy import column
    return column("geog")


def _pg_point_within(model, lat: float, lng: float, km: float):
    """ST_DWithin filter fragment for a model with a `geog` column."""
    return func.ST_DWithin(_geog_col(model.__tablename__),
                           _pg_point(lat, lng), km * 1000.0)


def _dist(order_model, lat, lng):
    if DB_BACKEND == "postgresql":
        return func.ST_Distance(_geog_col(order_model.__tablename__),
                                _pg_point(lat, lng))
    return None


def _rows(model, db, lat, lng, km, serialize):
    from app.models_db import Zone  # noqa: F401 (keeps registry warm)
    if DB_BACKEND == "postgresql":
        dcol = _dist(model, lat, lng)
        q = (db.query(model, dcol.label("_pg_d"))
             .filter(_pg_point_within(model, lat, lng, km))
             .order_by(dcol).limit(50))
        try:
            # ST_Distance on geography returns meters → serialize takes km.
            out = [serialize(r, float(m) / 1000.0) for r, m in q.all()]
            for x in out:
                x.pop("_d", None)  # sort key already applied by ORDER BY
            return out, "postgis"
        except Exception:
            db.rollback()  # geog col missing? fall through to haversine
    out = []
    for r in db.query(model).all():
        if getattr(r, "latitude", None) is None:
            continue
        d = _haversine_km(lat, lng, r.latitude, r.longitude or 0.0)
        if d <= km:
            out.append(serialize(r, d))
    out.sort(key=lambda x: x.get("_d", 1e9))
    for x in out:
        x.pop("_d", None)
    return out[:50], "haversine"


def zones_within_km(db, lat, lng, km=30.0):
    from app.models_db import Zone
    rows, backend = _rows(
        Zone, db, lat, lng, km,
        lambda r, d: {"zone_id": r.id, "name": r.name,
                      "dist_km": round(d, 2) if d is not None else None,
                      "_d": d if d is not None else 1e9})
    return {"zones": rows, "spatial_backend": backend}


def reports_within_km(db, lat, lng, km=30.0):
    from app.models_db import CitizenReport
    rows, backend = _rows(
        CitizenReport, db, lat, lng, km,
        lambda r, d: {"report_id": r.id, "status": r.status,
                      "dist_km": round(d, 2) if d is not None else None,
                      "_d": d if d is not None else 1e9})
    return {"reports": rows, "spatial_backend": backend}


def roads_within_km(db, lat, lng, km=30.0):
    from app.models_db import RoadSegment
    rows, backend = _rows(
        RoadSegment, db, lat, lng, km,
        lambda r, d: {"road": r.name, "status": r.status,
                      "dist_km": round(d, 2) if d is not None else None,
                      "_d": d if d is not None else 1e9})
    return {"roads": rows, "spatial_backend": backend}
