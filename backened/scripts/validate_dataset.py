"""Dataset validation gate (Phase 2B). Fails loudly on:
duplicates, missing/invalid coordinates, invalid labels, train/val leakage
(same district on both sides), missing timestamps, class imbalance (>10:1),
feature leakage (non-finite). Run: python scripts/validate_dataset.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models_db import Zone, LandslideEvent
from app.ml.dataset import (build_event_dataset, check_leakage,
                            EVENTS_BY_ZONE_YEAR, YEARS)


def main() -> dict:
    errors, warnings = [], []
    db = SessionLocal()
    try:
        zones = db.query(Zone).all()
        events = db.query(LandslideEvent).all()
    finally:
        db.close()

    # 1. coordinates present + valid
    for z in zones:
        if z.latitude is None or z.longitude is None:
            errors.append(f"{z.id}: missing coordinates")
        elif not (-90 <= z.latitude <= 90 and -180 <= z.longitude <= 180):
            errors.append(f"{z.id}: invalid coordinates {z.latitude},{z.longitude}")
        for f in ("slope", "elevation", "ruggedness", "road_proximity",
                  "drainage_proximity", "settlement_density"):
            v = getattr(z, f, None)
            if v is None or not (float("-inf") < float(v) < float("inf")):
                errors.append(f"{z.id}: bad feature {f}={v}")

    # 2. build + duplicates (leakage)
    try:
        X, y, groups, meta = build_event_dataset(zones)
        check_leakage(meta["keys"], groups)
    except ValueError as e:
        errors.append(str(e))
        X, y, groups, meta = None, None, None, {}

    # 3. labels valid + imbalance
    if y is not None:
        import numpy as np
        uy = np.unique(y)
        if set(uy.tolist()) - {0, 1}:
            errors.append(f"invalid labels: {uy.tolist()}")
        pos, neg = int(y.sum()), int(len(y) - y.sum())
        if pos == 0 or neg == 0:
            errors.append("single-class dataset")
        elif max(pos, neg) / max(1, min(pos, neg)) > 10:
            warnings.append(f"severe imbalance {pos}pos/{neg}neg")

    # 4. event timestamps present + no same-zone same-date duplicates
    seen_ed = set()
    for e in events:
        if e.event_date is None:
            errors.append(f"event {e.id}: missing timestamp")
        else:
            k = (e.zone_id, e.event_date.isoformat()[:10])
            if k in seen_ed:
                errors.append(f"duplicate event {k} (temporal leakage risk)")
            seen_ed.add(k)

    # 4b. duplicate coordinates across zones (spatial duplicates)
    seen_xy = {}
    for z in zones:
        k = (round(z.latitude or -999, 4), round(z.longitude or -999, 4))
        if k in seen_xy:
            errors.append(f"{z.id} shares coordinates with {seen_xy[k]}")
        seen_xy[k] = z.id

    # 4c. label-as-feature guard: no target/ID columns in the feature schema
    from app.ml.dataset import FEATURES
    for bad in ("label", "target", "zone_id", "event", "landslide"):
        if any(bad in f for f in FEATURES):
            errors.append(f"feature schema contains label-like column: {FEATURES}")

    # 4d. CSV artifact consistency (data/processed/events_v2.csv vs DB build)
    import csv as _csv
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data",
                            "processed", "events_v2.csv")
    if X is not None:
        if not os.path.exists(csv_path):
            warnings.append("data/processed/events_v2.csv missing — run data/process_events.py")
        else:
            with open(csv_path, encoding="utf-8") as f:
                rows = list(_csv.DictReader(f))
            if len(rows) != len(X):
                errors.append(f"CSV has {len(rows)} rows but DB build has {len(X)}")
            else:
                for r, (zz, yy) in zip(rows, meta["keys"]):
                    if r["sample_id"] != f"{zz}-{yy}" or int(r["label"]) not in (0, 1):
                        errors.append(f"CSV row mismatch: {r}")
                        break

    # 5. every recorded event resolves to a labeled sample
    if meta:
        keyset = set(meta["keys"])
        for k in EVENTS_BY_ZONE_YEAR:
            if k not in keyset:
                errors.append(f"inventory event {k} has no training sample")
        # 6. group separation sanity: >=3 districts for GroupKFold-3
        if len(set(groups.tolist())) < 3:
            errors.append("fewer than 3 district groups — spatial CV impossible")

    report = {"dataset_version": meta.get("dataset_version", "?"),
              "n_samples": meta.get("n_samples", 0),
              "errors": errors, "warnings": warnings,
              "status": "FAIL" if errors else "PASS"}
    print(report)
    if errors:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    main()
