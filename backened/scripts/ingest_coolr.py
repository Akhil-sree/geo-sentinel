"""NASA COOLR / GLC inventory ingest (SIH §2.1).

Primary: Socrata bulk API (data.nasa.gov/resource/dd9e-wu2v.json, paged).
Fallback: --manual PATH (official CSV saved by hand from landslides.nasa.gov).
Every run writes data/raw/coolr_download_report.json with one of:
DOWNLOADED / FAILED / MANUAL_DOWNLOAD_REQUIRED / MANUAL_LOADED.
One failed source never crashes the pipeline.

Official source: https://landslides.nasa.gov
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import (download, in_ner, valid_coords, classify_date,
                        RAW_DIR, META_DIR, write_json, utcnow,
                        OFFICIAL_SOURCES)

SOCRATA = "https://data.nasa.gov/resource/dd9e-wu2v.json"
RAW_JSON = os.path.join(RAW_DIR, "coolr_glc.json")
REPORT = os.path.join(RAW_DIR, "coolr_download_report.json")
PAGE = 1000


def _fetch_socrata(timeout=30) -> dict:
    """Paged SODA retrieval. Raises on transport failure (→ FAILED report)."""
    import urllib.request
    rows, offset = [], 0
    while True:
        url = f"{SOCRATA}?$limit={PAGE}&$offset={offset}"
        req = urllib.request.Request(url, headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            page = json.loads(r.read().decode())
        if not page:
            break
        rows.extend(page)
        offset += PAGE
        if len(page) < PAGE:
            break
    return rows


def _normalize_socrata(rows: list[dict]) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        try:
            lat = float(r.get("latitude") or r.get("lat") or float("nan"))
            lon = float(r.get("longitude") or r.get("lon") or float("nan"))
        except (TypeError, ValueError):
            continue
        if not valid_coords(lat, lon):
            continue
        dq, iso = classify_date(r.get("event_date") or r.get("date"))
        out.append({
            "source": "coolr", "source_event_id": str(r.get(":id") or r.get("id") or f"glc-{i}"),
            "event_date": iso, "date_quality": dq,
            "latitude": lat, "longitude": lon,
            "event_type": r.get("landslide_type") or r.get("event_type"),
            "severity": r.get("landslide_size") or r.get("size"),
            "confidence": r.get("location_accuracy"),
            "description": (r.get("event_description") or "")[:500],
            "source_url": OFFICIAL_SOURCES["coolr"],
            "in_ner": in_ner(lat, lon),
            "data_quality": "socrata-bulk; frozen export current as of 2016-03-07",
        })
    return out


def _load_manual(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f)):
            lat = r.get("latitude") or r.get("lat") or r.get("Latitude")
            lon = r.get("longitude") or r.get("lon") or r.get("Longitude")
            try:
                lat, lon = float(lat), float(lon)
            except (TypeError, ValueError):
                continue
            if not valid_coords(lat, lon):
                continue
            dq, iso = classify_date(r.get("event_date") or r.get("date") or r.get("Date"))
            out.append({
                "source": "coolr", "source_event_id": f"manual-{i}",
                "event_date": iso, "date_quality": dq,
                "latitude": lat, "longitude": lon,
                "event_type": r.get("landslide_type"), "severity": r.get("size"),
                "confidence": r.get("accuracy"), "description": (r.get("description") or "")[:500],
                "source_url": OFFICIAL_SOURCES["coolr"], "in_ner": in_ner(lat, lon),
                "data_quality": f"manual official CSV: {os.path.basename(path)}",
            })
    return out


def main() -> dict:
    manual = next((a.split("=", 1)[1] for a in sys.argv
                   if a.startswith("--manual=")), None)
    if manual:
        if not os.path.exists(manual):
            rep = {"status": "MANUAL_DOWNLOAD_REQUIRED",
                   "detail": f"Manual file not found: {manual}. Save the official CSV from "
                             "https://landslides.nasa.gov (viewer → Download Landslide Catalog)."}
        else:
            recs = _load_manual(manual)
            write_json(RAW_JSON, recs)
            rep = {"status": "MANUAL_LOADED", "n": len(recs),
                   "n_ner": sum(1 for r in recs if r["in_ner"]),
                   "file": RAW_JSON, "at": utcnow()}
        write_json(REPORT, rep)
        print(f"coolr: {rep}")
        return rep
    try:
        rows = _fetch_socrata()
    except Exception as e:  # noqa: BLE001 — transport failure is a report, not a crash
        rep = {"status": "FAILED", "source": OFFICIAL_SOURCES["coolr"],
               "error": f"{type(e).__name__}: {e}"[:200],
               "action": "Retry with full egress, or rerun with --manual=PATH "
                         "(official CSV from https://landslides.nasa.gov).",
               "at": utcnow()}
        write_json(REPORT, rep)
        print(f"coolr: {rep}")
        return rep
    recs = _normalize_socrata(rows)
    write_json(RAW_JSON, recs)
    rep = {"status": "DOWNLOADED", "n_raw": len(rows), "n_valid": len(recs),
           "n_ner": sum(1 for r in recs if r["in_ner"]),
           "file": RAW_JSON, "at": utcnow()}
    write_json(REPORT, rep)
    print(f"coolr: {rep}")
    return rep


if __name__ == "__main__":
    main()
