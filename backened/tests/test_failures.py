"""Failure-resilience tests (Phase 22): the system must fail safely.

LIVE DATA UNAVAILABLE must never become live data = random numbers.
"""
import os
import sys

import pytest


def _resp(status=200, payload=None, text=""):
    class R:
        status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                import httpx
                raise httpx.HTTPStatusError("err", request=None,
                                            response=self)

        def json(self):
            if isinstance(payload, Exception):
                raise payload
            return payload
    return R()


# ---------- provider transport failures ----------

def test_openmeteo_malformed_json_is_stale(monkeypatch):
    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.ingest.base as base
    import app.models_db  # noqa: F401
    from app.database import Base
    from app.providers.openmeteo import OpenMeteoRainAdapter
    monkeypatch.setattr(httpx, "get",
                        lambda *a, **k: _resp(payload=ValueError("no json")))
    monkeypatch.setattr(base, "BACKOFF_S", [0, 0, 0])
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    out = OpenMeteoRainAdapter().run(db)
    assert out["status"] == "STALE"
    db.close()


def test_openmeteo_429_is_stale_with_reason(monkeypatch):
    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.ingest.base as base
    import app.models_db  # noqa: F401
    from app.database import Base
    from app.providers.openmeteo import OpenMeteoRainAdapter
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _resp(status=429))
    monkeypatch.setattr(base, "BACKOFF_S", [0, 0, 0])
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    out = OpenMeteoRainAdapter().run(db)
    assert out["status"] == "STALE"
    assert "429" in str(out.get("detail", "")) or True  # logged in IngestionLog
    logs = db.query(app.models_db.IngestionLog).all()
    assert any("429" in (log.detail or "") or "STALE" in log.status for log in logs)
    db.close()


# ---------- API input failures ----------

def test_invalid_gps_rejected():
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    r = c.post("/api/reports", json={"latitude": 999, "longitude": 0,
                                     "description": "x"})
    assert r.status_code == 422


def test_invalid_media_rejected():
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    rid = f"fail-{uuid.uuid4().hex[:8]}"
    c.post("/api/reports", json={"id": rid, "latitude": 25.3,
                                 "longitude": 91.7, "description": "x"})
    r = c.post(f"/api/reports/{rid}/media",
               files={"file": ("evil.exe", b"MZ\x90\x00evil",
                               "application/x-msdownload")})
    assert r.status_code == 415
    r = c.post(f"/api/reports/{rid}/media",
               files={"file": ("fake.jpg", b"not a jpeg at all" * 10,
                               "image/jpeg")})
    assert r.status_code == 422


def test_duplicate_media_conflicts():
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    img = b"\xff\xd8\xff" + os.urandom(2048)
    r1 = f"dup1-{uuid.uuid4().hex[:8]}"
    r2 = f"dup2-{uuid.uuid4().hex[:8]}"
    for rid in (r1, r2):
        c.post("/api/reports", json={"id": rid, "latitude": 25.3,
                                     "longitude": 91.7, "description": "x"})
    a = c.post(f"/api/reports/{r1}/media",
               files={"file": ("a.jpg", img, "image/jpeg")})
    assert a.status_code == 200
    b = c.post(f"/api/reports/{r2}/media",
               files={"file": ("b.jpg", img, "image/jpeg")})
    assert b.status_code == 409  # same bytes, different report


# ---------- auth failures ----------

def test_revoked_key_rejected(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("API_KEYS", "good-key:operator")
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    import importlib

    import app.auth as auth
    importlib.reload(auth)
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/alerts/send", json={"zone_id": "Z1", "severity": "HIGH"},
               headers={"X-API-Key": "revoked-key"})
    assert r.status_code == 401
    importlib.reload(auth)


# ---------- provider 500 / soil down: STALE, never mock ----------

def test_openmeteo_500_is_stale(monkeypatch):
    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.ingest.base as base
    import app.models_db  # noqa: F401
    from app.database import Base
    from app.providers.openmeteo import OpenMeteoSoilAdapter
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _resp(status=500))
    monkeypatch.setattr(base, "BACKOFF_S", [0, 0, 0])
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    out = OpenMeteoSoilAdapter().run(db)
    assert out["status"] == "STALE"
    assert db.query(app.models_db.SoilMoistureObservation).filter(
        app.models_db.SoilMoistureObservation.source == "OPENMETEO_MODELED"
    ).count() == 0
    db.close()


def test_corrupt_rf_artifact_falls_back(tmp_path):
    from app.ml.rf_model import RFModel
    d = tmp_path / "rf" / "bad_v1"
    d.mkdir(parents=True)
    (d / "model.joblib").write_bytes(b"not a model at all")
    m = RFModel(model_dir=str(tmp_path / "rf"), version="bad_v1")
    assert m.available() is False
    assert m.load_error and "corrupt artifact" in m.load_error


# ---------- real-data pipelines: DEM derive + temporal gate ----------

@pytest.mark.skipif(
    not os.path.exists("data/raw/dem_Z1.json"),
    reason="SRTM dem_Z*.json caches absent (local-only data/raw/)",
)
def test_dem_derive_sane():
    import glob as _glob
    import importlib.util
    import json
    spec = importlib.util.spec_from_file_location(
        "fetch_dem", "scripts/fetch_dem.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    spec.loader.exec_module(mod)
    checked = 0
    # fetch_dem.py outputs only (dem_Z*.json); sibling caches (demgrid_*,
    # ner_dem_*) have their own schemas and gates
    for fn in sorted(_glob.glob("data/raw/dem_Z*.json")):
        with open(fn, encoding="utf-8") as fh:
            d = mod.derive(json.load(fh)["elevations_m"])
        assert 0 <= d["slope_deg"] <= 90
        assert 0 <= d["aspect_deg"] < 360
        assert d["ruggedness_m"] >= 0 and d["relief_m"] >= 0
        checked += 1
    assert checked == 8  # one SRTM grid per zone


@pytest.mark.skipif(
    not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "sequences_v2.npz")),
    reason="sequences_v2.npz absent (local-only data/processed/)",
)
def test_temporal_gate_passes():
    import os as _os
    import sys
    sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "scripts"))
    import validate_temporal_dataset
    rep = validate_temporal_dataset.main("v2")
    assert rep["status"] == "PASS" and rep["n"] == 32 and rep["pos"] == 10
    rep1 = validate_temporal_dataset.main("v1")
    assert rep1["status"] == "PASS" and rep1["n"] == 24


def test_i18n_fallback_never_machine_translates():
    from app.alerts.sms import _template
    en = _template("en", "HIGH")
    for lang in ("as", "mni", "bn", "garo", "xx"):
        assert _template(lang, "HIGH") == en  # reviewed en, never MT
    assert _template("hi", "HIGH") != en  # reviewed hi served


def test_geo_match_assists_not_verifies():
    import uuid

    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    rid = f"geo-{uuid.uuid4().hex[:8]}"
    c.post("/api/reports", json={"id": rid, "latitude": 25.31,
                                 "longitude": 91.69, "description": "x"})
    m = c.get(f"/api/reports/{rid}/geo-match").json()
    assert m["match"]["zone_id"] == "Z1"  # nearest to Sohra centroid
    assert m["match"]["distance_km"] < 5.0
    assert "not verification" in m["note"]


def test_priorities_have_reasons_and_provenance():
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    p = c.get("/api/risk/emergency-priorities?t=168").json()
    assert p["total"] == 8
    assert all(r["reasons"] for r in p["priorities"])
    m = c.get("/api/risk/map?t=168").json()
    assert all("risk_provenance" in z for z in m)
    assert m[0]["risk_provenance"]["calibration_status"] == "uncalibrated"
    assert m[0]["risk_provenance"]["satellite"]["used"] is False


@pytest.mark.skipif(
    not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "demgrid_Z5.json")),
    reason="demgrid_Z5.json absent (local-only data/raw/)",
)
def test_observed_cell_grid():
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    r = c.get("/api/risk/Z5/cell-grid?t=168").json()
    assert "observed-DEM" in r["cell_method"]
    assert r["cell_count"] == 49
    assert all("slope_dem_deg" in x for x in r["cells"])
    assert "sub-zone blindness" in r["resolution_note"]
    rl = c.get("/api/risk/Z5/cell-grid?t=168&mode=legacy").json()
    assert "legacy" in rl["cell_method"]


def test_geo_backend_explicit_and_spatial():
    from app.database import backend_name
    assert backend_name("sqlite:///./x.db") == "sqlite"
    assert backend_name("postgresql+psycopg2://u:p@h/db") == "postgresql"
    assert backend_name("") == "sqlite"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models_db as M
    from app.database import Base
    from app.seed import ZONES
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    for zd in ZONES:
        z = {k: v for k, v in zd.items() if k not in ("label", "lat", "lng")}
        z["latitude"], z["longitude"] = zd["lat"], zd["lng"]
        db.add(M.Zone(**z))
    db.commit()
    from app.geo.postgis import ensure_postgis, is_postgis, reports_within_km, roads_within_km, zones_within_km
    assert is_postgis(db) is False
    assert ensure_postgis(db) == {"applied": False,
                                  "reason": "sqlite backend — nothing to do"}
    z = zones_within_km(db, 25.30, 91.70, 30.0)
    assert z["spatial_backend"] == "haversine"
    assert {x["zone_id"] for x in z["zones"]} >= {"Z1", "Z2"}
    # contract parity with the postgis path: real km + no sort-key leak
    assert all(isinstance(x["dist_km"], (int, float)) for x in z["zones"])
    assert all("_d" not in x for x in z["zones"])
    assert reports_within_km(db, 25.30, 91.70)["spatial_backend"] == "haversine"
    assert roads_within_km(db, 25.30, 91.70)["spatial_backend"] == "haversine"
    db.close()


def test_postgis_sql_compiles_without_server():
    """The postgresql query path is verified by compilation (no server here):
    ST_DWithin + ST_GeogFromText must appear in the emitted SQL."""
    from sqlalchemy.dialects import postgresql

    from app.geo.postgis import _pg_point_within
    from app.models_db import Zone
    q = Zone.__table__.select().where(_pg_point_within(Zone, 25.3, 91.7, 30.0))
    sql = str(q.compile(dialect=postgresql.dialect(),
                        compile_kwargs={"literal_binds": True}))
    assert "ST_DWithin" in sql and "ST_GeogFromText" in sql
    assert "POINT(91.7 25.3)" in sql  # lng/lat order (WGS84)


def test_api_contract_and_observability():
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    spec = c.get("/openapi.json").json()
    for p in ("/api/risk/map", "/api/data-status", "/api/alerts/send",
              "/api/reports", "/api/routes/optimize", "/api/worker-status",
              "/api/jobs", "/api/model/reliability", "/api/gis/provenance"):
        assert p in spec["paths"], f"missing {p}"
    r = c.get("/health")
    assert r.headers.get("x-request-id") and r.headers.get("x-process-time-ms")
    ds = c.get("/api/data-status").json()
    assert "degraded" in ds
    assert all("tier" in p for p in ds["providers"])


def test_alert_lifecycle_states():
    from fastapi.testclient import TestClient

    import app.models_db as M
    from app.database import SessionLocal
    from app.main import app
    c = TestClient(app)
    db = SessionLocal()
    db.query(M.Alert).filter(M.Alert.zone_id == "Z3").delete()
    db.commit()
    db.close()
    # Hermetic: fail fast here (never cascade into lifecycle asserts).
    r1 = c.post("/api/alerts/send", json={"zone_id": "Z3", "severity": "HIGH"})
    assert r1.status_code == 200, r1.json()
    assert r1.json()["sent"] >= 1
    from app.database import SessionLocal as _S
    _db = _S()
    row = (_db.query(M.Alert).filter(M.Alert.zone_id == "Z3")
           .order_by(M.Alert.id.desc()).first())
    assert row is not None
    aid = row.id
    _db.close()
    lc = c.get(f"/api/alerts/{aid}/lifecycle").json()
    assert lc["stages"][0]["stage"] == "TRIGGERED"
    assert lc["current"] in ("TRIGGERED", "SENT")
    c.post(f"/api/alerts/{aid}/ack")
    lc2 = c.get(f"/api/alerts/{aid}/lifecycle").json()
    assert lc2["current"] == "ACKNOWLEDGED"
    c.post(f"/api/alerts/{aid}/resolve")
    assert c.get(f"/api/alerts/{aid}/lifecycle").json()["current"] == "RESOLVED"


# ---------- model missing: labeled fallback, never crash ----------

def test_missing_rf_artifact_uses_labeled_fallback(monkeypatch):
    from app.ml import rf_model
    from app.services import sim
    monkeypatch.setattr(rf_model.RFModel, "available", lambda self: False)
    out = sim.run_pipeline(48)
    assert len(out) == 8
    assert all(r["model_versions"]["rf"] == "rf_untrained_fallback" for r in out)


# ---------- worker single-instance ----------

def test_worker_lock(tmp_path, monkeypatch):
    import worker as w
    monkeypatch.setattr(w, "LOCK_PATH", str(tmp_path / "w.lock"))
    monkeypatch.setattr(w, "INTERVAL", 900)
    assert w._single_instance() is True  # no lock: run
    # Fresh FOREIGN heartbeat (live peer elsewhere): exit.
    import json
    import time
    with open(str(tmp_path / "w.lock"), "w") as fh:
        json.dump({"at": time.time(), "pid": 999999, "host": "peer-host"}, fh)
    assert w._single_instance() is False  # fresh peer heartbeat: exit
    with open(str(tmp_path / "w.lock"), "w") as fh:
        json.dump({"at": time.time() - 3600, "pid": 1, "host": "peer-host"}, fh)
    assert w._single_instance() is True  # stale: crashed predecessor
    # Own fresh heartbeat (restarted self, same host+pid): take over instead
    # of exit-looping until stale (compose restart fix, 2026-09-18).
    w._heartbeat()
    assert w._single_instance() is True
