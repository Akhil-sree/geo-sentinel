"""Retraining pipeline gate (Phase 17): verified report -> candidate ->
dataset validation -> registry TRAINING entry -> manual approval ->
production promotion. NEVER field-report -> auto-deploy.

Usage:
  python scripts/promote_reports.py --list        # show USED_FOR_TRAINING reports
  python scripts/promote_reports.py --export      # validate + write candidates JSON
  python scripts/promote_reports.py --approve     # human approval: mark registry entry
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models_db import CitizenReport

CANDIDATES_PATH = os.path.join(os.path.dirname(__file__), "..", "models",
                               "training_candidates.json")


def candidates(db):
    rows = db.query(CitizenReport).filter(
        CitizenReport.status == "USED_FOR_TRAINING").all()
    out, problems = [], []
    for r in rows:
        if r.latitude is None or not (-90 <= r.latitude <= 90
                                      and -180 <= r.longitude <= 180):
            problems.append(f"{r.id}: bad GPS")
            continue
        if not r.landslide_type:
            problems.append(f"{r.id}: missing category")
            continue
        out.append({"report_id": r.id, "lat": r.latitude, "lng": r.longitude,
                    "type": r.landslide_type,
                    "severity_observed": r.severity_observed,
                    "photo": bool(r.photo_url),
                    "client_timestamp": (r.client_timestamp.isoformat()
                                         if r.client_timestamp else None)})
    return out, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--approve", action="store_true")
    a = ap.parse_args()
    db = SessionLocal()
    try:
        out, problems = candidates(db)
    finally:
        db.close()
    if a.list or (not a.export and not a.approve):
        print(json.dumps({"candidates": out, "problems": problems}, indent=2))
    if a.export:
        os.makedirs(os.path.dirname(CANDIDATES_PATH), exist_ok=True)
        json.dump({"candidates": out, "problems": problems,
                   "note": "human approval required before training"},
                  open(CANDIDATES_PATH, "w"), indent=2)
        print(f"exported {len(out)} candidates "
              f"({len(problems)} problems) -> {CANDIDATES_PATH}")
    if a.approve:
        from app.ml import registry
        e = registry.register(
            model_id="retrain-request", version="pending-review-v1",
            dataset_version="events_v2+field-candidates",
            feature_version="terrain6_v1", algorithm="TBD-by-reviewer",
            parameters={}, metrics={"n_candidates": len(out)},
            validation_method="spatial GroupKFold required before promotion",
            status="TRAINING")
        print(f"approval recorded: {e['model_id']} {e['version']} "
              f"status={e['status']} — still NOT production")


if __name__ == "__main__":
    main()
