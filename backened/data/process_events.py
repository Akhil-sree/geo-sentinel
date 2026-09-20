"""Reproducible preprocessing pipeline (Phase 2):

    seed inventory (app/seed.py EVENTS + ZONES)
        v
    validation (coordinates, dates, zone ids)
        v
    spatial normalization (zone centroids WGS84, district groups)
        v
    temporal normalization (zone-year grid 2022-2024)
        v
    feature generation (static terrain, SAR excluded — leakage note)
        v
    label generation (1 if >=1 event in zone-year)
        v
    leakage checks (duplicates, district-group separation)
        v
    data/processed/events_v2.csv + data/metadata/events_v2.json

Run: python data/process_events.py. Deterministic. No external data.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import ZONES, EVENTS  # noqa: E402
from app.ml.dataset import (DATASET_VERSION, FEATURE_VERSION, FEATURES,  # noqa: E402
                            YEARS, EVENTS_BY_ZONE_YEAR)

HERE = os.path.dirname(__file__)


def main():
    zones = {z["id"]: z for z in ZONES}
    problems = []
    for zid, d, _t in EVENTS:
        if zid not in zones:
            problems.append(f"event zone {zid} not in ZONES")
        try:
            y, m, dd = map(int, d.split("-"))
            assert 2000 <= y <= 2030 and 1 <= m <= 12 and 1 <= dd <= 31
        except Exception:
            problems.append(f"bad date {d}")
    for z in ZONES:
        if not (-90 <= z["lat"] <= 90 and -180 <= z["lng"] <= 180):
            problems.append(f"{z['id']}: bad coords")
    if problems:
        raise SystemExit(f"validation failed: {problems}")

    rows = []
    for zid in sorted(zones):
        z = zones[zid]
        for yr in YEARS:
            rows.append({
                "sample_id": f"{zid}-{yr}", "zone_id": zid, "year": yr,
                "district": z["district"], "lat": z["lat"], "lng": z["lng"],
                "slope": z["slope"],
                "elevation_norm": round(min(1.0, z["elevation"] / 2000.0), 4),
                "ruggedness": z["ruggedness"],
                "road_proximity": z["road_proximity"],
                "drainage_proximity": z["drainage_proximity"],
                "settlement_density": z["settlement_density"],
                "label": 1 if (zid, yr) in EVENTS_BY_ZONE_YEAR else 0,
            })
    keys = [(r["zone_id"], r["year"]) for r in rows]
    assert len(set(keys)) == len(keys), "duplicate (zone,year)"
    assert len({z["district"] for z in ZONES}) >= 3, "need >=3 district groups"

    out_csv = os.path.join(HERE, "processed", "events_v2.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    meta = {
        "dataset_version": DATASET_VERSION, "feature_version": FEATURE_VERSION,
        "features": FEATURES, "n_samples": len(rows),
        "n_positive": sum(r["label"] for r in rows),
        "source_name": "GEO-SENTINEL seed demo inventory",
        "source_url": "n/a (in-repo app/seed.py EVENTS, 10 events 2022-2024)",
        "license": "demo synthetic — not for operational use",
        "collection_date": "2026-07 (seed v1)",
        "spatial_resolution": "zone-level (8 Meghalaya zones)",
        "temporal_resolution": "zone-year (2022-2024)",
        "preprocessing": "this script; static terrain only, SAR excluded (mock-leakage)",
        "label_definition": "1 if >=1 recorded event in zone-year else 0",
        "geographic_coverage": "Meghalaya, India (8 zones, 6 districts)",
        "leakage_checks": "duplicate (zone,year): pass; district groups>=3: pass",
    }
    out_json = os.path.join(HERE, "metadata", "events_v2.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"wrote {out_csv} ({len(rows)} rows) + {out_json}")
    return meta


if __name__ == "__main__":
    main()
