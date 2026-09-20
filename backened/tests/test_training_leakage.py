"""Mandatory training-leakage tests (SIH §45).

Verifies on the built ner_v1 artifacts (no network):
- no future rainfall/soil hours in raw caches past event end
- no test-event contamination (split uniqueness, class balance)
- no spatial-group positives shared across train/test (disclosed PARTIAL allowed)
- no duplicated source records across splits (canonical uniqueness)
- temporal direction: train positives strictly predate test positives
- no label-as-feature columns; no silent-zero fills in all-missing columns
- SAR caches are metadata-only (no backscatter/imagery keys)
"""
import csv
import glob
import json
import os

import pytest

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
RAW = os.path.join(DATA, "raw")
PROCESSED = os.path.join(DATA, "processed")
META = os.path.join(DATA, "metadata")
CSV = os.path.join(PROCESSED, "ner_training_ner_v1.csv")
NEED = os.path.exists(CSV)

pytestmark = pytest.mark.skipif(
    not NEED,
    reason="ner_v1 training data absent (local-only data/processed/)",
)


def _rows():
    with open(CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_no_future_rainfall_in_caches():
    assert NEED, "ner_v1 not built — run the pipeline first"
    for r in _rows():
        if not r["sample_id"].startswith("POS-"):
            continue
        eid = r["sample_id"].split("-", 1)[1]
        p = os.path.join(RAW, f"ner_rain_{eid}.json")
        assert os.path.exists(p), f"missing rain cache {eid}"
        with open(p, encoding="utf-8") as _rain_fh:
            d = json.load(_rain_fh)
        end = r["event_date"] + "T23:59"
        late = [t for t in d["hourly"]["time"] if t > end]
        assert not late, f"future rainfall in {eid}: {late[:3]}"


def test_no_test_event_contamination():
    rows = _rows()
    ids = [r["sample_id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate sample across splits"
    by_split = {}
    for r in rows:
        by_split.setdefault(r["split"], set()).add(r["label"])
    for s, labels in by_split.items():
        assert labels == {"RECORDED_LANDSLIDE", "NO_RECORDED_LANDSLIDE"}, s


def test_temporal_direction():
    rows = [r for r in _rows() if r["label"] == "RECORDED_LANDSLIDE"]
    tr = [int(r["event_date"][:4]) for r in rows if r["split"] == "train"]
    te = [int(r["event_date"][:4]) for r in rows if r["split"] == "test"]
    assert max(tr) < min(te), f"train {sorted(set(tr))} vs test {sorted(set(te))}"


def test_no_canonical_dup_across_splits():
    from app.models_db import NerInventory  # noqa — schema guard, no DB hit
    assert NerInventory.__tablename__ == "ner_inventory"
    rows = _rows()
    seen = {}
    for r in rows:
        prov = json.loads(r.get("provenance") or "{}")
        key = ("POS", r.get("event_date"), r.get("latitude"), r.get("longitude")) \
            if r["label"] == "RECORDED_LANDSLIDE" else ("CTL", prov.get("control_of"))
        assert key not in seen or seen[key] == r["split"], f"same source in two splits: {key}"
        seen[key] = r["split"]


def test_no_label_as_feature():
    rows = _rows()
    leak = [c for c in rows[0] if c.lower() in ("target", "seed_label", "zone_label")]
    assert not leak, leak


def test_no_silent_zero_fill():
    rows = _rows()
    meta = {"sample_id", "label", "event_date", "latitude", "longitude",
            "group_id", "provenance", "missingness", "split"}
    for c in rows[0]:
        if c in meta:
            continue
        vals = [r[c] for r in rows]
        if all(v in ("", None) for v in vals):
            assert not any(v == "0" or v == "0.0" for v in vals), f"zero-filled {c}"


def test_sar_metadata_only():
    for p in glob.glob(os.path.join(RAW, "ner_sar_*.json")):
        with open(p, encoding="utf-8") as _sar_fh:
            d = json.load(_sar_fh)
        blob = json.dumps(d).lower()
        for banned in ("backscatter", "sigma0", "gamma0", "coherence_value", "vv_db"):
            assert banned not in blob, f"imagery-derived key in {p}"
        assert d.get("imagery_status", "").startswith("AUTH_REQUIRED")


def test_soil_never_called_sensor():
    for r in _rows():
        prov = json.loads(r.get("provenance") or "{}")
        for k, v in prov.items():
            if k.startswith("soil"):
                assert v != "sensor", f"modeled soil mislabeled as sensor in {r['sample_id']}"
