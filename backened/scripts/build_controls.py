"""Matched control (negative) sampler (SIH §8).

For each TEMPORAL event: same location, same month-day, non-event years
(±1..3y, excluding any year with a TEMPORAL event within 30d at that site).
Controls represent NO_RECORDED_LANDSLIDE (absence of record, never proven
absence). Deterministic, no random negatives, no positive inflation.
"""
import sys
from datetime import datetime, timedelta

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models_db import NerInventory, TrainingSample


def _event_days(db) -> set:
    return {(e.latitude, e.longitude,
             e.event_date.date().isoformat()) for e in
            db.query(NerInventory).filter(NerInventory.record_kind == "TEMPORAL").all()}


def main(n_per_event: int = 2) -> dict:
    import os
    n_per_event = int(next((a.split("=", 1)[1] for a in sys.argv
                            if a.startswith("--n=")), n_per_event))
    db = SessionLocal()
    try:
        events = db.query(NerInventory).filter(NerInventory.record_kind == "TEMPORAL").all()
        event_days = _event_days(db)
        made, skipped = 0, 0
        for e in events:
            base = e.event_date.date()
            for k in range(1, n_per_event + 1):
                for year in (base.year - k, base.year + k):
                    try:
                        cand = base.replace(year=year)
                    except ValueError:
                        continue
                    if cand > datetime.now().date() - timedelta(days=2):
                        continue  # needs complete archive history
                    if any(abs((cand - datetime.fromisoformat(d).date()).days) <= 30
                           for (la, lo, d) in event_days
                           if abs(la - e.latitude) < 0.05 and abs(lo - e.longitude) < 0.05):
                        skipped += 1
                        continue
                    sid = f"CTL-{e.id}-{cand.isoformat()}"
                    if db.query(TrainingSample).filter(TrainingSample.sample_id == sid).first():
                        continue
                    db.add(TrainingSample(
                        dataset_version="__pending__", sample_id=sid, event_id=None,
                        label="NO_RECORDED_LANDSLIDE",
                        event_date=datetime.combine(cand, datetime.min.time()),
                        latitude=e.latitude, longitude=e.longitude,
                        features_json="{}",
                        provenance_json=(f'{{"control_of": {e.id}, "strategy": "matched-spatiotemporal '
                                          f'(same site, same month-day, non-event year)}}'),
                        group_id=(e.district or e.state or "NER")))
                    made += 1
                    break
        db.commit()
        return {"events": len(events), "controls_made": made, "skipped": skipped}
    finally:
        db.close()


if __name__ == "__main__":
    print(f"controls: {main()}")
