"""SMAP soil-moisture boundary (SIH §11).

NASA Earthdata SMAP L3 requires authentication (EARTHDATA_USERNAME /
EARTHDATA_PASSWORD); no credentials are ever hardcoded or logged. States:
CONFIGURED (creds present — retrieval still manual-gated per granule),
AUTH_REQUIRED (no creds), MANUAL_LOADED (--manual PATH with official
HDF/CSV rows), UNAVAILABLE. Missing soil is coded AUTH_REQUIRED, never
zero-filled; the feature step substitutes labeled MODELED reanalysis.

Official source: https://earthdata.nasa.gov
"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, MANUAL_DIR, write_json, utcnow, OFFICIAL_SOURCES

REPORT = os.path.join(RAW_DIR, "smap_ingest_report.json")
MANUAL_GLOB = os.path.join(MANUAL_DIR, "smap", "*.csv")


def _load_manual(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f)):
            try:
                out.append({"event_ref": r.get("event_ref") or r.get("event_id") or f"row-{i}",
                            "timestamp": r.get("timestamp"), "soil_moisture": float(r["soil_moisture"]),
                            "latitude": float(r.get("latitude", float("nan"))),
                            "longitude": float(r.get("longitude", float("nan"))),
                            "depth": r.get("depth", "0-5cm"), "product": r.get("product", "SPL3SMP"),
                            "quality": "REAL (SMAP L3, manual official file)"})
            except (KeyError, TypeError, ValueError):
                continue
    return out


def main() -> dict:
    os.makedirs(os.path.join(MANUAL_DIR, "smap"), exist_ok=True)
    manual = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--manual=")]
    files = manual + sorted(glob.glob(MANUAL_GLOB))
    user = os.getenv("EARTHDATA_USERNAME", "")
    if files and all(os.path.exists(p) for p in files):
        recs = []
        for p in files:
            recs.extend(_load_manual(p))
        write_json(os.path.join(RAW_DIR, "smap_manual.json"), recs)
        rep = {"status": "MANUAL_LOADED", "n": len(recs), "files": files, "at": utcnow()}
    elif user and os.getenv("EARTHDATA_PASSWORD", ""):
        rep = {"status": "CONFIGURED",
               "detail": "Earthdata credentials present; automated DAAC granule "
                         "retrieval is manual-gated (place files in data/manual/smap/ "
                         "or rerun with --manual=PATH). Nothing fetched automatically.",
               "at": utcnow()}
    else:
        rep = {"status": "AUTH_REQUIRED",
               "detail": "SMAP L3 needs Earthdata login. Set EARTHDATA_USERNAME + "
                         "EARTHDATA_PASSWORD (never commit), or place official files in "
                         "data/manual/smap/. Feature step uses labeled MODELED fallback.",
               "source": OFFICIAL_SOURCES["earthdata"], "at": utcnow()}
    write_json(REPORT, rep)
    print(f"smap: {rep}")
    return rep


if __name__ == "__main__":
    main()
