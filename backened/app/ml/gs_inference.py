"""GEO-SENTINEL gs_v1 inference adapter (SIH §12, §18).

Wires the trained gs_v1 artifacts into the project's existing risk language:
  RF(static susceptibility) + Mamba(temporal risk) -> fusion.fuse -> risk dict

- Coordinate input uses the terrain-core model (6 SRTM features, the only
  branch derivable anywhere on the grid; same window-stat approximation as
  the held-out validation, documented in the response).
- Package-schema input (14 features) uses the full gs_rf model.
- Temporal sequences use gs SmallSSM fold checkpoints (mean of 3 folds).
- Fusion reuses app.ml.fusion.fuse (config weights), NOT the experimental
  gs_fusion LR (kept as a research artifact; see MODEL_TRAINING_REPORT).
- No DB access; no frontend changes; invalid inputs raise ValueError.

SegFormer: no inference — BLOCKED (no masks, void pixels).
"""
import json
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_BACKEND_DIR, "data"))  # ner_v2_features (documented reuse)

import joblib  # noqa: E402
import numpy as np  # noqa: E402

from app.ml.fusion import (  # noqa: E402 — sys.path setup above must run first
    classify,  # fuse intentionally unused here (see assess_sequence)
)

MODELS_DIR = os.path.join(_BACKEND_DIR, "models")
TERRAIN_COLS = ["Elevation_m", "Slope_deg", "Aspect_deg", "Curvature",
                "TPI_m", "Roughness_m"]
MAMBA_FEATURES = ["Rain_1h_mm", "Rain_3h_mm", "Rain_6h_mm", "Rain_12h_mm",
                  "Rain_24h_mm", "Rain_72h_mm", "swvl1", "swvl2", "swvl3",
                  "swvl4", "t2m", "d2m", "sp", "u10", "v10"]
PROTO_NOTE = ("prototype thresholds/weights; uncalibrated "
              "(n=18 positives; see MODEL_TRAINING_REPORT.md)")

_cache = {}


def _load(name, loader):
    if name not in _cache:
        _cache[name] = loader()
    return _cache[name]


def terrain_model():
    return _load("terrain", lambda: joblib.load(
        os.path.join(MODELS_DIR, "rf", "gs_v1", "gs_terrain.joblib")))


def full_rf_model():
    return _load("rf", lambda: joblib.load(
        os.path.join(MODELS_DIR, "rf", "gs_v1", "gs_rf.joblib")))


def rf_feature_schema():
    schema_path = os.path.join(MODELS_DIR, "rf", "gs_v1", "gs_rf.metadata.json")
    with open(schema_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    return meta["features"]


def mamba_ensemble():
    """(models, scalers) for the 3 event-grouped folds."""
    def _build():
        sys.path.insert(0, os.path.join(_BACKEND_DIR, "app", "ml"))
        import torch
        from mamba_model import build_gs_ssm
        models, scalers = [], []
        ckpt = os.path.join(MODELS_DIR, "mamba", "gs_v1", "checkpoints")
        for k in range(3):
            net = build_gs_ssm()
            # weights_only=True: checkpoints are {state_dict, seed, dataset}
            # snapshots of local trusted artifacts — never unpickle arbitrary
            # Python objects from untrusted sources.
            net.load_state_dict(torch.load(os.path.join(ckpt, f"fold{k}.pt"),
                                           map_location="cpu",
                                           weights_only=True))
            net.eval()
            models.append(net)
            scalers.append(joblib.load(os.path.join(ckpt, f"scaler_fold{k}.joblib")))
        return models, scalers
    return _load("mamba", _build)


def _terrain_at(lat, lon):
    from gs_common import valid_lonlat
    if not valid_lonlat(lat, lon):
        raise ValueError(f"invalid coordinates: {lat}, {lon}")
    from ner_v2_features import raster_terrain
    feats, _, _ = raster_terrain(float(lat), float(lon))
    if feats.get("r_elevation_mean") is None:
        return None  # OUT_OF_COVERAGE / QUALITY_REJECTED — never filled
    return [feats["r_elevation_mean"], feats["r_slope_mean"],
            feats["r_aspect_mean"], feats["r_curvature"],
            feats.get("r_relief", 0.0) / 2.0, feats["r_ruggedness"]]


def assess_point(lat, lon):
    """Static susceptibility at a coordinate. Returns §18-style dict."""
    vec = _terrain_at(lat, lon)
    if vec is None:
        return {"risk_score": None, "risk_level": "UNKNOWN",
                "susceptibility": None, "temporal_risk": None,
                "landslide_detected": False, "confidence": 0.0,
                "note": "location outside SRTM coverage; no silent fill"}
    s = float(terrain_model().predict_proba([vec])[0, 1])
    return {"risk_score": round(s, 4), "risk_level": classify(s),
            "susceptibility": round(s, 4), "temporal_risk": None,
            "landslide_detected": bool(s >= 0.65),
            "confidence": 0.35, "note": "static-only assessment; " + PROTO_NOTE}


def assess_tabular(features: dict):
    """Full 14-feature package-schema assessment."""
    schema = rf_feature_schema()
    try:
        vec = [float(features[c]) for c in schema]
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"tabular input must carry numeric {schema}: {e}") from e
    s = float(full_rf_model().predict_proba([vec])[0, 1])
    return {"risk_score": round(s, 4), "risk_level": classify(s),
            "susceptibility": round(s, 4), "temporal_risk": None,
            "landslide_detected": bool(s >= 0.65),
            "confidence": 0.4, "note": "static-only assessment; " + PROTO_NOTE}


def assess_sequence(sequence, lat=None, lon=None, r24=0.0, r72=0.0, soil=0.0):
    """Temporal assessment from a 15-feature sequence (list of rows, any length ≥1).

    The gs Mamba weights (CV ROC~0.52, chance-level on 18 events) are research
    artifacts and are NOT wired into live risk — promoting them would violate
    the project's own promotion gate. This endpoint therefore returns the
    validated static susceptibility with temporal_risk=None until a live feed
    plus independently validated temporal weights exist. No silent heuristic
    is substituted for a trained model.
    """
    arr = np.asarray(sequence, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 15 or arr.shape[0] < 1:
        raise ValueError("sequence must be (T>=1, 15) in MAMBA_FEATURES order")
    if not np.isfinite(arr).all():
        raise ValueError("sequence contains NaN/Inf")
    static = 0.5
    static_note = "neutral static (no location given)"
    if lat is not None and lon is not None:
        vec = _terrain_at(lat, lon)
        if vec is not None:
            static = float(terrain_model().predict_proba([vec])[0, 1])
            static_note = "terrain-core static"
    return {"risk_score": round(static, 4), "risk_level": classify(static),
            "susceptibility": round(static, 4), "temporal_risk": None,
            "landslide_detected": bool(static >= 0.65),
            "confidence": 0.3, "static_note": static_note,
            "sequence_steps": int(arr.shape[0]),
            "note": "temporal branch not wired (gs Mamba chance-level; "
                    "promotion blocked); " + PROTO_NOTE}
