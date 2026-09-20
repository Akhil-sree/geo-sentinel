"""Hardening regression tests (P1/P2 remediation).

Covers: HTTP error semantics (422/503, not 200-with-error), input bounds,
path-traversal blocks, production-closed CORS/auth defaults, safe torch
loading, and ReportIn validation.
"""
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEM_TIF = os.path.join(_REPO, "datasets", "n25_e091_1arc_v3.tif")
_MAMBA_NPZ = os.path.join(
    _REPO, "datasets", "GEO_SENTINEL_TRAINING_PACKAGE",
    "GEO_SENTINEL_TRAINING_PACKAGE", "MAMBA",
    "meghalaya_mamba_supervised_tensor_15f.npz",
)

from app.api import gs as gs_router  # noqa: E402


def _gs_client():
    app = FastAPI()
    app.include_router(gs_router.router, prefix="/api")
    return TestClient(app)


def test_gs_point_out_of_range_returns_422():
    c = _gs_client()
    r = c.get("/api/risk/gs_point", params={"lat": 999, "lon": 0})
    assert r.status_code == 422
    r = c.get("/api/risk/gs_point", params={"lat": 25.3, "lon": 991})
    assert r.status_code == 422


@pytest.mark.skipif(
    not os.path.exists(_DEM_TIF),
    reason="SRTM raster n25_e091_1arc_v3.tif absent (local-only datasets/)",
)
def test_gs_point_valid_still_200_with_null_temporal():
    c = _gs_client()
    r = c.get("/api/risk/gs_point", params={"lat": 25.30, "lon": 91.70})
    assert r.status_code == 200
    body = r.json()
    assert body["temporal_risk"] is None
    assert body["risk_level"] in ("LOW", "MODERATE", "HIGH", "VERY_HIGH",
                                  "UNKNOWN")


def test_gs_point_out_of_coverage_returns_null_not_error():
    c = _gs_client()
    r = c.get("/api/risk/gs_point", params={"lat": 25.095, "lon": 92.357})
    assert r.status_code == 200
    assert r.json()["risk_score"] is None


def test_gs_tabular_empty_returns_422():
    c = _gs_client()
    r = c.post("/api/risk/gs_tabular", json={"features": {}})
    assert r.status_code == 422
    assert r.json()["risk_level"] == "UNKNOWN"


def test_gs_sequence_empty_and_oversize_return_422():
    c = _gs_client()
    assert c.post("/api/risk/gs_sequence",
                  json={"sequence": []}).status_code == 422
    big = [[0.0] * 15] * 1001
    assert c.post("/api/risk/gs_sequence",
                  json={"sequence": big}).status_code == 422
    wrong_width = [[0.0] * 14] * 5
    assert c.post("/api/risk/gs_sequence",
                  json={"sequence": wrong_width}).status_code == 422


@pytest.mark.skipif(
    not os.path.exists(_MAMBA_NPZ),
    reason="MAMBA tensor npz absent (local-only datasets/)",
)
def test_gs_sequence_valid_returns_null_temporal():
    c = _gs_client()
    seq = [[0.1] * 15] * 49
    r = c.post("/api/risk/gs_sequence",
               json={"sequence": seq, "lat": 25.30, "lon": 91.70})
    assert r.status_code == 200
    body = r.json()
    assert body["temporal_risk"] is None
    assert body["sequence_steps"] == 49


def test_gs_model_missing_returns_503(monkeypatch):
    import app.api.gs as gsm
    monkeypatch.setattr(gsm, "assess_point",
                        lambda *a, **k: (_ for _ in ()).throw(
                            OSError("no such file")))
    c = _gs_client()
    r = c.get("/api/risk/gs_point", params={"lat": 25.3, "lon": 91.7})
    assert r.status_code == 503
    assert "risk_level" in r.json()


def test_cors_production_fails_closed(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main._cfg, "ENVIRONMENT", "production")
    monkeypatch.setattr(main._cfg, "CORS_ORIGINS", "*")
    assert main._cors_origins() == []
    monkeypatch.setattr(main._cfg, "CORS_ORIGINS",
                        "https://example.com, https://app.example.com")
    assert main._cors_origins() == ["https://example.com",
                                    "https://app.example.com"]
    monkeypatch.setattr(main._cfg, "ENVIRONMENT", "development")
    monkeypatch.setattr(main._cfg, "CORS_ORIGINS", "*")
    assert main._cors_origins() == ["*"]


def test_auth_open_demo_dev_but_closed_in_production(monkeypatch):
    from app.auth import guard
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_KEYS", raising=False)
    import app.auth as authmod
    monkeypatch.setattr(authmod, "ADMIN_API_KEY", "")
    assert guard(None) == {"auth_mode": "open-demo"}
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(Exception) as e:
        guard(None)
    assert getattr(e.value, "status_code", None) == 401


def test_meta_blocks_traversal():
    from app.api.datasets import _meta
    assert _meta("../../secret.json") is None
    assert _meta("/etc/passwd") is None
    assert _meta("..%2f..%2fsecret.json") is None
    assert _meta("not-a-real-report.json") is None


def test_dataset_version_traversal_returns_404():
    from fastapi import FastAPI as _F

    from app.api import datasets as ds
    app = _F()
    app.include_router(ds.router, prefix="/api")
    c = TestClient(app)
    r = c.get("/api/datasets/..%2F..%2Fsecret")
    assert r.status_code in (404, 422)


def test_observed_cells_blocks_traversal():
    from app.api.risk import _observed_cells
    cells, reason = _observed_cells("../../etc/passwd")
    assert cells is None
    cells, reason = _observed_cells("..\\windows\\win")
    assert cells is None


def test_report_accuracy_non_numeric_rejected():
    from pydantic import ValidationError

    from app.schemas import ReportIn
    with pytest.raises(ValidationError):
        ReportIn(latitude=25.3, longitude=91.7, accuracy="abc")
    ok = ReportIn(latitude=25.3, longitude=91.7, accuracy="12.5")
    assert ok.accuracy == 12.5


def test_mamba_checkpoint_loads_weights_only():
    torch = pytest.importorskip("torch")
    ckpt = os.path.join(os.path.dirname(__file__), "..", "models",
                        "mamba", "gs_v1", "checkpoints", "fold0.pt")
    if not os.path.exists(ckpt):
        pytest.skip("mamba checkpoint absent (correctly unused live)")
    obj = torch.load(ckpt, map_location="cpu", weights_only=True)
    assert isinstance(obj, dict)


def test_worker_helpers_defined_before_main_loop():
    """Regression (compose 2026-09-18): `_mark_sensor_health` was defined
    AFTER the blocking `if __name__ == '__main__'` loop, so every worker
    cycle failed with NameError. Helpers must precede the main guard."""
    import ast
    with open(os.path.join(os.path.dirname(__file__), "..", "worker.py"),
              encoding="utf-8") as _w_fh:
        src = _w_fh.read()
    tree = ast.parse(src)
    main_line = next(n.lineno for n in ast.walk(tree)
                     if isinstance(n, ast.If)
                     and isinstance(n.test, ast.Compare)
                     and isinstance(n.test.left, ast.Name)
                     and n.test.left.id == "__name__")
    helpers = [n.lineno for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)
               and n.name == "_mark_sensor_health"]
    assert helpers and all(h < main_line for h in helpers)


def test_worker_restart_self_takes_over_but_peer_blocked(tmp_path, monkeypatch):
    """Regression (compose 2026-09-18): `restart worker` exit-looped because
    the new process saw its own pre-restart heartbeat as a live peer.
    Same host+pid (only possible for a restarted self) takes over; a fresh
    foreign heartbeat still blocks; a stale one is taken over."""
    import json
    import time

    import worker as w
    monkeypatch.setattr(w, "LOCK_PATH", str(tmp_path / ".worker.lock"))
    monkeypatch.setattr(w, "INTERVAL", 900.0)
    me = w._owner()
    # own fresh heartbeat -> take over
    with open(w.LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump({"at": time.time(), **me}, f)
    assert w._single_instance() is True
    # foreign fresh heartbeat -> blocked
    with open(w.LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump({"at": time.time(), "pid": me["pid"] + 999999,
                   "host": "other-host"}, f)
    assert w._single_instance() is False
    # stale foreign heartbeat -> take over
    with open(w.LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump({"at": time.time() - 3 * 900.0, "pid": 1, "host": "h"}, f)
    assert w._single_instance() is True
    # release removes only our own lock
    with open(w.LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump({"at": time.time(), **me}, f)
    w._release()
    assert not os.path.exists(w.LOCK_PATH)


@pytest.mark.skipif(
    not os.path.exists(_DEM_TIF),
    reason="SRTM raster n25_e091_1arc_v3.tif absent (local-only datasets/)",
)
def test_known_coordinate_regression():
    """Map/GIS: a known in-coverage coordinate gives a stable HIGH static
    assessment; swapped lat/lon is rejected (no silent wrong-location risk)."""
    from app.ml.gs_inference import assess_point
    out = assess_point(25.30, 91.70)
    assert out["risk_level"] == "HIGH"
    assert 0.6 < out["risk_score"] < 0.8
    assert out["temporal_risk"] is None
    with pytest.raises(ValueError):
        assess_point(91.70, 25.30)  # swapped: lat out of range, must not assess


def test_torch_load_uses_weights_only():
    import inspect

    import app.ml.gs_inference as gsi
    src = inspect.getsource(gsi.mamba_ensemble)
    assert "weights_only=True" in src
    # No unsafe torch.load remains anywhere in the request-serving code.
    import re
    appdir = os.path.join(os.path.dirname(__file__), "..", "app")
    bad = []
    for root, _, files in os.walk(appdir):
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                with open(p, encoding="utf-8") as _s_fh:
                    s = _s_fh.read()
                if re.search(r"torch\.load\(", s) and "weights_only=True" not in s:
                    bad.append(p)
    assert bad == [], f"unsafe torch.load in: {bad}"
