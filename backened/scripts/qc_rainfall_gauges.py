"""PHASE 2 — Gauge rainfall QC + Open-Meteo agreement analysis.

Reads the 3 datasets/ rainfall CSVs (READ-ONLY) and:
1. Validates timestamps (format + range), coords, duplicates, sentinel
   values (-999* → missing, never zero), negatives, spikes (>500 mm/h,
   >1000 mm/day → flagged, excluded from features, never silently capped
   into use).
2. Writes a cleaned station registry:
   data/processed/gauge_stations_v2.json (station, district, lat/lon,
   file, period, n_rows, qc flags, usability verdict).
3. Agreement check: for each v2 TRAINING_ELIGIBLE event day that falls
   inside a gauge file's span, compares nearest-station gauge accumulation
   vs the Open-Meteo archive day sum at the event coords (fetched live;
   failures → NOT_AVAILABLE, never blocking). Writes
   data/processed/gauge_agreement_v2.json.

Provenance verdict: OBSERVED-gauge (instrument reading) with origin
UNKNOWN — tagged `gauge-unverified`, never "real observed" without the
WRIS/department confirmation (recorded as DATA GAP).

Run: python scripts/qc_rainfall_gauges.py [--write] [--agree N]
--agree limits agreement events (default 12, deterministic first-N by day).
"""
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import haversine_km  # noqa: E402
from ner_v2_common import (  # noqa: E402
    DATASETS_DIR, PROCESSED_DIR, META_DIR, GAUGE_MISSING,
    HOURLY_SPIKE_MM, DAILY_SPIKE_MM, PROV_GAUGE, utcnow,
)

FILES = {
    "manual_0120": ("rainfall_manual_daily_meghalaya_ml_1991_2020.csv",
                    "Manual Daily Rainfall (mm)", "D", "%d-%m-%Y %H:%M"),
    "manual_2125": ("rainfall_manual_daily_meghalaya_ml_2021_2025.csv",
                    "Manual Daily Rainfall (mm)", "D", "%d-%m-%Y %H:%M"),
    "tel_2125": ("rainfall_tel_hr_meghalaya_ml_2021_2025.csv",
                 "Telemetry Hourly Rainfall (mm)", "H", "%d-%m-%Y %H:%M"),
}
STATIONS_JSON = os.path.join(PROCESSED_DIR, "gauge_stations_v2.json")
AGREE_JSON = os.path.join(PROCESSED_DIR, "gauge_agreement_v2.json")
QC_META = os.path.join(META_DIR, "gauge_qc_v2.json")
CAND_JSON = os.path.join(PROCESSED_DIR, "reports_v2_candidates.json")


def qc_file(key: str) -> dict:
    fname, valcol, kind, fmt = FILES[key]
    path = os.path.join(DATASETS_DIR, fname)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    spike_lim = HOURLY_SPIKE_MM if kind == "H" else DAILY_SPIKE_MM
    stations: dict = {}
    bad_ts = dup = sentinel = neg = spike = 0
    seen = set()
    dmin = dmax = None
    for r in rows:
        st = (r.get("Station") or "").strip()
        try:
            lat = float(r.get("Latitude") or "")
            lon = float(r.get("Longitude") or "")
            ok_ll = -90 <= lat <= 90 and -180 <= lon <= 180
        except (ValueError, TypeError):
            lat = lon = None
            ok_ll = False
        try:
            t = dt.datetime.strptime((r.get("Data Acquisition Time") or "").strip(), fmt)
            ok_ts = True
        except ValueError:
            t = None
            ok_ts = False
            bad_ts += 1
        if ok_ts:
            dmin = t if dmin is None or t < dmin else dmin
            dmax = t if dmax is None or t > dmax else dmax
        try:
            v = float((r.get(valcol) or "").strip())
            ok_v = True
        except (ValueError, AttributeError):
            v = None
            ok_v = False
        flag = "OK"
        if not ok_ts:
            flag = "BAD_TIMESTAMP"
        elif (st, t) in seen:
            flag = "DUPLICATE"
            dup += 1
        elif ok_v and v in GAUGE_MISSING:
            flag = "MISSING_SENTINEL"
            sentinel += 1
        elif ok_v and v < 0:
            flag = "NEGATIVE"
            neg += 1
        elif ok_v and v > spike_lim:
            flag = "SPIKE"
            spike += 1
        seen.add((st, t))
        s = stations.setdefault(st, {
            "station": st, "district": (r.get("District") or "").strip(),
            "latitude": lat, "longitude": lon, "coords_ok": ok_ll,
            "file": fname, "kind": kind, "n_rows": 0, "n_ok": 0,
            "flags": {}, "tmin": None, "tmax": None})
        s["n_rows"] += 1
        if flag == "OK":
            s["n_ok"] += 1
        else:
            s["flags"][flag] = s["flags"].get(flag, 0) + 1
        if ok_ts:
            iso = t.isoformat()
            s["tmin"] = iso if not s["tmin"] or iso < s["tmin"] else s["tmin"]
            s["tmax"] = iso if not s["tmax"] or iso > s["tmax"] else s["tmax"]
    usable = sum(1 for s in stations.values()
                 if s["coords_ok"] and s["n_ok"] > 0 and 24.5 <= (s["latitude"] or 0) <= 26.5)
    return {"file": fname, "kind": kind, "rows": len(rows),
            "bad_timestamps": bad_ts, "duplicates": dup,
            "sentinel_missing": sentinel, "negatives": neg, "spikes": spike,
            "span": [dmin.isoformat() if dmin else None, dmax.isoformat() if dmax else None],
            "n_stations": len(stations), "n_usable_stations": usable,
            "provenance": "OBSERVED-gauge, origin UNKNOWN (gauge-unverified)",
            "stations": sorted(stations.values(), key=lambda s: s["station"])}


def load_ok_values(key: str) -> list[dict]:
    fname, valcol, kind, fmt = FILES[key]
    path = os.path.join(DATASETS_DIR, fname)
    spike_lim = HOURLY_SPIKE_MM if kind == "H" else DAILY_SPIKE_MM
    out = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                t = dt.datetime.strptime((r.get("Data Acquisition Time") or "").strip(), fmt)
                v = float((r.get(valcol) or "").strip())
                lat = float(r.get("Latitude") or "")
                lon = float(r.get("Longitude") or "")
            except (ValueError, AttributeError, TypeError):
                continue
            if v in GAUGE_MISSING or v < 0 or v > spike_lim:
                continue
            out.append({"station": (r.get("Station") or "").strip(),
                        "t": t, "v": v, "lat": lat, "lon": lon})
    return out


def om_day_sum(lat: float, lon: float, day: str) -> float | None:
    import urllib.request
    import urllib.parse
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "start_date": day,
        "end_date": day, "hourly": "precipitation", "timezone": "UTC"})
    try:
        req = urllib.request.Request(
            f"https://archive-api.open-meteo.com/v1/archive?{q}",
            headers={"User-Agent": "GEO-SENTINEL-ner-pipeline/2.0"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            h = json.loads(resp.read().decode()).get("hourly", {})
        vals = [x or 0.0 for x in h.get("precipitation", [])]
        return round(sum(vals), 2) if vals else None
    except Exception:
        return None


def agreement(vals_by_file: dict, n: int) -> dict:
    cands = [c for c in json.load(open(CAND_JSON, encoding="utf-8"))
             if c.get("status") == "TRAINING_ELIGIBLE"]
    cands.sort(key=lambda c: (c["event_day"], c["source_event_id"]))
    # gauge files only cover Meghalaya; restrict to ML rows in span
    tel = [v for v in vals_by_file["tel_2125"]]
    man = [v for v in vals_by_file["manual_0120"]]
    res = []
    for c in cands:
        if c["state"] != "Meghalaya":
            continue
        day = c["event_day"]
        pool = tel if "2023-01-01" <= day <= "2025-12-31" else (
            man if "2001-01-01" <= day <= "2018-12-31" else [])
        if not pool:
            continue
        near = min(pool, key=lambda v: haversine_km(c["latitude"], c["longitude"], v["lat"], v["lon"]))
        dist = haversine_km(c["latitude"], c["longitude"], near["lat"], near["lon"])
        if dist > 60.0:
            res.append({"event": c["source_event_id"], "day": day,
                        "verdict": "NO_STATION_IN_RANGE", "dist_km": round(dist, 1)})
            continue
        same = [v["v"] for v in pool
                if v["station"] == near["station"] and v["t"].date().isoformat() == day]
        if not same:
            res.append({"event": c["source_event_id"], "day": day,
                        "verdict": "NO_GAUGE_DAY", "station": near["station"]})
            continue
        om = om_day_sum(c["latitude"], c["longitude"], day)
        res.append({"event": c["source_event_id"], "day": day,
                    "station": near["station"], "dist_km": round(dist, 1),
                    "gauge_day_mm": round(sum(same), 2),
                    "om_day_mm": om,
                    "verdict": ("COMPARED" if om is not None else "OM_UNAVAILABLE")})
        if sum(1 for r in res if r["verdict"] == "COMPARED") >= n:
            break
    compared = [r for r in res if r["verdict"] == "COMPARED"]
    if compared:
        diffs = [abs(r["gauge_day_mm"] - (r["om_day_mm"] or 0)) for r in compared]
        summary = {"n_compared": len(compared),
                   "mean_abs_diff_mm": round(sum(diffs) / len(diffs), 2),
                   "max_abs_diff_mm": round(max(diffs), 2)}
    else:
        summary = {"n_compared": 0}
    summary["n_checked"] = len(res)
    return {"summary": summary, "rows": res}


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--agree", type=int, default=12)
    args = ap.parse_args()
    reports = {k: qc_file(k) for k in FILES}
    print(json.dumps({k: {kk: v for kk, v in r.items() if kk != "stations"}
                      for k, r in reports.items()}, indent=1))
    out = {"at": utcnow(), "files": reports}
    if args.write:
        stations = []
        for r in reports.values():
            stations.extend(r["stations"])
        with open(STATIONS_JSON, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(), "provenance": PROV_GAUGE,
                       "n": len(stations), "stations": stations}, fh, indent=1)
        vals = {k: load_ok_values(k) for k in FILES}
        agr = agreement(vals, args.agree)
        with open(AGREE_JSON, "w", encoding="utf-8") as fh:
            json.dump(agr, fh, indent=1)
        with open(QC_META, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(),
                       "rules": {"sentinel": sorted(GAUGE_MISSING),
                                 "hourly_spike_mm": HOURLY_SPIKE_MM,
                                 "daily_spike_mm": DAILY_SPIKE_MM,
                                 "station_range_km": 60.0},
                       "code_version": "ner-pipeline-2.0"}, fh, indent=1)
        print(f"agreement: {json.dumps(agr['summary'])}")
        print(f"wrote {STATIONS_JSON}, {AGREE_JSON}, {QC_META}")
        out["agreement"] = agr["summary"]
    return out


if __name__ == "__main__":
    main()
