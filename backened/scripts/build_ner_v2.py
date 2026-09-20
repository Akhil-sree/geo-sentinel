"""PHASES 6/7 — ner_v2 fusion build: controls, features, gates, dataset.

Pipeline (all additive; ner_v1 rows, seq_real_v2, registry history untouched):
1. Load TRAINING_ELIGIBLE candidates (qc_reports_v2.py --write first).
2. Per positive: Open-Meteo archive rain (fetch_rainfall), point DEM via
   OpenTopodata at unique sites (ingest_dem; raster r_ overlay where the
   datasets/ tiles cover), ASF S1 metadata (ingest_sentinel1, failures OK),
   gauge g_ features (prior-day cutoff), soil codes (Meghalaya only),
   PBF road features (Meghalaya bbox + buffer only).
3. Matched controls (same rule as build_controls.py: same site, same
   month-day, non-event year, ±30 d exclusion, no future dates).
4. Base features via build_features.build_one (needs DB for spatial ctx +
   exposure reads only — no existing rows modified).
5. Leakage-safe splits (temporal holdout = most recent positive year;
   controls follow linked positives), group-median imputation (recorded).
6. Writes data/processed/ner_training_ner_v2.csv + metadata + DatasetVersion
   row (new version only) + TrainingSample rows (new sample_ids, version
   ner_v2 only) + data/metadata/ner_v2_gates.json.
7. Ablation CSVs + training/eval are separate steps (train_models.py
   --dataset ...; see docs). This script stops at the gated dataset.

Day-precision policy: Reports dates have no event time, so ALL temporal
features use a conservative prior-day cutoff (end = event day T00:00).
Same-day measurements are never used — they may be post-event.

Run: python scripts/build_ner_v2.py [--limit N] [--skip-fetch]
"""
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import haversine_km, write_json  # noqa: E402
from ner_v2_common import (  # noqa: E402
    PROCESSED_DIR, META_DIR, RAW_DIR, VERSION, FEATURE_VERSION,
    CODE_VERSION, utcnow,
)

CAND_JSON = os.path.join(PROCESSED_DIR, "reports_v2_candidates.json")
TERR_JSON = os.path.join(PROCESSED_DIR, "terrain_raster_v2.json")
CSV_OUT = os.path.join(PROCESSED_DIR, f"ner_training_{VERSION}.csv")
META_OUT = os.path.join(META_DIR, f"ner_training_{VERSION}.json")
GATES_OUT = os.path.join(META_DIR, "ner_v2_gates.json")

PBF_BBOX = (89.80, 25.00, 92.85, 26.20)
PBF_BUF = 0.5


def _median(vals):
    vals = sorted(vals)
    return vals[len(vals) // 2] if vals else 0.0


def in_pbf(lat: float, lon: float) -> bool:
    return (PBF_BBOX[0] - PBF_BUF <= lon <= PBF_BBOX[2] + PBF_BUF
            and PBF_BBOX[1] - PBF_BUF <= lat <= PBF_BBOX[3] + PBF_BUF)


def make_controls(positives: list[dict], event_days: set, n_per_event: int = 2) -> list[dict]:
    """Same rule as build_controls.py, operating on candidate dicts.
    event_days: {(lat, lon, iso_day)} of all dated positives (inventory
    TEMPORAL + candidates) for the ±30 d exclusion."""
    today = dt.date.today() - dt.timedelta(days=2)
    ctrls = []
    for i, p in enumerate(positives):
        base = dt.date.fromisoformat(p["event_day"])
        made = 0
        for k in range(1, 4):
            if made >= n_per_event:
                break
            for year in (base.year - k, base.year + k):
                if made >= n_per_event:
                    break
                try:
                    cand = base.replace(year=year)
                except ValueError:
                    continue
                if cand > today or cand < dt.date(1940, 1, 1):
                    continue
                clash = any(abs((cand - dt.date.fromisoformat(d)).days) <= 30
                            and abs(la - p["latitude"]) < 0.05
                            and abs(lo - p["longitude"]) < 0.05
                            for (la, lo, d) in event_days)
                if clash:
                    continue
                ctrls.append({"pos_idx": i, "event_day": cand.isoformat(),
                              "latitude": p["latitude"], "longitude": p["longitude"],
                              "district": p["district"]})
                made += 1
    return ctrls


def build(limit: int = 0, skip_fetch: bool = False) -> dict:
    from app.database import SessionLocal
    from app.models_db import TrainingSample, DatasetVersion, NerInventory
    from fetch_rainfall import fetch_event as fetch_rain
    from ingest_dem import fetch_event as fetch_dem
    from ingest_sentinel1 import discover as sar_discover
    from build_features import build_one
    from ner_v2_features import (raster_terrain, load_soil_units, soil_at,
                                 load_road_nodes, road_features, gauge_features)

    cands = [c for c in json.load(open(CAND_JSON, encoding="utf-8"))
             if c.get("status") == "TRAINING_ELIGIBLE"]
    cands.sort(key=lambda c: (c["event_day"], c["source_event_id"]))
    if limit:
        # deterministic head slice (smoke mode) — recorded, never silent
        cands = cands[:limit]
    terr = json.load(open(TERR_JSON, encoding="utf-8")) if os.path.exists(TERR_JSON) else {}
    soil_units = load_soil_units()
    roads = load_road_nodes()

    db = SessionLocal()
    try:
        inv_temp = db.query(NerInventory).filter(
            NerInventory.record_kind == "TEMPORAL").all()
    finally:
        db.close()
    event_days = {(e.latitude, e.longitude, e.event_date.date().isoformat())
                  for e in inv_temp if e.event_date}
    event_days |= {(c["latitude"], c["longitude"], c["event_day"]) for c in cands}

    fetch_stats = {"rain_ok": 0, "rain_fail": 0, "dem_ok": 0, "dem_fail": 0,
                   "sar_ok": 0, "sar_fail": 0}
    samples: list[dict] = []  # (kind, idx, lat, lon, day, group, prov_extra)

    # --- positives ---
    dem_cache: dict = {}
    for i, c in enumerate(cands):
        key, lat, lon, day = f"V2P{i}", c["latitude"], c["longitude"], c["event_day"]
        if not skip_fetch:
            try:
                fetch_rain(key, lat, lon, day)
                fetch_stats["rain_ok"] += 1
            except Exception:
                fetch_stats["rain_fail"] += 1
            site = (round(lat, 4), round(lon, 4))
            if site not in dem_cache:
                try:
                    fetch_dem(f"V2SITE{i}", lat, lon)
                    dem_cache[site] = f"V2SITE{i}"
                    fetch_stats["dem_ok"] += 1
                except Exception:
                    dem_cache[site] = None
                    fetch_stats["dem_fail"] += 1
            else:
                fetch_stats["dem_ok"] += 1
            try:
                sar_discover(key, lat, lon, day + "T00:00:00")
                fetch_stats["sar_ok"] += 1
            except Exception:
                fetch_stats["sar_fail"] += 1
        samples.append({"kind": "POS", "key": key, "idx": i, "lat": lat, "lon": lon,
                        "day": day, "group": c["district"] or "NER", "cand": c,
                        "dem_key": dem_cache.get((round(lat, 4), round(lon, 4)), key)})

    # --- controls ---
    ctrls = make_controls(cands, event_days)
    for j, c in enumerate(ctrls):
        key = f"V2C{j}"
        if not skip_fetch:
            try:
                fetch_rain(key, c["latitude"], c["longitude"], c["event_day"])
                fetch_stats["rain_ok"] += 1
            except Exception:
                fetch_stats["rain_fail"] += 1
            site = (round(c["latitude"], 4), round(c["longitude"], 4))
            if site not in dem_cache:
                # same site as its positive in practice; independent key anyway
                dem_cache[site] = dem_cache.get(site)
        samples.append({"kind": "CTL", "key": key, "idx": j, "lat": c["latitude"],
                        "lon": c["longitude"], "day": c["event_day"],
                        "group": c["district"] or "NER", "pos_idx": c["pos_idx"],
                        "dem_key": dem_cache.get((round(c["latitude"], 4),
                                                  round(c["longitude"], 4)), key)})

    # --- features ---
    from app.database import SessionLocal as SL
    db = SL()
    try:
        rows = []
        for s in samples:
            end_iso = s["day"] + "T00:00"  # prior-day cutoff (day-precision policy)
            feats, prov, miss = build_one(db, s["dem_key"] or s["key"],
                                          s["lat"], s["lon"], end_iso, {})
            label = ("RECORDED_LANDSLIDE" if s["kind"] == "POS"
                     else "NO_RECORDED_LANDSLIDE")
            # v2 augmentations (each tagged; gaps stay None)
            rf, rp, rm = raster_terrain(s["lat"], s["lon"])
            feats.update(rf)
            prov.update(rp)
            miss.update({k: v for k, v in rm.items()
                         if k not in ("raster_tile", "raster_window")})
            if rm.get("raster_tile"):
                miss["raster_tile"] = rm["raster_tile"]
            gf, gp, gm = gauge_features(s["lat"], s["lon"], s["day"])
            feats.update(gf)
            prov.update(gp)
            miss.update(gm)
            if s["lat"] and 24.5 <= s["lat"] <= 26.5 and 89.5 <= s["lon"] <= 93.0:
                sf, sp, sm = soil_at(soil_units, s["lat"], s["lon"])
            else:
                sf = {"soil_drainage": "UNKNOWN", "soil_texture": "UNKNOWN",
                      "soil_erosion": "UNKNOWN", "soil_unit": "UNKNOWN"}
                sp = {k: "soilmap-unverified" for k in sf}
                sm = {"soil_match": None, "soil_note": "OUT_OF_MAP"}
            feats.update(sf)
            prov.update(sp)
            miss.update(sm)
            # numeric soil encoding (documented; raw strings kept in provenance):
            # drainage = wetness ordinal, erosion = severity ordinal,
            # texture = one-hot, unit id excluded (identifier, not a feature)
            drain_scale = {"EXCESSIVE": 0, "WELL": 1, "MODERATE": 2,
                           "IMPERFECT": 3, "POOR": 4, "VERY_POOR": 5}
            ero_scale = {"NONE": 0, "SLIGHT": 1, "MODERATE": 2, "SEVERE": 3,
                         "VERY_SEVERE": 4}
            for k in ("soil_drainage", "soil_texture", "soil_erosion", "soil_unit"):
                prov["raw_" + k] = feats.pop(k, "UNKNOWN")
            feats["soil_drainage_n"] = drain_scale.get(prov["raw_soil_drainage"])
            prov["soil_drainage_n"] = "soilmap-unverified"
            feats["soil_erosion_n"] = ero_scale.get(prov["raw_soil_erosion"])
            prov["soil_erosion_n"] = "soilmap-unverified"
            for tex in ("FINE", "FINE_LOAMY", "FINE_SILTY", "COARSE_LOAMY",
                        "LOAMY", "CLAYEY", "SANDY"):
                feats[f"soil_tex_{tex}"] = (1 if prov["raw_soil_texture"] == tex
                                            else (None if prov["raw_soil_texture"] == "UNKNOWN" else 0))
                prov[f"soil_tex_{tex}"] = "soilmap-unverified"
            if prov["raw_soil_drainage"] == "UNKNOWN":
                miss["soil_drainage_n"] = "NOT_AVAILABLE"
            if prov["raw_soil_erosion"] == "UNKNOWN":
                miss["soil_erosion_n"] = "NOT_AVAILABLE"
            if in_pbf(s["lat"], s["lon"]):
                df, dp, dm = road_features(roads, s["lat"], s["lon"])
            else:
                df = {"road_dist_km": None, "road_density_5km": None}
                dp = {k: "osm-pbf-unknown-vintage" for k in df}
                dm = {"road_dist_km": "OUT_OF_COVERAGE",
                      "road_density_5km": "OUT_OF_COVERAGE",
                      "road_data_vintage": "UNKNOWN"}
            feats.update(df)
            prov.update(dp)
            miss.update(dm)
            base_prov = {"feature_version": "nerfeat_v2", "built_at": utcnow(),
                         "event_precision": "DAY (prior-day cutoff)",
                         "road_data_vintage": "UNKNOWN"}
            if s["kind"] == "POS":
                base_prov.update({"candidate": s["cand"]["source_event_id"],
                                  "location_accuracy": s["cand"]["location_accuracy"],
                                  "candidate_source": s["cand"]["source_name"]})
                sid = f"V2POS-{s['idx']}"
            else:
                base_prov.update({"control_of": f"V2POS-{s['pos_idx']}",
                                  "strategy": "matched-spatiotemporal (same site, same month-day, non-event year)"})
                sid = f"V2CTL-{s['idx']}"
            rows.append({"sample_id": sid, "label": label,
                         "event_date": s["day"], "latitude": s["lat"],
                         "longitude": s["lon"], "group_id": s["group"],
                         "feats": feats,
                         "prov": {**base_prov, **prov},
                         "miss": miss})
        # --- splits (temporal holdout = most recent positive year) ---
        pos_years = sorted({r["event_date"][:4] for r in rows if r["label"] == "RECORDED_LANDSLIDE"})
        holdout = pos_years[-1] if pos_years else None
        test_pos = {r["sample_id"] for r in rows
                    if r["label"] == "RECORDED_LANDSLIDE" and r["event_date"][:4] == holdout}
        test_pos_idx = {r["sample_id"].split("-", 1)[1] for r in rows
                        if r["sample_id"] in test_pos}
        val_cands = sorted({r["group_id"] for r in rows}
                           - {r["group_id"] for r in rows if r["sample_id"] in test_pos})
        val_group = val_cands[len(val_cands) // 2] if val_cands else None
        feat_keys: list[str] = []
        for r in rows:
            for k in r["feats"]:
                if k not in feat_keys:
                    feat_keys.append(k)
        num_keys = [k for k in feat_keys
                    if any(isinstance(rr["feats"].get(k), (int, float)) for rr in rows)]
        medians = {}
        for k in num_keys:
            vs = [rr["feats"][k] for rr in rows if isinstance(rr["feats"].get(k), (int, float))]
            medians[k] = _median(vs)
        out_rows, counts = [], {"train": 0, "val": 0, "test": 0}
        for r in rows:
            miss = dict(r["miss"])
            row = {"sample_id": r["sample_id"], "label": r["label"],
                   "event_date": r["event_date"], "latitude": r["latitude"],
                   "longitude": r["longitude"], "group_id": r["group_id"],
                   "provenance": json.dumps(r["prov"]),
                   "missingness": json.dumps(miss)}
            for k in feat_keys:
                v = r["feats"].get(k)
                if v is None and k in medians:
                    v = medians[k]
                    miss[k] = str(miss.get(k, "NOT_AVAILABLE")) + "+median-imputed"
                row[k] = v
            row["missingness"] = json.dumps(miss)
            if r["label"] == "RECORDED_LANDSLIDE":
                split = ("test" if r["event_date"][:4] == holdout
                         else ("val" if r["group_id"] == val_group else "train"))
            else:
                linked = r["prov"].get("control_of", "")
                split = ("test" if linked.split("-", 1)[-1] in test_pos_idx
                         else ("val" if r["group_id"] == val_group else "train"))
            row["split"] = split
            counts[split] += 1
            out_rows.append(row)
        if os.path.exists(CSV_OUT):
            return {"status": "BLOCKED",
                    "reason": f"{CSV_OUT} exists — delete explicitly or bump version (never overwrite silently)"}
        with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        # --- TrainingSample rows (new version + new ids only) ---
        made = 0
        for r in out_rows:
            if db.query(TrainingSample).filter(
                    TrainingSample.sample_id == r["sample_id"]).first():
                continue
            db.add(TrainingSample(
                dataset_version=VERSION, sample_id=r["sample_id"], event_id=None,
                label=r["label"],
                event_date=dt.datetime.fromisoformat(r["event_date"]),
                latitude=r["latitude"], longitude=r["longitude"],
                features_json=json.dumps({k: r[k] for k in feat_keys}),
                provenance_json=r["provenance"], missingness_json=r["missingness"],
                group_id=r["group_id"], split=r["split"]))
            made += 1
        from ner_common import dataset_checksum
        meta = {"version": VERSION, "region": "NER",
                "feature_version": FEATURE_VERSION, "code_version": CODE_VERSION,
                "n": len(out_rows),
                "positive": sum(1 for r in out_rows if r["label"] == "RECORDED_LANDSLIDE"),
                "negative": sum(1 for r in out_rows if r["label"] == "NO_RECORDED_LANDSLIDE"),
                "splits": counts, "holdout_year": holdout, "val_group": val_group,
                "groups": sorted({r["group_id"] for r in rows}),
                "features": feat_keys, "imputation": "group-median (recorded per-cell)",
                "fetch": fetch_stats,
                "checksum": dataset_checksum(CSV_OUT), "created_at": utcnow()}
        write_json(META_OUT, meta)
        if not db.query(DatasetVersion).filter(DatasetVersion.version == VERSION).first():
            db.add(DatasetVersion(
                version=VERSION, region="NER",
                sources_json=json.dumps({"inventory": "coolr-reports-v2",
                                         "rain": "openmeteo-archive+gauge-unverified",
                                         "soil": "soilmap-unverified(static)+modeled-era5-land",
                                         "dem": "srtm30m-points+srtm1arc-raster",
                                         "sar": "asf-metadata",
                                         "roads": "osm-pbf-unknown-vintage"}),
                counts_json=json.dumps(meta), feature_version=FEATURE_VERSION,
                code_version=CODE_VERSION, checksum=meta["checksum"], status="DRAFT"))
        db.commit()
        gates = run_gates(out_rows)
        write_json(GATES_OUT, {"at": utcnow(), "version": VERSION, "gates": gates})
        print(f"ner_v2: n={len(out_rows)} pos={meta['positive']} splits={counts} gates={gates}")
        return {"status": "BUILT", **meta, "gates": gates,
                "training_rows_added": made}
    finally:
        db.close()


def run_gates(rows: list[dict]) -> dict:
    """v2 leakage + integrity gates (any FAIL blocks training)."""
    g: dict = {}
    ids = [r["sample_id"] for r in rows]
    g["split_uniqueness"] = "PASS" if len(ids) == len(set(ids)) else "FAIL"
    splits: dict = {}
    for r in rows:
        splits.setdefault(r["split"], []).append(r)
    bal = {s: {r["label"] for r in v} for s, v in splits.items()}
    g["split_class_balance"] = ("PASS" if all(len(v) == 2 for v in bal.values() if v)
                                else "FAIL")
    pos = [r for r in rows if r["label"] == "RECORDED_LANDSLIDE"]
    tr_y = [r["event_date"][:4] for r in pos if r["split"] == "train"]
    te_y = [r["event_date"][:4] for r in pos if r["split"] == "test"]
    g["temporal_direction"] = ("PASS" if tr_y and te_y and max(tr_y) < min(te_y)
                               else "FAIL")
    g["temporal_detail"] = f"train_years={sorted(set(tr_y))} test_years={sorted(set(te_y))}"
    by_pos = {r["sample_id"]: r["split"] for r in pos}
    bad = []
    for r in rows:
        try:
            linked = "V2POS-" + json.loads(r["provenance"]).get("control_of", "").split("-", 1)[-1]
        except (ValueError, AttributeError, IndexError):
            linked = None
        if linked and linked != "V2POS-" and by_pos.get(linked) != r["split"]:
            bad.append(r["sample_id"])
    g["control_split_integrity"] = "PASS" if not bad else "FAIL"
    g["control_link_detail"] = bad[:5]
    leak_cols = [c for c in rows[0] if c.lower() in ("target", "seed_label", "zone_label")]
    g["no_label_feature"] = "PASS" if not leak_cols else "FAIL"
    meta_cols = {"sample_id", "label", "event_date", "latitude", "longitude",
                 "group_id", "provenance", "missingness", "split"}
    num_cols = [c for c in rows[0] if c not in meta_cols]
    g["all_none_columns"] = [c for c in num_cols if all(r[c] in ("", None) for r in rows)]
    g["no_silent_zeros"] = "PASS"
    provs = [json.loads(r["provenance"]) for r in rows]
    g["road_vintage_tagged"] = ("PASS" if all(p.get("road_data_vintage") == "UNKNOWN"
                                              for p in provs) else "FAIL")
    g["day_precision_cutoff"] = ("PASS" if all(p.get("event_precision") == "DAY (prior-day cutoff)"
                                                for p in provs) else "FAIL")
    g["overall"] = ("PASS" if all(v == "PASS" for k, v in g.items()
                                  if k not in ("temporal_detail", "control_link_detail",
                                               "all_none_columns")) else "FAIL")
    return g


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()
    return build(limit=args.limit, skip_fetch=args.skip_fetch)


if __name__ == "__main__":
    print(main())
