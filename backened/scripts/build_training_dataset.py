"""Assemble versioned NER training dataset (SIH PHASE 13-15 → §20/§24).

python scripts/build_training_dataset.py --region NER --version ner_v1

Reads training_samples (features built), imputes defensible numeric gaps
(group-median, recorded in missingness), assigns leakage-safe splits
(temporal holdout = most recent event year → test; remaining → train/val by
district group), writes data/processed/ner_training_v1.csv + metadata +
dataset_versions ledger row (immutable — reruns bump version suffix).
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import PROCESSED_DIR, META_DIR, write_json, utcnow, dataset_checksum

VERSION = "ner_v1"
FEATURE_VERSION = "nerfeat_v1"
CODE_VERSION = "ner-pipeline-1.0"


def _median(vals):
    vals = sorted(vals)
    return vals[len(vals) // 2] if vals else 0.0


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="NER")
    ap.add_argument("--version", default=VERSION)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    from app.database import SessionLocal
    from app.models_db import TrainingSample, DatasetVersion
    db = SessionLocal()
    try:
        rows = db.query(TrainingSample).all()
        rows = [r for r in rows if r.features_json and r.features_json != "{}"]
        if not rows:
            return {"status": "BLOCKED", "reason": "no built feature rows — run build_features.py first"}
        feat_keys, groups = [], {}
        parsed = []
        for r in rows:
            f = json.loads(r.features_json)
            miss = json.loads(r.missingness_json or "{}")
            parsed.append((r, f, miss))
            for k in f:
                if k not in feat_keys:
                    feat_keys.append(k)
        num_keys = [k for k in feat_keys if any(isinstance(f.get(k), (int, float)) for _, f, _ in parsed)]
        for _, f, _ in parsed:
            for k in num_keys:
                groups.setdefault(k, []).append(f[k])
        medians = {k: _median([v for v in vs if isinstance(v, (int, float))]) for k, vs in groups.items()}
        # Leakage-safe splits: temporal holdout = most recent POSITIVE year.
        # Test = those positives + controls linked to them (matched structure
        # stays intact; no positive site spans train/test). Val = a district
        # with no test positives; train = rest. Controls never leak positives
        # across splits because they follow their linked event.
        pos_years = sorted({r.event_date.year for r, _, _ in parsed
                            if r.event_date and r.label == "RECORDED_LANDSLIDE"})
        holdout_year = pos_years[-1] if pos_years else None
        test_pos_ids = {r.event_id for r, _, _ in parsed
                        if r.label == "RECORDED_LANDSLIDE" and r.event_date
                        and r.event_date.year == holdout_year}
        test_groups = {r.group_id for r, _, _ in parsed
                       if r.label == "RECORDED_LANDSLIDE" and r.event_date
                       and r.event_date.year == holdout_year}
        val_candidates = sorted({r.group_id or "NER" for r, _, _ in parsed}
                                - set(test_groups))
        val_district = val_candidates[len(val_candidates) // 2] if val_candidates else None
        out_rows, counts = [], {"train": 0, "val": 0, "test": 0}
        for r, f, miss in parsed:
            row = {"sample_id": r.sample_id, "label": r.label,
                   "event_date": r.event_date.date().isoformat() if r.event_date else "",
                   "latitude": r.latitude, "longitude": r.longitude,
                   "group_id": r.group_id or "NER",
                   "provenance": r.provenance_json or "",
                   "missingness": r.missingness_json or ""}
            for k in feat_keys:
                v = f.get(k)
                if v is None and k in medians:
                    v = medians[k]
                    miss[k] = miss.get(k, "NOT_AVAILABLE") + "+median-imputed"
                row[k] = v
            row["missingness"] = json.dumps(miss)
            if r.label == "RECORDED_LANDSLIDE":
                split = ("test" if r.event_date and r.event_date.year == holdout_year
                         else ("val" if r.group_id == val_district else "train"))
            else:
                linked = json.loads(r.provenance_json or "{}").get("control_of")
                split = ("test" if str(linked) in {str(x) for x in test_pos_ids}
                         else ("val" if r.group_id == val_district else "train"))
            row["split"] = split
            counts[split] += 1
            r.split = split
            r.dataset_version = args.version
            out_rows.append(row)
        csv_path = os.path.join(PROCESSED_DIR, f"ner_training_{args.version}.csv")
        if os.path.exists(csv_path) and not args.force:
            return {"status": "BLOCKED",
                    "reason": f"{csv_path} exists — rerun with --force or bump --version (never overwrite silently)"}
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        meta = {"version": args.version, "region": args.region,
                "feature_version": FEATURE_VERSION, "code_version": CODE_VERSION,
                "n": len(out_rows),
                "positive": sum(1 for r in out_rows if r["label"] == "RECORDED_LANDSLIDE"),
                "negative": sum(1 for r in out_rows if r["label"] == "NO_RECORDED_LANDSLIDE"),
                "splits": counts, "holdout_year": holdout_year,
                "val_district": val_district,
                "groups": sorted({r.group_id or "NER" for r, _, _ in parsed}),
                "features": feat_keys, "imputation": "group-median (recorded per-cell)",
                "checksum": dataset_checksum(csv_path), "created_at": utcnow()}
        write_json(os.path.join(META_DIR, f"ner_training_{args.version}.json"), meta)
        if not db.query(DatasetVersion).filter(DatasetVersion.version == args.version).first():
            db.add(DatasetVersion(version=args.version, region=args.region,
                                  sources_json=json.dumps({"inventory": "ner_inventory",
                                                           "rain": "openmeteo-archive",
                                                           "soil": "modeled-era5-land+smap-boundary",
                                                           "dem": "srtm30m", "sar": "asf-metadata",
                                                           "roads": "osm-overpass"}),
                                  counts_json=json.dumps(meta),
                                  feature_version=FEATURE_VERSION,
                                  code_version=CODE_VERSION,
                                  checksum=meta["checksum"], status="DRAFT"))
        elif args.force:
            # explicit --force rebuild: ledger follows the artifact openly
            # (immutability holds across version names, not against --force)
            row = db.query(DatasetVersion).filter(
                DatasetVersion.version == args.version).first()
            row.counts_json = json.dumps(meta)
            row.checksum = meta["checksum"]
            row.status = "DRAFT (rebuilt --force)"
        db.commit()
        print(f"dataset: {args.version} n={len(out_rows)} splits={counts}")
        return {"status": "BUILT", **meta}
    finally:
        db.close()


if __name__ == "__main__":
    print(main())
