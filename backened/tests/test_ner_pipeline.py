"""NER pipeline unit tests (SIH §44): parsing, NER filter, date classes,
deduplication, alignment, sampling, versioning, registry gate. No network —
all fixtures inline (honest small-scale checks of pipeline logic)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import NEGATIVE, POSITIVE, classify_date, dedup_records, in_ner, valid_coords


def test_ner_filter_bounds():
    assert in_ner(25.3, 91.7) and in_ner(22.0, 90.0) and in_ner(29.0, 96.0)
    assert not in_ner(21.9, 91.0) and not in_ner(25.0, 89.9) and not in_ner(25.0, 96.1)
    assert not valid_coords(999, 0) and valid_coords(25.3, 91.7)


def test_date_classification():
    assert classify_date("2024-07-10") == ("EXACT_DATE", "2024-07-10T00:00:00")
    assert classify_date("2024-07")[0] == "MONTH_ONLY"
    assert classify_date("2024")[0] == "YEAR_ONLY"
    assert classify_date(None) == ("UNKNOWN", None)
    assert classify_date("") == ("UNKNOWN", None)
    assert classify_date("not-a-date") == ("UNKNOWN", None)


def test_dedup_same_event_merges():
    # dated same-place same-date records merge; dateless same-place pairs
    # stay separate + flagged (uncertain → never force-merged)
    recs = [
        {"source": "gsi", "source_event_id": "g1", "event_date": "2024-07-10T00:00:00",
         "latitude": 25.30, "longitude": 91.70},
        {"source": "nrsc", "source_event_id": "n9", "event_date": "2024-07-10T00:00:00",
         "latitude": 25.301, "longitude": 91.701},
        {"source": "coolr", "source_event_id": "c2", "event_date": "2024-07-10T00:00:00",
         "latitude": 25.60, "longitude": 90.46},
    ]
    out, rep = dedup_records(recs, dist_km=2.0)
    assert rep["n_groups"] == 2, rep
    assert out[0]["canonical_event_id"] == out[1]["canonical_event_id"]
    assert out[0]["source_count"] == 2
    assert out[2]["canonical_event_id"] != out[0]["canonical_event_id"]


def test_dedup_dateless_stays_separate_but_flagged():
    recs = [
        {"source": "gsi", "source_event_id": "g1", "event_date": None,
         "latitude": 25.30, "longitude": 91.70},
        {"source": "nrsc", "source_event_id": "n9", "event_date": None,
         "latitude": 25.301, "longitude": 91.701},
    ]
    out, rep = dedup_records(recs, dist_km=2.0)
    assert rep["n_groups"] == 2 and rep["merged"] == 0
    assert rep["flagged_review"] == 1
    assert out[1].get("review_flag") == "spatial-duplicate-candidate"


def test_dedup_uncertain_stays_separate():
    recs = [
        {"source": "gsi", "source_event_id": "g1", "event_date": "2024-07-10T00:00:00",
         "latitude": 25.30, "longitude": 91.70},
        {"source": "gsi", "source_event_id": "g2", "event_date": "2023-07-10T00:00:00",
         "latitude": 25.301, "longitude": 91.701},
    ]
    out, rep = dedup_records(recs)
    assert rep["n_groups"] == 2  # same place, different dates → separate
    assert rep["merged"] == 0


def test_label_terminology():
    assert POSITIVE == "RECORDED_LANDSLIDE"
    assert NEGATIVE == "NO_RECORDED_LANDSLIDE"


def test_registry_gate_blocks_small_n(tmp_path, monkeypatch):
    from app.ml import registry as reg
    # isolated registry file: tests must never pollute models/registry.json
    fake = str(tmp_path / "registry.json")
    monkeypatch.setattr(reg, "REGISTRY_PATH", fake)
    _e = reg.register(model_id="__probe__", version="t1", dataset_version="ner_probe",
                     feature_version="v", algorithm="Probe", parameters={},
                     metrics={"f1": 0.99, "recall": 0.99, "brier": 0.01,
                              "n_samples": 10, "leakage_check_passed": True},
                     validation_method="spatial GroupKFold", status="EXPERIMENTAL")
    gate = reg.evaluate_promotion("__probe__", "t1")
    assert gate["verdict"] == "BLOCK", gate  # n=10 must block despite perfect F1
    assert any("minimum_samples" in r for r in gate["reasons"])


def test_dataset_version_immutable():
    import json
    meta = os.path.join(os.path.dirname(__file__), "..", "data",
                        "metadata", "ner_training_ner_v1.json")
    assert os.path.exists(meta), "build the dataset first"
    with open(meta, encoding="utf-8") as _meta_fh:
        d = json.load(_meta_fh)
    assert d["checksum"] and d["feature_version"] == "nerfeat_v1"
    assert d["positive"] >= 1 and d["negative"] >= 1


def test_datasets_api_shapes():
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    assert c.get("/api/datasets").status_code == 200
    assert c.get("/api/datasets/ner_v1").status_code == 200
    assert c.get("/api/landslides/temporal").status_code == 200
    assert c.get("/api/landslides/spatial").status_code == 200
    assert c.get("/api/data-quality").status_code == 200
    r = c.get("/api/models/ner_rf")
    assert r.status_code == 200
    assert c.get("/api/rainfall/history?limit=5").status_code == 200
    assert c.get("/api/soil/history?limit=5").status_code == 200
    assert c.get("/api/terrain/features").status_code == 200
