"""GEO-SENTINEL pipeline tests (§34): data guards, split integrity, model I/O, GIS.

Run: pytest tests/test_geosentinel.py -q   (from backened/)
All tests are read-only w.r.t. datasets/ (BLOCKED artefacts excepted).
"""
import csv
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from gs_common import (  # noqa: E402
    RF_CSV, MAMBA_NPZ, MAMBA_CSV, normalize_event_id, valid_lonlat,
    validate_rf_rows, validate_mamba_npz, segformer_gate, event_groups_rf,
    SEGFORMER_STATUS,
)

RF_ROWS = list(csv.DictReader(open(RF_CSV, encoding="utf-8")))


def test_event_id_normalization():
    assert normalize_event_id("LS_10,985") == "10985"
    assert normalize_event_id("10,985") == "10985"
    assert normalize_event_id("10985") == "10985"
    assert normalize_event_id("BG_001__10,985".split("__")[-1]) == "10985"
    with pytest.raises(ValueError):
        normalize_event_id("")


def test_coordinate_validation():
    assert valid_lonlat(25.5, 91.8) and not valid_lonlat(255, 91.8)
    assert not valid_lonlat("x", 91.8) and not valid_lonlat(None, None)


def test_rf_validation_passes_and_flags_pseudo_absence():
    rep = validate_rf_rows(RF_ROWS)
    assert rep["n_rows"] == 54 and rep["n_pos"] == 18 and rep["n_neg"] == 36
    assert set(rep["feature_cols"]) and "Landslide_Label" not in rep["feature_cols"]


def test_rf_validation_rejects_bad_labels():
    bad = [dict(r, Landslide_Label="2") for r in RF_ROWS[:3]]
    with pytest.raises(ValueError):
        validate_rf_rows(bad)


def test_rainfall_qc_gates_respected():
    from gs_common import rainfall_qc_stats
    qc = rainfall_qc_stats()
    assert qc["manual_1991_2020"]["rejected_sentinel"] > 0  # -999 present
    assert qc["tel_2021_2025"]["rejected_spike_gt_500.0"] > 0  # spikes present
    assert all(v["accepted"] > 0 for v in qc.values())


def test_crs_guard_state_boundary_is_projected():
    import json as _json
    gj = _json.load(open(os.path.join(
        os.path.dirname(RF_CSV), "..", "..", "..", "state_NWIC.GeoJSON"),
        encoding="utf-8"))
    crs = gj.get("crs", {}).get("properties", {}).get("name", "")
    assert "7755" in crs, "boundary CRS assumption changed — re-verify reprojection need"


def test_mamba_shape_and_groups():
    rep = validate_mamba_npz()
    assert rep["n_seq"] == 666 and rep["n_events"] == 18
    d = np.load(MAMBA_NPZ, allow_pickle=False)
    assert d["X"].shape[1:] == (73, 15) and np.isfinite(d["X"]).all()


def test_mamba_csv_integrity_sample():
    from gs_common import check_mamba_csv_integrity
    rep = check_mamba_csv_integrity(max_seqs=20)
    assert rep["n_seq_checked"] == 20 and len(rep["feature_cols"]) == 15


def test_no_event_across_tabular_groups():
    groups = event_groups_rf(RF_ROWS)
    from sklearn.model_selection import StratifiedGroupKFold
    y = np.array([int(r["Landslide_Label"]) for r in RF_ROWS])
    for tri, tei in StratifiedGroupKFold(n_splits=3, shuffle=True,
                                         random_state=42).split(
            np.zeros(len(y)), y, groups):
        assert not set(np.array(groups)[tri]) & set(np.array(groups)[tei])


def test_mamba_event_window_isolation():
    sids = [str(s) for s in np.load(MAMBA_NPZ, allow_pickle=False)["sequence_ids"]]
    ev = [normalize_event_id(s.split("__")[-1].replace("LS_", "")) for s in sids]
    from sklearn.model_selection import GroupKFold
    y = np.load(MAMBA_NPZ, allow_pickle=False)["y"].astype(int)
    for tri, tei in GroupKFold(n_splits=3).split(np.zeros(len(y)), y, ev):
        assert not set(np.array(ev)[tri]) & set(np.array(ev)[tei])


def test_scaler_fits_train_only_convention():
    # pipeline invariant: no StandardScaler may be fit on a full matrix that
    # is later split — spot-check the worker + tabular code paths textually
    import pathlib
    worker = pathlib.Path(__file__).parent.parent.joinpath(
        "scripts", "gs_mamba_worker.py").read_text()
    assert "StandardScaler().fit(X[tri]" in worker
    pipe = pathlib.Path(__file__).parent.parent.joinpath(
        "scripts", "train_geosentinel.py").read_text()
    assert "fit_transform(all" not in pipe and "fit(X[tri]" in pipe or \
        "make_pipeline" in pipe


def test_model_artifacts_io_and_range():
    import joblib
    base = os.path.join(os.path.dirname(__file__), "..", "models")
    art = os.path.join(base, "rf", "gs_v1", "gs_rf.joblib")
    if not os.path.exists(art):
        pytest.skip("full pipeline not run yet")
    clf = joblib.load(art)
    rng = np.random.RandomState(0)
    X = rng.uniform(0, 1, size=(5, clf.n_features_in_))
    p = clf.predict_proba(X)[:, 1]
    assert p.shape == (5,) and ((p >= 0) & (p <= 1)).all()
    # deterministic inference
    assert np.allclose(p, clf.predict_proba(X)[:, 1])
    # checkpoint loading
    ckpt = os.path.join(base, "mamba", "gs_v1", "checkpoints", "fold0.pt")
    assert os.path.exists(ckpt)


def test_gis_outputs_crs_and_dims():
    base = os.path.join(os.path.dirname(__file__), "..", "models", "gs_gis")
    tif = os.path.join(base, "susceptibility_terrain.tif")
    gjp = os.path.join(base, "high_risk_points.geojson")
    if not (os.path.exists(tif) and os.path.exists(gjp)):
        pytest.skip("GIS stage not run yet")
    with open(tif, "rb") as fh:
        buf = fh.read()
    assert buf[:2] == b"II"  # little-endian TIFF
    import struct as _st
    import zlib as _zl
    _off = _st.unpack("<I", buf[4:8])[0]
    _n = _st.unpack("<H", buf[_off:_off + 2])[0]
    _tags = {}
    for _i in range(_n):
        _t, _ty, _c, _v = _st.unpack("<HHI4s", buf[_off + 2 + _i * 12:_off + 2 + _i * 12 + 12])
        _tags[_t] = _st.unpack("<I", _v)[0]
    assert _tags[259] == 8 and _tags[339] == 3  # deflate, float32
    _raw = _zl.decompress(buf[_tags[273]:_tags[273] + _tags[279]])
    _g = np.frombuffer(_raw, dtype="<f4").reshape(_tags[257], _tags[256])
    assert _g.shape[0] > 10 and (_g > -9999).sum() > 1000  # parses + has data
    gj = json.load(open(gjp, encoding="utf-8"))
    assert gj["crs"]["properties"]["name"] == "EPSG:4326"
    for f in gj["features"]:
        lon, lat = f["geometry"]["coordinates"]
        assert 89.9 <= lon <= 92.1 and 24.9 <= lat <= 27.1


def test_segformer_blocked():
    assert SEGFORMER_STATUS == "BLOCKED"
    gate = segformer_gate()
    assert gate["status"] == "BLOCKED"
    assert gate["checks"]["masks_present"] is False
    blocked = os.path.join(os.path.dirname(__file__), "..", "models",
                           "segformer", "BLOCKED.md")
    if os.path.exists(blocked):
        assert "BLOCKED" in open(blocked, encoding="utf-8").read()


def test_fusion_label_order_invariant():
    # Regression (2026-09-18): NPZ row order != CSV order; fusion must use
    # CSV-ordered labels, never NPZ-order (5.4% silent misalignment before).
    import csv as _csv
    import numpy as _np
    d = _np.load(MAMBA_NPZ, allow_pickle=False)
    npz_sids = [str(s) for s in d["sequence_ids"]]
    rows = list(_csv.DictReader(open(MAMBA_CSV, encoding="utf-8")))
    csv_sids = []
    for r in rows:
        if not csv_sids or csv_sids[-1] != r["Sequence_ID"]:
            csv_sids.append(r["Sequence_ID"])
    assert npz_sids != csv_sids, "invariant changed — recheck fusion label mapping"
    import inspect as _insp
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import train_geosentinel as _gs
    src = _insp.getsource(_gs.step_fusion)
    assert "mamba_y" in src and "y_all" not in src, \
        "fusion must take CSV-ordered labels, never NPZ-order"
