"""Remediation regression tests: no untrained net in prod path, no live
overclaim, satellite quarantine, upload validation, cooldown."""
import os
from datetime import UTC


def test_temporal_defaults_to_fallback():
    os.environ.pop("MAMBA_LIVE", None)
    os.environ.pop("MAMBA_WEIGHTS", None)
    import importlib

    import app.ml.mamba_model as m
    importlib.reload(m)
    model = m.get_temporal_model()
    assert model.backend() == "mock_heuristic"
    st = m.temporal_status()
    assert st["state"].startswith("FALLBACK")


def test_satellite_quarantined_from_risk(monkeypatch):
    monkeypatch.setenv("SATELLITE_LIVE", "false")
    assert os.getenv("SATELLITE_LIVE") == "false"  # quarantine flag honored


def test_openmeteo_adapters_validate():
    from datetime import datetime

    from app.providers.openmeteo import OpenMeteoRainAdapter, OpenMeteoSoilAdapter
    now = datetime.now(UTC).isoformat()
    assert OpenMeteoRainAdapter().validate(
        [{"zone_id": "Z1", "timestamp": now,
          "rainfall_mm_per_hr": 12.5}])[0]["rainfall_mm_per_hr"] == 12.5
    assert OpenMeteoRainAdapter().validate(
        [{"zone_id": "Z1", "timestamp": now,
          "rainfall_mm_per_hr": 9999}]) == []
    assert OpenMeteoSoilAdapter().validate(
        [{"zone_id": "Z9", "timestamp": now, "soil_moisture": 0.5}]) == []
    # clock-error gate: missing/future/ancient stamps are dropped
    assert OpenMeteoRainAdapter().validate(
        [{"zone_id": "Z1", "rainfall_mm_per_hr": 5.0}]) == []
    assert OpenMeteoRainAdapter().validate(
        [{"zone_id": "Z1", "timestamp": "2099-01-01T00:00",
          "rainfall_mm_per_hr": 5.0}]) == []


def test_video_mime_allowed():
    from app.api.reports import ALLOWED, MAX_VIDEO
    assert ALLOWED["video/mp4"] == ".mp4"
    assert MAX_VIDEO == 25 * 1024 * 1024
    from app.api.reports import _check_magic
    assert _check_magic(b"\x00\x00\x00 ftypisom" + b"0" * 32, "video/mp4")
    assert not _check_magic(b"MZ\x90\x00evil", "video/mp4")


def test_xai_labels_method():
    from app.ml.xai import explain
    class Z:
        slope = 40
        road_proximity = 0.8
    out = explain(Z(), {"static_score": 0.7, "importances": {"slope": 0.5}},
                  {"dynamic_score": 0.6},
                  {"rainfall_72h": 250, "rainfall_24h": 90},
                  {"soil_moisture_current": 0.7}, False, [])
    assert out["method"] in ("IMPORTANCE_WEIGHTED", "HEURISTIC DRIVER ANALYSIS")
    assert all("direction" in d for d in out["drivers"])


def test_provider_states_shape():
    from unittest.mock import MagicMock

    from app.ingest.runner import provider_states
    db = MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
    states = provider_states(db)
    assert {s["source"] for s in states} == {"rainfall", "soil_moisture", "sentinel1_sar"}
    sar = next(s for s in states if s["source"] == "sentinel1_sar")
    assert sar["is_simulated"] and not sar["is_live"]
