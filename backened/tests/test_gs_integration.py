"""GEO-SENTINEL integration tests (§20): inventory, configs, entry point,
inference I/O + invalid handling, API responses. No datasets/ writes.
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DEM_TIF = os.path.join(REPO, "datasets", "n25_e091_1arc_v3.tif")
_MAMBA_NPZ = os.path.join(
    REPO, "datasets", "GEO_SENTINEL_TRAINING_PACKAGE",
    "GEO_SENTINEL_TRAINING_PACKAGE", "MAMBA",
    "meghalaya_mamba_supervised_tensor_15f.npz",
)


def test_inventory_valid_and_numbers_verified():
    with open(os.path.join(REPO, "reports", "dataset_inventory.json"),
              encoding="utf-8") as _inv_fh:
        inv = json.load(_inv_fh)
    assert len(inv["datasets"]) == 18
    by_id = {d["id"]: d for d in inv["datasets"]}
    assert by_id["gs_labels"]["rows"] == 18
    assert by_id["gs_rf"]["rows"] == 54
    assert by_id["gs_mamba"]["tensor"] == [666, 73, 15]
    assert by_id["gs_segformer"]["classification"] == "INSUFFICIENT_FOR_TRAINING"
    assert all("sha256:" in d.get("sha256", "") for d in inv["datasets"])


def test_configs_load():
    import yaml
    for name in ("datasets.yaml", "training.yaml", "models.yaml"):
        with open(os.path.join(
            REPO, "backened", "configs", name), encoding="utf-8") as _cfg_fh:
            cfg = yaml.safe_load(_cfg_fh)
        assert isinstance(cfg, dict) and len(cfg) > 3


def test_train_all_segformer_refuses():
    import subprocess
    r = subprocess.run([sys.executable, "-m", "training.train_all",
                        "--model", "segformer"], capture_output=True, text=True,
                       cwd=os.path.join(REPO, "backened"))
    assert r.returncode == 0 and "BLOCKED" in r.stdout


@pytest.mark.skipif(
    not os.path.exists(_DEM_TIF),
    reason="SRTM raster n25_e091_1arc_v3.tif absent (local-only datasets/)",
)
def test_gs_inference_point_and_invalid():
    from app.ml.gs_inference import assess_point
    ok = assess_point(25.30, 91.70)
    assert set(ok) >= {"risk_score", "risk_level", "susceptibility",
                       "temporal_risk", "landslide_detected", "confidence"}
    assert ok["risk_level"] in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
    gap = assess_point(25.095, 92.357)  # SRTM-gap location: honest UNKNOWN
    assert gap["risk_level"] == "UNKNOWN" and gap["risk_score"] is None
    import pytest
    with pytest.raises(ValueError):
        assess_point(999, 0)


@pytest.mark.skipif(
    not os.path.exists(_MAMBA_NPZ),
    reason="MAMBA tensor npz absent (local-only datasets/)",
)
def test_gs_inference_sequence_and_tabular_invalid():
    import pytest

    from app.ml.gs_inference import assess_sequence, assess_tabular
    z = np.load(os.path.join(
        REPO, "datasets", "GEO_SENTINEL_TRAINING_PACKAGE",
        "GEO_SENTINEL_TRAINING_PACKAGE", "MAMBA",
        "meghalaya_mamba_supervised_tensor_15f.npz"))["X"]
    out = assess_sequence(z[18].tolist(), lat=25.30, lon=91.70)
    assert out["temporal_risk"] is None  # unwired by design (chance-level)
    assert out["sequence_steps"] == 73
    with pytest.raises(ValueError):
        assess_sequence([[0.0] * 14])  # wrong width
    with pytest.raises(ValueError):
        assess_tabular({"Slope_deg": 1.0})  # incomplete schema


@pytest.mark.skipif(
    not os.path.exists(_DEM_TIF),
    reason="SRTM raster n25_e091_1arc_v3.tif absent (local-only datasets/)",
)
def test_gs_api_responses():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import gs as gs_router
    app = FastAPI()
    app.include_router(gs_router.router, prefix="/api")
    c = TestClient(app)
    r = c.get("/api/risk/gs_point", params={"lat": 25.30, "lon": 91.70})
    assert r.status_code == 200 and "risk_level" in r.json()
    r = c.get("/api/risk/gs_point", params={"lat": 999, "lon": 0})
    assert r.status_code == 422  # P2 fix: invalid coords are 422, not 200-with-error
    r = c.post("/api/risk/gs_tabular", json={"features": {"x": 1}})
    assert "risk_level" in r.json()
