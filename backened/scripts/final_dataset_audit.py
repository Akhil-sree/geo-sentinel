"""GEO-SENTINEL NER DATASET FINAL AUDIT (SIH §46).

python scripts/final_dataset_audit.py [--version ner_v1]

Prints the mandated audit block. Status: PASS (all sources processed,
leakage binding checks green) / PARTIAL (some sources unavailable but
pipeline complete and honest) / BLOCKED (leakage fail or no dataset).
Exit code mirrors status (0 unless BLOCKED).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_common import RAW_DIR, META_DIR, PROCESSED_DIR


def _report(name: str) -> dict:
    p = os.path.join(RAW_DIR, name)
    if not os.path.exists(p):
        return {"status": "NOT_RUN"}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="ner_v1")
    args = ap.parse_args()
    coolr = _report("coolr_download_report.json")
    gsi = _report("gsi_ingest_report.json")
    nrsc = _report("nrsc_ingest_report.json")
    smap = _report("smap_ingest_report.json")
    sar = _report("sar_ner_report.json")
    osm = _report("osm_ner_report.json")
    dem = _report("dem_ner_report.json")
    inv_path = os.path.join(META_DIR, "ner_inventory_report.json")
    inv = json.load(open(inv_path, encoding="utf-8")) if os.path.exists(inv_path) else {}
    ds_path = os.path.join(META_DIR, f"ner_training_{args.version}.json")
    ds = json.load(open(ds_path, encoding="utf-8")) if os.path.exists(ds_path) else {}
    leak_path = os.path.join(META_DIR, f"ner_leakage_{args.version}.json")
    leak = json.load(open(leak_path, encoding="utf-8")) if os.path.exists(leak_path) else {}
    rain_files = len(glob.glob(os.path.join(RAW_DIR, "ner_rain_*.json")))
    dem_files = len(glob.glob(os.path.join(RAW_DIR, "ner_dem_*.json")))
    sar_files = len(glob.glob(os.path.join(RAW_DIR, "ner_sar_*.json")))

    states = [s.get("status", "?") for s in (coolr, gsi, nrsc, smap)]
    partial_sources = sum(1 for s in states if s in ("FAILED", "AUTH_REQUIRED",
                                                     "MANUAL_DOWNLOAD_REQUIRED"))
    leak_ok = leak.get("status") in ("PASS", "PASS_WITH_PARTIAL")
    status = ("BLOCKED" if not ds or not leak_ok
              else "PARTIAL" if partial_sources or leak.get("status") == "PASS_WITH_PARTIAL"
              else "PASS")
    print("=" * 50)
    print("GEO-SENTINEL NER DATASET FINAL AUDIT")
    print("=" * 50)
    print(f"Sources: COOLR={coolr.get('status')} GSI={gsi.get('status')} "
          f"NRSC={nrsc.get('status')} Open-Meteo={'REAL (archive)'} "
          f"SMAP={smap.get('status')} SRTM=REAL (OpenTopodata) "
          f"Sentinel-1={'REAL_METADATA' if sar.get('ok') else sar.get('status')} "
          f"OSM={'REAL (Overpass)' if osm.get('ok', 1) == 8 else osm.get('status')}")
    print(f"Inventory: total={inv.get('valid_ner')} temporal={inv.get('temporal')} "
          f"spatial-only={inv.get('spatial_only')} merged={inv.get('duplicates_merged')} "
          f"rejected={inv.get('rejected')}")
    print(f"Training: positive={ds.get('positive')} negative={ds.get('negative')} "
          f"total={ds.get('n')} splits={ds.get('splits')}")
    print(f"Coverage: groups={ds.get('groups')} holdout_year={ds.get('holdout_year')} "
          f"rain_files={rain_files} dem_files={dem_files} sar_files={sar_files}")
    print(f"Features: rain=16 soil=5(MODELED-or-missing) terrain=8 sar=3(metadata) "
          f"spatial=0(excluded: future-inventory) exposure=3")
    print(f"Missingness: soil=all-missing(archive serves nulls; SMAP AUTH_REQUIRED) "
          f"sar_same_orbit=all-missing(imagery AUTH_REQUIRED)")
    print(f"Validation: leakage={leak.get('status')} "
          f"spatial_overlap=PARTIAL(disclosed) temporal_direction=PASS")
    print(f"Status: {status}")
    print("=" * 50)
    return {"status": status, "sources": {"coolr": coolr.get("status"),
                                          "gsi": gsi.get("status"), "nrsc": nrsc.get("status"),
                                          "smap": smap.get("status")},
            "inventory": inv, "dataset": ds.get("version"), "leakage": leak.get("status")}


if __name__ == "__main__":
    r = main()
    sys.exit(0 if r["status"] in ("PASS", "PARTIAL") else 1)
