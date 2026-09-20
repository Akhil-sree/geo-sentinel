"""Real temporal sequence acquisition (Phases 1–4).

For each seed inventory event (date + zone centroid) fetch genuine ERA5
history from the Open-Meteo ARCHIVE API (keyless):
  168h pre-event window, hourly precipitation (observed blend) +
  soil_moisture_3_9cm (MODELED reanalysis — labeled as such).

Matched negatives: same zone, same month-day in a non-event year
(background sampling, documented — never random labels).

Prediction timestamp = event date 12:00 UTC (inventory dates lack time;
documented approximation). ALL features use hours <= t (pre-event only).

Stages:
  --fetch : network -> data/raw/archive_{zid}_{yyyymmdd}_{pos|neg}.json
  --build : raw -> data/processed/sequences_v1.npz + samples_v1.csv

Rate: 24 API calls (10 pos + 14 neg). Deterministic build.
"""
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import ZONES, EVENTS  # noqa: E402

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw")
WINDOW_H = 168

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def _window_for(event_date: str):
    end = dt.datetime.fromisoformat(event_date).replace(
        hour=12, tzinfo=dt.timezone.utc)
    start = end - dt.timedelta(hours=WINDOW_H)
    return start, end


def plan_samples():
    """(zone_id, end_date_str, label) — 10 positives + 14 matched negatives."""
    zmap = {z["id"]: z for z in ZONES}
    pos = []
    for zid, d, _t in EVENTS:
        pos.append((zid, d, 1))
    by_zone = {}
    for zid, d, _ in EVENTS:
        by_zone.setdefault(zid, set()).add(d[:4])
    neg = []
    for z in ZONES:
        zid = z["id"]
        taken = by_zone.get(zid, set())
        md = None
        for _zid, d, _ in EVENTS:
            if _zid == zid:
                md = d[5:]
                break
        md = md or "07-15"
        for yr in ("2022", "2023", "2024"):
            if yr not in taken:
                neg.append((zid, f"{yr}-{md}", 0))
    out = [(zid, d, lab) for zid, d, lab in pos + neg]
    assert len([s for s in out if s[2] == 1]) == 10
    assert len([s for s in out if s[2] == 0]) == 14
    return sorted(out), zmap


def fetch():
    import httpx
    os.makedirs(RAW, exist_ok=True)
    samples, zmap = plan_samples()
    for zid, d, lab in samples:
        z = zmap[zid]
        start, end = _window_for(d)
        fn = os.path.join(
            RAW, f"archive_{zid}_{d.replace('-', '')}_{'pos' if lab else 'neg'}.json")
        if os.path.exists(fn):
            print("cached", fn)
            continue
        r = httpx.get(ARCHIVE, params={
            "latitude": z["lat"], "longitude": z["lng"],
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "hourly": "precipitation,soil_moisture_3_9cm",
            "timezone": "UTC"}, timeout=60)
        r.raise_for_status()
        payload = {"zone_id": zid, "end_date": d, "label": lab,
                   "centroid": [z["lat"], z["lng"]],
                   "window_h": WINDOW_H,
                   "prediction_timestamp": end.isoformat(),
                   "rainfall_source": ("Open-Meteo archive (ERA5 observed "
                                       "blend, code 201)"),
                   "soil_source": "MODELED (ERA5-Land reanalysis via Open-Meteo)",
                   "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "hourly": r.json().get("hourly", {})}
        json.dump(payload, open(fn, "w"))
        print("fetched", fn, len(payload["hourly"].get("time", [])), "hours")


def build(tag="v1"):
    """tag=v1: plan_samples only (24). tag=v2: + *_hard.json (32)."""
    import glob as _glob
    import numpy as np
    import pandas as pd
    from app.ml.features import build_model_sequence
    samples, zmap = plan_samples()
    if tag == "v2":
        for fn in sorted(_glob.glob(os.path.join(RAW, "archive_*_hard.json"))):
            p0 = json.load(open(fn))
            samples.append((p0["zone_id"], p0["end_date"], 0))
        samples = sorted(set(samples))
    X, y, groups, rows = [], [], [], []
    for zid, d, lab in samples:
        cands = [os.path.join(
            RAW, f"archive_{zid}_{d.replace('-', '')}_{s}.json")
            for s in (("pos" if lab else "neg"), "hard")]
        fn = next((c for c in cands if os.path.exists(c)), None)
        assert fn, f"missing raw for {(zid, d, lab)}"
        p = json.load(open(fn))
        h = p["hourly"]
        # PRE-EVENT ONLY: clip to prediction timestamp (leakage guard)
        t_end = dt.datetime.fromisoformat(p["prediction_timestamp"])
        times = [dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc)
                 for t in h["time"]]
        rain = [0.0 if v is None else float(v) for v in h["precipitation"]]
        soil = [v if v is None else float(v) for v in h["soil_moisture_3_9cm"]]
        past = [(t, r, s) for t, r, s in zip(times, rain, soil) if t <= t_end]
        assert len(past) >= WINDOW_H, f"{fn}: only {len(past)} pre-event hours"
        past = past[-WINDOW_H:]
        rain_df = pd.DataFrame([{"timestamp": t, "rainfall_mm_per_hr": r}
                                for t, r, _ in past])
        s_vals, last = [], 0.34
        for _, _, s in past:  # forward-fill Nones, default 0.34 (documented)
            last = s if s is not None else last
            s_vals.append(last)
        soil_df = pd.DataFrame([{"timestamp": t, "soil_moisture": s}
                                for (t, _, _), s in zip(past, s_vals)])
        seq = build_model_sequence(rain_df, soil_df, 0.0, seq_len=48)
        assert len(seq) == 48, f"{fn}: seq len {len(seq)}"
        X.append(seq[-48:])
        y.append(lab)
        groups.append(zmap[zid]["district"])
        arr = np.asarray(seq)
        rows.append({"sample_id": f"{zid}-{d}", "zone_id": zid,
                     "end_date": d, "label": lab,
                     "rain_24h": round(float(arr[-24:, 1].max() * 300), 1),
                     "rain_72h": round(float(arr[-1, 2] * 600), 1),
                     "soil_last": round(float(arr[-1, 4]), 3),
                     "soil_source": "MODELED"})
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=int)
    ver = "seq_real_v2" if tag == "v2" else "seq_real_v1"
    stem = "sequences_v2" if tag == "v2" else "sequences_v1"
    samp = "samples_v2.csv" if tag == "v2" else "samples_v1.csv"
    np.savez(os.path.join(HERE, "processed", f"{stem}.npz"),
             X=X, y=y, groups=np.asarray(groups),
             meta=json.dumps({"dataset_version": ver,
                              "n": len(X), "pos": int(y.sum()),
                              "window_h": WINDOW_H, "seq_len": 48,
                              "rainfall_source": "Open-Meteo archive ERA5",
                              "soil_source": "MODELED ERA5-Land",
                              "negatives": ("matched same-zone non-event years"
                                            + (" + hard peak-rain no-event "
                                               "windows" if tag == "v2" else ""))}))
    with open(os.path.join(HERE, "processed", samp), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"built {ver}: {len(X)} real sequences ({int(y.sum())} pos)")


def fetch_hard_negatives():
    """HARD negatives (Phase 2): per zone, the wettest 7-day window in any
    monsoon (Jun–Sep 2022/24 non-event context) with no RECORDED event
    within ±30 days and no overlap with existing samples.

    Label means "extreme conditions, no RECORDED event" — the inventory may
    be incomplete (documented caveat, not hidden). One per zone → v2.
    """
    import httpx
    import glob as _glob
    os.makedirs(RAW, exist_ok=True)
    samples, zmap = plan_samples()
    have = {(zid, d) for zid, d, _ in samples}
    event_days = {}
    for zid, d, lab in samples:
        if lab == 1:
            event_days.setdefault(zid, []).append(
                dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc))
    new = []
    for z in ZONES:
        zid = z["id"]
        r = httpx.get(ARCHIVE, params={
            "latitude": z["lat"], "longitude": z["lng"],
            "start_date": "2022-06-01", "end_date": "2024-09-30",
            "daily": "precipitation_sum", "timezone": "UTC"}, timeout=60)
        r.raise_for_status()
        daily = r.json()["daily"]
        days = [dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc)
                for t in daily["time"]]
        rain = [0.0 if v is None else float(v)
                for v in daily["precipitation_sum"]]
        best, best_sum = None, -1.0
        for i in range(len(days) - 6):
            w = [days[i + k] for k in range(7)]
            s = sum(rain[i:i + 7])
            mid = w[6]  # window end day; prediction ts = noon
            if any(abs((mid - e).days) <= 30 for e in event_days.get(zid, [])):
                continue
            if any(abs((mid - dt.datetime.fromisoformat(d)
                        .replace(tzinfo=dt.timezone.utc)).days) <= 8
                   for zz, d in have if zz == zid):
                continue
            if s > best_sum:
                best, best_sum = mid, s
        assert best is not None, f"{zid}: no qualifying hard-negative window"
        dstr = best.strftime("%Y-%m-%d")
        new.append((zid, dstr, best_sum))
        print(f"{zid}: hard neg ending {dstr} (7d sum {best_sum:.0f}mm)")
    # Fetch hourly 168h windows for the chosen negatives
    for zid, dstr, wsum in new:
        z = zmap[zid]
        end = dt.datetime.fromisoformat(dstr).replace(
            hour=12, tzinfo=dt.timezone.utc)
        start = end - dt.timedelta(hours=WINDOW_H)
        import httpx as _hx
        r = _hx.get(ARCHIVE, params={
            "latitude": z["lat"], "longitude": z["lng"],
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "hourly": "precipitation,soil_moisture_3_9cm",
            "timezone": "UTC"}, timeout=60)
        r.raise_for_status()
        fn = os.path.join(RAW, f"archive_{zid}_{dstr.replace('-', '')}_hard.json")
        json.dump({"zone_id": zid, "end_date": dstr, "label": 0,
                   "hard_negative": True,
                   "neg_reason": (f"wettest 7d window ({wsum:.0f}mm), no "
                                  "RECORDED event within ±30d — inventory "
                                  "may be incomplete"),
                   "centroid": [z["lat"], z["lng"]], "window_h": WINDOW_H,
                   "prediction_timestamp": end.isoformat(),
                   "rainfall_source": "Open-Meteo archive (ERA5 observed blend)",
                   "soil_source": "MODELED (ERA5-Land reanalysis via Open-Meteo)",
                   "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "hourly": r.json().get("hourly", {})}, open(fn, "w"))
        print("fetched", fn)


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    if "--build" in sys.argv:
        build("v2" if "--v2" in sys.argv else "v1")
    if "--fetch-hard" in sys.argv:
        fetch_hard_negatives()
    if len(sys.argv) < 2:
        print("usage: fetch_temporal.py --fetch [--build [--v2]] [--fetch-hard]")
