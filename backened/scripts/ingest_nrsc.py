"""NRSC Landslide Atlas boundary (SIH §2.3).

The Atlas (~80,000 events claimed, 1998–2022 — NOT assumed downloadable) has
no bulk machine-readable endpoint: inventory lives in the Bhuvan web-GIS
viewer + per-state PDFs. This script implements the honest boundary:

- data/manual/nrsc/ placeholder + schema contract for hand-extracted rows
- validates any placed CSVs (coords, NER, dates) into data/raw/nrsc_ner.json
- otherwise reports MANUAL_DOWNLOAD_REQUIRED with exact instructions

Official source: https://www.isro.gov.in (Landslide Atlas of India);
viewer: https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php?id=landslide
"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import (in_ner, valid_coords, classify_date, RAW_DIR,
                        MANUAL_DIR, write_json, utcnow, OFFICIAL_SOURCES)

MANUAL_GLOB = os.path.join(MANUAL_DIR, "nrsc", "*.csv")
REPORT = os.path.join(RAW_DIR, "nrsc_ingest_report.json")
PLACEHOLDER = os.path.join(MANUAL_DIR, "nrsc", "README.txt")


def _ensure_placeholder() -> None:
    if os.path.exists(PLACEHOLDER):
        return
    os.makedirs(os.path.dirname(PLACEHOLDER), exist_ok=True)
    with open(PLACEHOLDER, "w", encoding="utf-8") as f:
        f.write(
            "NRSC Landslide Atlas manual drop-box (no bulk API exists).\n"
            "Place hand-extracted official rows here as CSV with header:\n"
            "latitude,longitude,event_date,event_type,district,state,source_ref\n"
            "Atlas PDFs: https://www.isro.gov.in (Landslide Atlas of India).\n"
            "Counts are recorded as-imported; the ~80,000 figure is NEVER assumed.\n")


def main() -> dict:
    _ensure_placeholder()
    files = sorted(glob.glob(MANUAL_GLOB))
    if not files:
        rep = {"status": "MANUAL_DOWNLOAD_REQUIRED", "n": 0,
               "detail": "No NRSC CSVs in data/manual/nrsc/. See README.txt there. "
                         "Atlas has no bulk endpoint; actual imported count = 0.",
               "at": utcnow()}
        write_json(REPORT, rep)
        print(f"nrsc: {rep}")
        return rep
    recs, rejected = [], 0
    for p in files:
        with open(p, encoding="utf-8-sig") as f:
            for i, r in enumerate(csv.DictReader(f)):
                try:
                    lat, lon = float(r["latitude"]), float(r["longitude"])
                except (KeyError, TypeError, ValueError):
                    rejected += 1
                    continue
                if not valid_coords(lat, lon):
                    rejected += 1
                    continue
                dq, iso = classify_date(r.get("event_date"))
                recs.append({
                    "source": "nrsc", "source_event_id": f"nrsc-{os.path.basename(p)}-{i}",
                    "event_date": iso, "date_quality": dq,
                    "latitude": lat, "longitude": lon,
                    "district": r.get("district"), "state": r.get("state"),
                    "event_type": r.get("event_type"),
                    "source_url": OFFICIAL_SOURCES["nrsc"],
                    "in_ner": in_ner(lat, lon),
                    "data_quality": f"hand-extracted official Atlas rows: {os.path.basename(p)}",
                })
    write_json(os.path.join(RAW_DIR, "nrsc_ner.json"), recs)
    rep = {"status": "MANUAL_LOADED", "n": len(recs), "rejected": rejected,
           "n_ner": sum(1 for r in recs if r["in_ner"]), "at": utcnow()}
    write_json(REPORT, rep)
    print(f"nrsc: {rep}")
    return rep


if __name__ == "__main__":
    main()
