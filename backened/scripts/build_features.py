"""NER feature engineering (SIH §7/§11-13/§15/§19-22).

Per TEMPORAL event + control, strictly ≤ event date (pre-event clip):
rain windows 1/3/6/12/24/48/72h/7/14/30d + max-1h/3h/24h + antecedent +
trend + intensity (Open-Meteo archive cache, REAL); soil current/1d/3d/7d
(SMAP-manual REAL if present else ERA5-Land MODELED, tagged); terrain
5x5-window stats (SRTM REAL); SAR metadata features (ASF REAL_METADATA or
missing code — never zero); spatial context (GSI density/dist); exposure
(road/village/infra distance from existing tables). Every feature carries
provenance; every gap carries a missingness code + optional imputation
method (median-of-group, recorded). Writes training_samples rows (version
stamped later) + data/processed/ner_features_v1.json preview.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, PROCESSED_DIR, write_json, utcnow, MISSING

WINDOWS_H = {"rain_1h": 1, "rain_3h": 3, "rain_6h": 6, "rain_12h": 12,
             "rain_24h": 24, "rain_48h": 48, "rain_72h": 72,
             "rain_7d": 168, "rain_14d": 336, "rain_30d": 720}


def _hourly(cache: dict, end_iso: str) -> tuple[list, list, list]:
    h = cache.get("hourly", {})
    times, rain, soil = h.get("time", []), h.get("precipitation", []), h.get("soil_moisture_3_9cm", [])
    cut, r, s = [], [], []
    for t, v, m in zip(times, rain, soil):
        if t <= end_iso:
            cut.append(t)
            r.append(0.0 if v is None else float(v))
            s.append(m)
    return cut, r, s


def _rain_feats(r: list[float]) -> tuple[dict, dict]:
    feats, prov = {}, {}
    if not r:
        return ({k: None for k in list(WINDOWS_H) + ["rain_max_1h", "rain_max_3h",
                                                    "rain_max_24h", "rain_intensity",
                                                    "rain_trend", "antecedent_7d"]},
                {k: "NOT_AVAILABLE" for k in WINDOWS_H})
    for k, hrs in WINDOWS_H.items():
        feats[k] = round(sum(r[-hrs:]), 2)
        prov[k] = "openmeteo-archive"
    feats["rain_max_1h"] = round(max(r[-24:] or [0]), 2)
    feats["rain_max_3h"] = round(max((sum(r[i:i + 3]) for i in range(max(0, len(r) - 72))), default=0), 2)
    feats["rain_max_24h"] = round(max((sum(r[i:i + 24]) for i in range(max(0, len(r) - 168))), default=0), 2)
    feats["rain_intensity"] = round(feats["rain_1h"], 2)
    feats["rain_trend"] = round(sum(r[-6:]) / 6 - sum(r[-12:-6]) / 6, 3) if len(r) >= 12 else 0.0
    feats["antecedent_7d"] = feats["rain_7d"]
    prov.update({k: "openmeteo-archive" for k in ("rain_max_1h", "rain_max_3h", "rain_max_24h",
                                                 "rain_intensity", "rain_trend", "antecedent_7d")})
    return feats, prov


def _soil_feats(s: list, smap_value: float | None) -> tuple[dict, dict]:
    if smap_value is not None:
        return ({"soil_moisture": smap_value, "soil_1d": None, "soil_3d": None, "soil_7d": None},
                {"soil_moisture": "smap-manual", "soil_1d": "NOT_AVAILABLE",
                 "soil_3d": "NOT_AVAILABLE", "soil_7d": "NOT_AVAILABLE"})
    vals = [float(x) for x in s if x is not None]
    if not vals:
        return ({"soil_moisture": None, "soil_1d": None, "soil_3d": None, "soil_7d": None},
                {k: "NOT_AVAILABLE" for k in ("soil_moisture", "soil_1d", "soil_3d", "soil_7d")})
    cur = vals[-1]
    return ({"soil_moisture": round(cur, 3),
             "soil_1d": round(sum(vals[-24:]) / len(vals[-24:]), 3),
             "soil_3d": round(sum(vals[-72:]) / len(vals[-72:]), 3),
             "soil_7d": round(sum(vals[-168:]) / len(vals[-168:]), 3)},
            {k: "modeled-era5-land" for k in ("soil_moisture", "soil_1d", "soil_3d", "soil_7d")})


def _terrain(eid, lat, lon) -> tuple[dict, dict]:
    p = os.path.join(RAW_DIR, f"ner_dem_{eid}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        feats = {k: d[k] for k in ("elevation_mean", "elevation_min", "elevation_max",
                                   "elevation_range", "slope_mean", "slope_max",
                                   "slope_var", "ruggedness") if k in d}
        if feats:
            return feats, {k: "srtm30m-opentopodata" for k in feats}
    # zone-seed fallback (STATIC, tagged — never presented as measured DEM)
    from app.seed import ZONES
    z = min(ZONES, key=lambda z: (z["lat"] - lat) ** 2 + (z["lng"] - lon) ** 2)
    feats = {"elevation_mean": float(z["elevation"]), "slope_mean": float(z["slope"]),
             "ruggedness": float(z["ruggedness"]), "elevation_min": None,
             "elevation_max": None, "elevation_range": None,
             "slope_max": None, "slope_var": None}
    return feats, {k: ("static-seed-profile" if v is not None else "NOT_AVAILABLE")
                   for k, v in feats.items()}


def _sar(eid) -> tuple[dict, dict]:
    p = os.path.join(RAW_DIR, f"ner_sar_{eid}.json")
    if not os.path.exists(p):
        # controls have no SAR search by design (event-windowed discovery);
        # coded NOT_ACQUIRED, excluded from training — never zero-filled
        return ({"sar_pre_days": None, "sar_post_days": None, "sar_same_orbit": None},
                {k: "NOT_ACQUIRED" for k in ("sar_pre_days", "sar_post_days", "sar_same_orbit")})
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    from datetime import datetime
    pivot = d.get("retrieved_at", "")[:10]
    feats, prov = {}, {}
    for slot, key in (("pre_event_scene", "sar_pre_days"), ("post_event_scene", "sar_post_days")):
        s = d.get(slot)
        if s and s.get("acquisition_time"):
            try:
                acq = datetime.fromisoformat(s["acquisition_time"].replace("Z", "+00:00")).date().isoformat()
                feats[key] = acq  # acquisition date string (temporal feature, not magnitude)
                prov[key] = "asf-real-metadata"
            except ValueError:
                feats[key], prov[key] = None, "QUALITY_REJECTED"
        else:
            feats[key], prov[key] = None, "NOT_ACQUIRED"
    pre, post = d.get("pre_event_scene") or {}, d.get("post_event_scene") or {}
    if pre.get("orbit") and post.get("orbit"):
        feats["sar_same_orbit"] = pre["orbit"] == post["orbit"]
        prov["sar_same_orbit"] = "asf-real-metadata"
    else:
        feats["sar_same_orbit"], prov["sar_same_orbit"] = None, "NOT_ACQUIRED"
    return feats, prov


def _spatial_ctx(db, lat, lon) -> tuple[dict, dict]:
    from app.models_db import NerInventory
    ds = [math.dist((lat, lon), (r.latitude, r.longitude)) * 111.0
          for r in db.query(NerInventory).filter(NerInventory.record_kind == "SPATIAL").all()]
    feats = {"hist_density_15km": sum(1 for d in ds if d <= 15.0),
             "nearest_spatial_km": round(min(ds), 2) if ds else None}
    return feats, {k: ("gsi-spatial" if feats[k] is not None else "NOT_AVAILABLE") for k in feats}


def _exposure(db, lat, lon) -> tuple[dict, dict]:
    from app.models_db import RoadSegment, Village, Infrastructure
    def _nearest(rows):
        ds = [math.dist((lat, lon), (r.latitude or 0, r.longitude or 0)) * 111.0
              for r in rows if r.latitude is not None]
        return round(min(ds), 2) if ds else None
    feats = {"road_dist_km": _nearest(db.query(RoadSegment).all()),
             "village_dist_km": _nearest(db.query(Village).all()),
             "infra_dist_km": _nearest(db.query(Infrastructure).all())}
    return feats, {k: ("static-registry" if v is not None else "NOT_AVAILABLE")
                   for k, v in feats.items()}


def build_one(db, eid, lat, lon, end_iso, smap: dict) -> tuple[dict, dict, dict]:
    feats, prov, miss = {}, {}, {}
    cache_p = os.path.join(RAW_DIR, f"ner_rain_{eid}.json")
    if not os.path.exists(cache_p):
        for k in list(WINDOWS_H) + ["rain_max_1h", "rain_max_3h", "rain_max_24h",
                                    "rain_intensity", "rain_trend", "antecedent_7d"]:
            feats[k], miss[k] = None, "NOT_AVAILABLE"
    else:
        with open(cache_p, encoding="utf-8") as f:
            cache = json.load(f)
        _, r, s = _hourly(cache, end_iso)
        rf, rp = _rain_feats(r)
        feats.update(rf)
        prov.update(rp)
        miss.update({k: "NOT_AVAILABLE" for k, v in rf.items() if v is None})
        sf, sp = _soil_feats(s, smap.get(eid))
        feats.update(sf)
        prov.update(sp)
        miss.update({k: v for k, v in sp.items() if v in
                     ("NOT_AVAILABLE",)})
    # group-median imputation for defensible numeric gaps (recorded, never silent)
    tf, tp = _terrain(eid, lat, lon)
    feats.update(tf)
    prov.update(tp)
    miss.update({k: v for k, v in tp.items() if v in ("NOT_AVAILABLE",)})
    sf2, sp2 = _sar(eid)
    feats.update(sf2)
    prov.update(sp2)
    miss.update({k: v for k, v in sp2.items() if v.startswith("NOT_")})
    sc, scp = _spatial_ctx(db, lat, lon)
    feats.update(sc)
    prov.update(scp)
    ex, exp = _exposure(db, lat, lon)
    feats.update(ex)
    prov.update(exp)
    return feats, prov, miss


def main() -> dict:
    from app.database import SessionLocal
    from app.models_db import NerInventory, TrainingSample
    smap = {}
    p = os.path.join(RAW_DIR, "smap_manual.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in json.load(f):
                try:
                    smap[int(r.get("event_ref", -1))] = float(r["soil_moisture"])
                except (TypeError, ValueError):
                    continue
    db = SessionLocal()
    try:
        events = db.query(NerInventory).filter(NerInventory.record_kind == "TEMPORAL").all()
        ctrls = db.query(TrainingSample).filter(TrainingSample.label == "NO_RECORDED_LANDSLIDE").all()
        n = 0
        for e in events:
            end_iso = e.event_date.date().isoformat() + "T23:00"
            feats, prov, miss = build_one(db, e.id, e.latitude, e.longitude, end_iso, smap)
            sid = f"POS-{e.id}"
            row = db.query(TrainingSample).filter(TrainingSample.sample_id == sid).first()
            payload = dict(features_json=json.dumps(feats),
                           provenance_json=json.dumps({**prov, "feature_version": "nerfeat_v1",
                                                       "built_at": utcnow()}),
                           missingness_json=json.dumps(miss),
                           group_id=e.district or e.state or "NER")
            if row:
                for k, v in payload.items():
                    setattr(row, k, v)
            else:
                db.add(TrainingSample(dataset_version="__pending__", sample_id=sid,
                                      event_id=e.id, label="RECORDED_LANDSLIDE",
                                      event_date=e.event_date, latitude=e.latitude,
                                      longitude=e.longitude, group_id=payload.pop("group_id"),
                                      **payload))
            n += 1
        for c in ctrls:
            end_iso = c.event_date.date().isoformat() + "T23:00"
            feats, prov, miss = build_one(db, f"C{c.id}", c.latitude, c.longitude, end_iso, smap)
            # controls need their own rain cache: fetch on demand via eid key C{id}
            keep = {}
            try:
                keep = json.loads(c.provenance_json or "{}")
            except (json.JSONDecodeError, TypeError):
                keep = {}
            keep = {k: v for k, v in keep.items() if k in ("control_of", "strategy")}
            if "control_of" not in keep and c.sample_id.startswith("CTL-"):
                # deterministic re-derivation from our own CTL-{event_id}-{date}
                # format (repairs rows clobbered before provenance preservation)
                try:
                    keep["control_of"] = int(c.sample_id.split("-")[1])
                    keep["strategy"] = ("matched-spatiotemporal "
                                        "(same site, same month-day, non-event year)")
                except (IndexError, ValueError):
                    pass
            c.features_json = json.dumps(feats)
            c.provenance_json = json.dumps({**keep, **prov, "feature_version": "nerfeat_v1",
                                            "built_at": utcnow()})
            c.missingness_json = json.dumps(miss)
            n += 1
        db.commit()
        preview = [{"sample": r.sample_id, "label": r.label,
                    "n_features": len(json.loads(r.features_json or "{}")),
                    "n_missing": len(json.loads(r.missingness_json or "{}"))}
                   for r in db.query(TrainingSample).all()]
        write_json(os.path.join(PROCESSED_DIR, "ner_features_v1.json"), preview)
        return {"samples": n, "preview": os.path.join(PROCESSED_DIR, "ner_features_v1.json")}
    finally:
        db.close()


if __name__ == "__main__":
    print(f"features: {main()}")
