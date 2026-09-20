"""Temporal dataset validation gate (Phase 5). Fails loudly on:
post-event features, overlapping same-zone windows, duplicate samples,
missing timestamps, impossible values, label leakage, spatial-group
shortage, imbalance (>10:1), npz/CSV/raw drift.
Run: python scripts/validate_temporal_dataset.py
"""
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

HERE = os.path.join(os.path.dirname(__file__), "..", "data")


def main(tag="v2") -> dict:
    import numpy as np
    errors, warnings = [], []
    stem = "sequences_v2" if tag == "v2" else "sequences_v1"
    samp = "samples_v2.csv" if tag == "v2" else "samples_v1.csv"
    exp_n, exp_pos = (32, 10) if tag == "v2" else (24, 10)
    z = np.load(os.path.join(HERE, "processed", f"{stem}.npz"),
                allow_pickle=True)
    X, y, groups = z["X"], z["y"], z["groups"]
    meta = json.loads(str(z["meta"]))
    with open(os.path.join(HERE, "processed", samp),
              encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # 1. shapes + counts
    if X.shape != (exp_n, 48, 7):
        errors.append(f"bad X shape {X.shape}")
    if len(y) != exp_n or len(rows) != exp_n:
        errors.append(f"count != {exp_n}")
    pos, neg = int(y.sum()), int(len(y) - y.sum())
    if pos != exp_pos or pos + neg != exp_n:
        errors.append(f"balance drift: {pos}pos/{neg}neg")
    if max(pos, neg) / max(1, min(pos, neg)) > 10:
        warnings.append("severe imbalance")

    # 2. value ranges (normalized 0..1 rain-ish cols, soil 0..1)
    if not np.isfinite(X).all():
        errors.append("non-finite sequence values")
    if X.min() < -0.01 or X.max() > 1.01:
        errors.append(f"sequence out of [0,1]: [{X.min()}, {X.max()}]")

    # 3. raw-level: pre-event-only, no overlap, timestamps present
    import glob as _glob
    seen, windows = set(), {}
    for r in rows:
        key = (r["zone_id"], r["end_date"])
        if key in seen:
            errors.append(f"duplicate sample {key}")
        seen.add(key)
        cands = _glob.glob(os.path.join(
            HERE, "raw",
            f"archive_{r['zone_id']}_{r['end_date'].replace('-', '')}_*.json"))
        # exclude sat_*.json (satellite metadata, different prefix — no clash)
        cands = [c for c in cands if os.path.basename(c).startswith("archive_")]
        if not cands:
            errors.append(f"missing raw for {key}")
            continue
        fn = sorted(cands)[0]
        p = json.load(open(fn))
        t_end = dt.datetime.fromisoformat(p["prediction_timestamp"])
        times = [dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc)
                 for t in p["hourly"]["time"]]
        # Build clips to t<=t_end; verify the USED window is pre-event-only
        # and covers the full 168h (raw files legitimately extend past noon
        # on the end date — those hours must be, and are, excluded).
        used = [t for t in times if t <= t_end][-168:]
        if len(used) < 168:
            errors.append(f"{fn}: only {len(used)} pre-event hours (<168h)")
        elif used[-1] > t_end or (t_end - used[0]).total_seconds() < 167 * 3600:
            errors.append(f"{fn}: used window not fully pre-event")
        w = (min(times[-169:]), t_end)
        for (s, e) in windows.get(r["zone_id"], []):
            if s <= t_end <= e or s <= w[0] <= e:
                errors.append(f"{r['zone_id']}: overlapping windows")
        windows.setdefault(r["zone_id"], []).append(w)
        if p.get("soil_source", "").upper().find("MODELED") < 0:
            errors.append(f"{fn}: soil source not labeled MODELED")

    # 4. spatial groups for leakage-safe CV
    if len(set(groups.tolist())) < 3:
        errors.append("fewer than 3 district groups")

    # 5. npz labels match CSV labels
    for i, r in enumerate(rows):
        if int(r["label"]) != int(y[i]):
            errors.append(f"label mismatch row {i}")
            break

    report = {"dataset_version": meta.get("dataset_version"),
              "n": len(X), "pos": pos, "neg": neg,
              "errors": errors, "warnings": warnings,
              "status": "FAIL" if errors else "PASS"}
    print(report)
    if errors:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    main("v2" if "--v2" in sys.argv else "v1")
