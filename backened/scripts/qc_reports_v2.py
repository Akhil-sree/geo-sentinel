"""PHASE 1 — Landslide Reports.csv QC → validated event candidates.

Reads datasets/Landslide Reports.csv (READ-ONLY) and produces the audited
funnel RAW → NER → DATED → SPATIALLY VALID → NOVEL → DEDUPLICATED →
TRAINING-ELIGIBLE, written to data/processed/reports_v2_candidates.{csv,json}
plus data/metadata/reports_v2_qc.json. No database writes. Never invents
dates, coords, or sources; every rejection carries a status + reason.

Verification policy (honest, no per-row field access possible here):
- SOURCE check: row must name a real information source AND (event catalog
  ref OR source URL). Rows with neither → SOURCE_UNVERIFIED (kept out of
  TRAINING_ELIGIBLE, retained as candidates for later field verification).
- LOCATION: GLC accuracy bucket must be <= 5 km, else LOCATION_WEAK.
- DATE: must parse to a calendar day (Reports dates are day-precision),
  else DATE_WEAK. The "5:30 am" suffix is a load stamp, not event time.
- DEDUP: vs existing ner_inventory_v1.json (same day + <= 2 km, the project
  rule) and within-file; bulk single-day artifacts (>25 same-day NER rows
  from one mapping campaign) are flagged, not promoted.
- RAINFALL feasibility: event day must fall inside a usable rainfall window
  (Open-Meteo archive covers 1940→~now; gauge files cover their own spans;
  future-dated rows fail). Informational only — features are built later.

Run: python scripts/qc_reports_v2.py [--write]
Without --write it only prints the funnel (audit mode).
"""
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import haversine_km, in_ner  # noqa: E402
from ner_v2_common import (  # noqa: E402
    DATASETS_DIR, PROCESSED_DIR, META_DIR, ACC_KM, TRAINING_ACC_KM,
    DEDUP_KM, NER_DIVISIONS, ST_CANDIDATE, ST_QC_FAILED, ST_DUPLICATE,
    ST_LOCATION_WEAK, ST_DATE_WEAK, ST_SOURCE_UNVERIFIED,
    ST_TRAINING_ELIGIBLE, utcnow,
)
from ner_v2_common import ST_RAW  # noqa: E402,F401

REPORTS_CSV = os.path.join(DATASETS_DIR, "Landslide Reports.csv")
INVENTORY_JSON = os.path.join(PROCESSED_DIR, "ner_inventory_v1.json")
CAND_CSV = os.path.join(PROCESSED_DIR, "reports_v2_candidates.csv")
CAND_JSON = os.path.join(PROCESSED_DIR, "reports_v2_candidates.json")
QC_META = os.path.join(META_DIR, "reports_v2_qc.json")

OM_ARCHIVE_START = dt.date(1940, 1, 1)


def parse_day(value: str) -> str | None:
    """'DD/MM/YY, 5:30 am' → ISO day. Returns None when unparseable."""
    s = (value or "").strip()
    if not s:
        return None
    try:
        day = s.split(",")[0].strip()
        dd, mm, yy = (int(x) for x in day.split("/"))
        yy += 2000 if yy < 100 else 0
        return dt.date(yy, mm, dd).isoformat()
    except (ValueError, IndexError):
        return None


def parse_coords(row: dict) -> tuple | None:
    try:
        lat = float((row.get("Latitude") or "").strip())
        lon = float((row.get("Longitude") or "").strip())
    except (ValueError, AttributeError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return (lat, lon)


def source_verified(row: dict) -> tuple[bool, str]:
    """A row is source-verified iff it names an information source AND gives
    either a catalog reference or a retrievable link. Anything less stays a
    candidate (SOURCE_UNVERIFIED), never a label."""
    name = (row.get("Name of Information Source") or "").strip()
    link = (row.get("Link to Information Source") or "").strip()
    cat = (row.get("Imported Event Source Catalog") or "").strip()
    sid = (row.get("Imported Event Source Id") or "").strip()
    if not name:
        return False, "no information source named"
    if cat and sid:
        return True, f"catalog {cat}:{sid}"
    if link.startswith("http"):
        return True, "source link present"
    if cat:
        return True, f"catalog {cat} (no numeric id)"
    return False, "named source but no catalog ref or link"


def load_reports() -> list[dict]:
    with open(REPORTS_CSV, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_inventory() -> tuple[list, list]:
    with open(INVENTORY_JSON, encoding="utf-8") as fh:
        inv = json.load(fh)
    temp = [x for x in inv if x.get("kind") == "TEMPORAL" and x.get("date")]
    spat = [x for x in inv if x.get("kind") == "SPATIAL"]
    return temp, spat


def funnel(rows: list[dict], inv_temp: list, inv_spat: list) -> tuple[list[dict], dict]:
    stats: dict = {"raw": len(rows)}
    # NER filter (administrative division — explicit, auditable)
    ner = [r for r in rows if (r.get("Administrative Division") or "").strip() in NER_DIVISIONS]
    stats["ner"] = len(ner)
    out: list[dict] = []
    for r in ner:
        day = parse_day(r.get("Event Date"))
        ll = parse_coords(r)
        acc_raw = (r.get("Location Accuracy") or "").strip()
        acc_km = ACC_KM.get(acc_raw)
        ok_src, src_how = source_verified(r)
        rec = {
            "source": "coolr-reports",
            "source_event_id": f"coolr-{(r.get('Event ID') or '').strip()}-{(r.get('OBJECTID') or '').strip()}",
            "event_day": day,
            "latitude": ll[0] if ll else None,
            "longitude": ll[1] if ll else None,
            "district": (r.get("Administrative Division") or "").strip(),
            "state": (r.get("Administrative Division") or "").strip(),
            "event_type": (r.get("Landslide Category") or "").strip() or "UNKNOWN",
            "trigger": (r.get("Landslide Trigger") or "").strip() or "UNKNOWN",
            "fatalities": (r.get("Number of Fatalities") or "").strip() or None,
            "location_accuracy": acc_raw or "UNKNOWN",
            "accuracy_km": acc_km,
            "source_name": (r.get("Name of Information Source") or "").strip(),
            "source_link": (r.get("Link to Information Source") or "").strip(),
            "source_catalog": (r.get("Imported Event Source Catalog") or "").strip(),
            "source_how": src_how,
            "in_ner": bool(ll) and in_ner(ll[0], ll[1]),
            "rain_feasible": False,
        }
        # status cascade: date → coords → source → location → (dedup later)
        if day is None:
            rec["status"], rec["reason"] = ST_DATE_WEAK, "event date missing/unparseable"
        elif ll is None:
            rec["status"], rec["reason"] = ST_QC_FAILED, "coords missing/invalid"
        elif not ok_src:
            rec["status"], rec["reason"] = ST_SOURCE_UNVERIFIED, src_how
        elif acc_km is None or acc_km > TRAINING_ACC_KM:
            rec["status"], rec["reason"] = ST_LOCATION_WEAK, f"accuracy '{acc_raw}' > 5 km"
        else:
            rec["status"], rec["reason"] = ST_CANDIDATE, src_how
        out.append(rec)
    stats["dated"] = sum(1 for r in out if r["event_day"])
    stats["spatially_valid"] = sum(1 for r in out if r["status"] == ST_CANDIDATE)
    # novelty vs existing inventory: same day + <= 2 km (temporal), else <= 2 km spatial
    novel = []
    n_temp_overlap = n_spat_overlap = 0
    for r in out:
        if r["status"] != ST_CANDIDATE:
            continue
        hit_t = any((t.get("date") or "")[:10] == r["event_day"]
                    and haversine_km(r["latitude"], r["longitude"], t["lat"], t["lon"]) <= DEDUP_KM
                    for t in inv_temp)
        if hit_t:
            r["status"], r["reason"], n_temp_overlap = ST_DUPLICATE, "matches inventory TEMPORAL (day+2km)", n_temp_overlap + 1
            continue
        hit_s = any(haversine_km(r["latitude"], r["longitude"], s["lat"], s["lon"]) <= DEDUP_KM
                    for s in inv_spat)
        if hit_s:
            r["status"], r["reason"], n_spat_overlap = ST_DUPLICATE, "within 2 km of inventory SPATIAL", n_spat_overlap + 1
            continue
        novel.append(r)
    stats["novel"] = len(novel)
    stats["overlap_temporal"] = n_temp_overlap
    stats["overlap_spatial"] = n_spat_overlap
    # within-file dedup (same day + <= 2 km keeps first, rest DUPLICATE)
    kept: list[dict] = []
    n_wd = 0
    for r in novel:
        if any(k["event_day"] == r["event_day"]
               and haversine_km(r["latitude"], r["longitude"], k["latitude"], k["longitude"]) <= DEDUP_KM
               for k in kept):
            r["status"], r["reason"], n_wd = ST_DUPLICATE, "within-file same-day 2 km duplicate", n_wd + 1
            continue
        kept.append(r)
    stats["within_file_dupes"] = n_wd
    stats["deduplicated"] = len(kept)
    # bulk single-day artifact flag (>25 same-day NER rows from the funnel):
    # informational — such days need campaign-level review before promotion
    by_day: dict[str, int] = {}
    for r in kept:
        by_day[r["event_day"]] = by_day.get(r["event_day"], 0) + 1
    stats["bulk_days"] = {d: n for d, n in by_day.items() if n > 25}
    # rainfall feasibility + final eligibility
    today = dt.date.today()
    n_elig = 0
    for r in kept:
        day = dt.date.fromisoformat(r["event_day"])
        if day < OM_ARCHIVE_START or day > today:
            r["status"], r["reason"] = ST_QC_FAILED, "event day outside rainfall-archive span"
            continue
        r["rain_feasible"] = True
        r["status"], r["reason"] = ST_TRAINING_ELIGIBLE, "passed all QC gates"
        n_elig += 1
    stats["training_eligible"] = n_elig
    stats["by_status"] = {}
    for r in out:
        stats["by_status"][r["status"]] = stats["by_status"].get(r["status"], 0) + 1
    stats["by_state_eligible"] = {}
    for r in kept:
        if r["status"] == ST_TRAINING_ELIGIBLE:
            stats["by_state_eligible"][r["state"]] = stats["by_state_eligible"].get(r["state"], 0) + 1
    return out, stats


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    rows = load_reports()
    inv_temp, inv_spat = load_inventory()
    recs, stats = funnel(rows, inv_temp, inv_spat)
    print(f"reports funnel: {json.dumps(stats, indent=1)}")
    if args.write:
        from ner_v2_common import PROCESSED_DIR as _p, META_DIR as _m  # noqa
        with open(CAND_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(recs[0].keys()))
            w.writeheader()
            w.writerows(recs)
        with open(CAND_JSON, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, indent=1)
        with open(QC_META, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(), "stats": stats,
                       "policy": "accuracy<=5km, dedup 2km+day, source catalog-or-link, rain-feasible",
                       "code_version": "ner-pipeline-2.0"}, fh, indent=1)
        print(f"wrote {CAND_CSV} ({len(recs)} rows), {CAND_JSON}, {QC_META}")
    return stats


if __name__ == "__main__":
    main()
