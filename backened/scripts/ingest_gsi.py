"""GSI inventory → ner_inventory loader (SIH §2.2).

Machine-readable path: the bharatlas CC0-1.0 parquet mirror already vendored
(data/raw/gsi_meghalaya.parquet via data/process_gsi.py). Bhukosh itself is
registration-gated (no public API — never bypassed); manually downloaded
official files placed in data/manual/gsi/ are validated and preferred.
INITIATION year 0 = unknown → SPATIAL; year-known → YEAR_ONLY (spatial-only
too: only EXACT_DATE enters temporal training, SIH §6).

Official source: https://bhukosh.gsi.gov.in/Bhukosh/Public
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import (in_ner, RAW_DIR, MANUAL_DIR, write_json, utcnow,
                        OFFICIAL_SOURCES)

PARQUET = os.path.join(RAW_DIR, "gsi_meghalaya.parquet")
REPORT = os.path.join(RAW_DIR, "gsi_ingest_report.json")


def _records_from_parquet(path: str, tag: str) -> list[dict]:
    import pandas as pd
    df = pd.read_parquet(path)
    out = []
    for _, r in df.iterrows():
        try:
            lat, lon = float(r["LATITUDE"]), float(r["LONGITUDE"])
        except (KeyError, TypeError, ValueError):
            continue
        init = r.get("INITIATION", 0)
        try:
            year = int(init)
        except (TypeError, ValueError):
            year = 0
        out.append({
            "source": "gsi", "source_event_id": f"gsi-{tag}-{r.get('OBJECTID', '?')}",
            "event_date": None,
            "date_quality": "YEAR_ONLY" if year > 0 else "UNKNOWN",
            "date_year": year or None,
            "latitude": lat, "longitude": lon,
            "district": str(r.get("DISTRICT", "")),
            "state": "Meghalaya",
            "event_type": None, "severity": None,
            "confidence": "catalogued",
            "trigger": str(r.get("TRIGGERING", "")),
            "activity": str(r.get("ACTIVITY", "")),
            "source_url": OFFICIAL_SOURCES["gsi"],
            "in_ner": in_ner(lat, lon),
            "data_quality": f"GSI catalog via bharatlas CC0 mirror ({tag}); year-or-unknown resolution",
        })
    return out


def main() -> dict:
    manual = sorted(glob.glob(os.path.join(MANUAL_DIR, "gsi", "*.parquet")))
    recs, origin = [], "none"
    if manual:
        for p in manual:
            recs.extend(_records_from_parquet(p, "manual-official"))
        origin = f"manual-official ({len(manual)} files)"
    if os.path.exists(PARQUET):
        recs.extend(_records_from_parquet(PARQUET, "bharatlas-mirror"))
        origin += "+bharatlas-mirror" if origin != "none" else "bharatlas-mirror"
    if not recs:
        rep = {"status": "MANUAL_DOWNLOAD_REQUIRED",
               "detail": "No GSI parquet found. Run data/process_gsi.py with the vendored mirror, "
                         "or place official Bhukosh downloads in data/manual/gsi/ "
                         "(registration required at https://bhukosh.gsi.gov.in/Bhukosh/Public)."}
    else:
        write_json(os.path.join(RAW_DIR, "gsi_ner.json"), recs)
        rep = {"status": "DOWNLOADED" if origin == "bharatlas-mirror" else "MANUAL_LOADED",
               "origin": origin, "n": len(recs),
               "n_ner": sum(1 for r in recs if r["in_ner"]),
               "n_year_known": sum(1 for r in recs if r["date_quality"] == "YEAR_ONLY"),
               "boundary": "year-or-unknown → SPATIAL ONLY, never temporal labels",
               "at": utcnow()}
    write_json(REPORT, rep)
    print(f"gsi: {rep}")
    return rep


if __name__ == "__main__":
    main()
