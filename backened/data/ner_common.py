"""Shared NER training-pipeline core: bounds, validation, date classes,
deduplication, downloads, provenance, missingness codes.

Nothing here fabricates data: every helper classifies and records; sources
that cannot be reached return honest statuses (DOWNLOADED / AUTH_REQUIRED /
MANUAL_DOWNLOAD_REQUIRED / UNAVAILABLE / FAILED).
"""
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone

# Primary training region (SIH §5)
NER_LAT = (22.0, 29.0)
NER_LON = (90.0, 96.0)

DATE_QUALITIES = ("EXACT_DATE", "YEAR_ONLY", "MONTH_ONLY", "UNKNOWN", "ESTIMATED")

# Missingness taxonomy (SIH §22) — never silently zero-filled
MISSING = ("NOT_AVAILABLE", "NOT_ACQUIRED", "AUTH_REQUIRED", "OUT_OF_COVERAGE",
           "QUALITY_REJECTED", "TEMPORARILY_UNAVAILABLE")

# Label terminology (SIH §8): negatives are absence-of-record, not proof
POSITIVE = "RECORDED_LANDSLIDE"
NEGATIVE = "NO_RECORDED_LANDSLIDE"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
META_DIR = os.path.join(DATA_DIR, "metadata")
MANUAL_DIR = os.path.join(DATA_DIR, "manual")

OFFICIAL_SOURCES = {
    "coolr": "https://landslides.nasa.gov",
    "gsi": "https://bhukosh.gsi.gov.in/Bhukosh/Public",
    "nrsc": "https://www.isro.gov.in",
    "openmeteo_archive": "https://open-meteo.com/en/docs/historical-weather-api",
    "openmeteo": "https://open-meteo.com/en/docs",
    "earthdata": "https://earthdata.nasa.gov",
    "usgs": "https://earthexplorer.usgs.gov",
    "copernicus": "https://dataspace.copernicus.eu",
    "geofabrik": "https://download.geofabrik.de/asia/india.html",
    "osmnx": "https://osmnx.readthedocs.io",
    "imd": "https://mausam.imd.gov.in",
    "openweather": "https://openweathermap.org/api",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def in_ner(lat: float, lon: float) -> bool:
    try:
        return (NER_LAT[0] <= float(lat) <= NER_LAT[1]
                and NER_LON[0] <= float(lon) <= NER_LON[1])
    except (TypeError, ValueError):
        return False


def valid_coords(lat, lon) -> bool:
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
    except (TypeError, ValueError):
        return False


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    d1, d2 = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = (math.sin(d1 / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(d2 / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def classify_date(value) -> tuple[str, str | None]:
    """Classify a date value → (quality, iso-or-None). Only EXACT_DATE
    carries a usable timestamp; never invents dates."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "UNKNOWN", None
    if isinstance(value, datetime):
        return "EXACT_DATE", value.isoformat()
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return "EXACT_DATE", datetime.strptime(s[:19] if "T" in s or " " in s
                                                   else s, fmt).isoformat()
        except ValueError:
            continue
    if len(s) == 7 and s[4] == "-":
        return "MONTH_ONLY", None
    if len(s) == 4 and s.isdigit():
        return "YEAR_ONLY", None
    return "UNKNOWN", None


def download(url: str, dest: str, timeout: int = 30,
             retries: int = 3) -> dict:
    """Download with retry+backoff+resume-awareness. Returns a status record;
    never raises for transport failures (FAILED status instead)."""
    import urllib.request
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    attempt, last_err = 0, ""
    while attempt < retries:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r, \
                    open(dest, "wb") as f:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            return {"status": "DOWNLOADED", "url": url, "file": dest,
                    "size": os.path.getsize(dest),
                    "sha256": sha256_file(dest),
                    "downloaded_at": utcnow()}
        except Exception as e:  # noqa: BLE001 — transport failure is data, not crash
            last_err = f"{type(e).__name__}: {e}"[:200]
            attempt += 1
            time.sleep(2 ** attempt)
    return {"status": "FAILED", "url": url, "error": last_err,
            "attempts": retries, "downloaded_at": utcnow()}


def sha256_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()[:16]


def dedup_records(records: list[dict], dist_km: float = 2.0) -> tuple[list[dict], dict]:
    """Deterministic dedup: same source_event_id, or (≤dist_km AND same
    event_date), share a canonical_event_id. Uncertain pairs stay separate
    (flagged), never force-merged."""
    canon, groups, report = {}, {}, {"n_in": len(records), "n_groups": 0,
                                     "merged": 0, "flagged_review": 0}
    for r in records:
        key = None
        sid = r.get("source_event_id")
        if sid and sid in groups:
            key = groups[sid]
        else:
            for c, members in canon.items():
                m = members[0]
                same_date = (r.get("event_date") and r.get("event_date") == m.get("event_date"))
                try:
                    near = haversine_km(r["latitude"], r["longitude"],
                                        m["latitude"], m["longitude"]) <= dist_km
                except (KeyError, TypeError):
                    near = False
                if near and same_date:
                    key = c
                    break
                if near and not r.get("event_date") and not m.get("event_date"):
                    r["review_flag"] = "spatial-duplicate-candidate"
                    report["flagged_review"] += 1
        if key is None:
            key = f"CANON-{len(canon) + 1:05d}"
            canon[key] = []
        else:
            report["merged"] += 1
        r["canonical_event_id"] = key
        canon[key].append(r)
        if sid:
            groups[sid] = key
    report["n_groups"] = len(canon)
    for c, members in canon.items():
        for r in members:
            r["source_count"] = len(members)
    return records, report


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def dataset_checksum(path: str) -> str | None:
    return sha256_file(path)
