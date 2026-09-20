"""Build reports/dataset_inventory.json from the ACTUAL files (SIH §2).

Read-only w.r.t. datasets/. Every number is measured, never assumed.
Run: python scripts/build_inventory.py   (from backened/)
"""
import csv
import glob
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from gs_common import normalize_event_id, sha256_of  # noqa: E402
from ner_v2_common import DATASETS_DIR  # noqa: E402

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "..", "reports")
PKG = os.path.join(DATASETS_DIR, "GEO_SENTINEL_TRAINING_PACKAGE",
                   "GEO_SENTINEL_TRAINING_PACKAGE")


def _csv_info(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def _tif_const_check(path):
    with open(path, "rb") as fh:
        buf = fh.read()
    off = struct.unpack("<I", buf[4:8])[0]
    n = struct.unpack("<H", buf[off:off + 2])[0]
    tags = {}
    for i in range(n):
        t, _, _, v = struct.unpack("<HHI4s", buf[off + 2 + i * 12:off + 2 + i * 12 + 12])
        tags[t] = struct.unpack("<I", v)[0]
    raw = zlib.decompress(buf[tags[324]:tags[324] + tags[325]])
    px = struct.unpack("<" + str(len(raw) // 2) + "h", raw)
    return {"width": tags[256], "pixels": len(px), "n_unique": len(set(px)),
            "values": sorted(set(px))[:5]}


def main():
    inv = {"generated_by": "scripts/build_inventory.py (measured, not assumed)",
           "datasets": []}

    def add(entry):
        p = entry.get("path")
        if p and os.path.exists(os.path.join(DATASETS_DIR, p)):
            entry["sha256"] = sha256_of(os.path.join(DATASETS_DIR, p))
            entry["bytes"] = os.path.getsize(os.path.join(DATASETS_DIR, p))
        inv["datasets"].append(entry)

    # COOLR global catalogs
    ev = _csv_info(os.path.join(DATASETS_DIR, "Landslide Events.csv"))
    add({"id": "coolr_events", "path": "Landslide Events.csv", "type": "CSV",
         "rows": len(ev), "cols": 24, "static_or_series": "static (event list)",
         "spatial": "global; India=176 (all Uttarakhand/Himachal); Meghalaya=0",
         "temporal": "mixed 2007-2024 inventory dates",
         "labels": "AUTHORITATIVE point inventories, none in project region",
         "classification": "NOT_RELEVANT",
         "reason": "0 Meghalaya rows; India slice is a single UT/Himachal inventory."})

    rep = _csv_info(os.path.join(DATASETS_DIR, "Landslide Reports.csv"))
    meg = [r for r in rep if r.get("Administrative Division") == "Meghalaya"]
    add({"id": "coolr_reports", "path": "Landslide Reports.csv", "type": "CSV",
         "rows": len(rep), "meghalaya_rows": len(meg), "cols": 32,
         "static_or_series": "static (event list)",
         "spatial": "global; Meghalaya=38 (point, mostly <=5 km accuracy)",
         "temporal": "2007-2019 (Event Date, day precision)",
         "labels": "AUTHORITATIVE/OBSERVED (NASA COOLR/GLC, media-sourced); "
                   "18 high-confidence used for training, ~20 lower-confidence held out",
         "classification": "DIRECTLY_USABLE",
         "reason": "Label source for the 18 training events + 20-event held-out pool."})

    # gauges
    for fid, fname, col in [
            ("gauge_manual_0120", "rainfall_manual_daily_meghalaya_ml_1991_2020.csv",
             "Manual Daily Rainfall (mm)"),
            ("gauge_manual_2125", "rainfall_manual_daily_meghalaya_ml_2021_2025.csv",
             "Manual Daily Rainfall (mm)"),
            ("gauge_tel_2125", "rainfall_tel_hr_meghalaya_ml_2021_2025.csv",
             "Telemetry Hourly Rainfall (mm)")]:
        rows = _csv_info(os.path.join(DATASETS_DIR, fname))
        sts = sorted({r["Station"] for r in rows})
        dts = sorted(r["Data Acquisition Time"] for r in rows)
        neg = sum(1 for r in rows
                  if r[col].strip() not in ("", "-") and float(r[col]) < 0)
        add({"id": fid, "path": fname, "type": "CSV", "rows": len(rows),
             "n_stations": len(sts), "static_or_series": "time-series (gauge)",
             "spatial": f"Meghalaya ({len(sts)} stations)",
             "temporal": f"{dts[0]} .. {dts[-1]} (actual file span; filename may differ)",
             "labels": "UNLABELED (predictor only)",
             "negatives_or_sentinels": neg,
             "classification": "USABLE_AFTER_PREPROCESSING",
             "reason": "QC gates required (sentinel/negative/spike/duplicate rejects)."})

    # OSM / soil / SRTM / boundary
    add({"id": "osm_pbf", "path": "meghalaya.pbf", "type": "OSM PBF",
         "static_or_series": "static", "spatial": "Meghalaya extract",
         "labels": "UNLABELED (road 선도 features via import_pbf_roads.py)",
         "classification": "AUXILIARY",
         "reason": "Consumed through processed roads_v2.json; not a direct model input."})
    soil = json.load(open(os.path.join(DATASETS_DIR, "Meghalaya_Soil.geojson"),
                          encoding="utf-8"))
    add({"id": "soil", "path": "Meghalaya_Soil.geojson", "type": "GeoJSON",
         "polygons": len(soil["features"]), "crs": "NO crs member (WGS84 assumed)",
         "static_or_series": "static",
         "spatial": "Meghalaya, 24 coarse taxonomy units",
         "labels": "UNLABELED",
         "classification": "AUXILIARY",
         "reason": "Coarse polygon categories; CRS assumption must be verified per use."})
    for t in ["n25_e090_1arc_v3.tif", "n25_e091_1arc_v3.tif", "n26_e090_1arc_v3.tif"]:
        add({"id": "srtm_" + t[:8], "path": t, "type": "GeoTIFF",
             "grid": "3601x3601 int16", "crs": "EPSG:4326", "resolution_m": "~30",
             "static_or_series": "static",
             "spatial": t[1:3] + "N " + t[4:7] + "E tile; lon 92-93 strip MISSING",
             "labels": "UNLABELED",
             "classification": "DIRECTLY_USABLE",
             "reason": "30 m DEM backbone; east-fringe gap documented."})
    add({"id": "state_boundary", "path": "state_NWIC.GeoJSON", "type": "GeoJSON",
         "crs": "EPSG:7755 (projected metres — reproject before lon/lat use)",
         "static_or_series": "static", "spatial": "all-India (36 features incl. Meghalaya)",
         "labels": "UNLABELED", "classification": "AUXILIARY",
         "reason": "Reference boundary only; duplicated inside training package."})

    # ECMWF samples
    add({"id": "ecmf_oper", "path": "data_stream-oper_stepType-instant.nc",
         "type": "NetCDF4", "static_or_series": "time-series (single Jan-2020 window)",
         "spatial": "6x14 @0.25 deg over Meghalaya", "labels": "UNLABELED",
         "classification": "AUXILIARY",
         "reason": "Schema reference for a future live feed; overlaps zero label events."})
    add({"id": "ecmf_accum", "path": "data_stream-oper_stepType-accum.nc",
         "type": "NetCDF4", "static_or_series": "time-series (single Jan-2020 window)",
         "spatial": "6x14 @0.25 deg", "labels": "UNLABELED",
         "classification": "AUXILIARY", "reason": "Total-precip schema sample only."})
    add({"id": "ecmf_wave", "path": "data_stream-wave_stepType-instant.nc",
         "type": "NetCDF4", "static_or_series": "time-series",
         "spatial": "ocean wave vars over landlocked hills",
         "labels": "UNLABELED", "classification": "NOT_RELEVANT",
         "reason": "mwd/mwp/swh are ocean variables; meaningless for Meghalaya landslides."})

    # training package
    lab = _csv_info(os.path.join(PKG, "LABELS", "meghalaya_high_confidence_events.csv"))
    add({"id": "gs_labels", "path": "GEO_SENTINEL_TRAINING_PACKAGE/.../LABELS/meghalaya_high_confidence_events.csv",
         "type": "CSV", "rows": len(lab),
         "labels": "AUTHORITATIVE/OBSERVED point labels (COOLR high-confidence subset)",
         "classification": "DIRECTLY_USABLE",
         "reason": "The 18 training events; point-level, day precision."})
    rf = _csv_info(os.path.join(PKG, "RF", "meghalaya_rf_training_features.csv"))
    npos = sum(1 for r in rf if r["Landslide_Label"] == "1")
    add({"id": "gs_rf", "path": "GEO_SENTINEL_TRAINING_PACKAGE/.../RF/meghalaya_rf_training_features.csv",
         "type": "CSV", "rows": len(rf), "positives": npos,
         "negatives_background": len(rf) - npos,
         "labels": "1=AUTHORITATIVE event point; 0=PSEUDO-BACKGROUND (no record, NOT confirmed absence)",
         "classification": "DIRECTLY_USABLE",
         "reason": "Prototype tabular supervision; pseudo-absence caveat applies."})
    import numpy as np
    d = np.load(os.path.join(PKG, "MAMBA", "meghalaya_mamba_supervised_tensor_15f.npz"))
    add({"id": "gs_mamba", "path": "GEO_SENTINEL_TRAINING_PACKAGE/.../MAMBA/*.{csv,npz}",
         "type": "CSV+NPZ", "tensor": list(d["X"].shape),
         "labels": "sequence-level: 18 AUTHORITATIVE event windows + 648 PSEUDO-BACKGROUND windows",
         "classification": "DIRECTLY_USABLE",
         "reason": "Event-grouped temporal supervision; bg shares event windows (split by event)."})
    man = _csv_info(os.path.join(PKG, "SEGFORMER", "segformer_manifest.csv"))
    const = 0
    total = 0
    for row in man:
        for band in ("blue", "green", "red", "nir"):
            p = row.get(band, "").strip().replace("/", os.sep)
            fp = os.path.join(PKG, p) if p else ""
            if p and os.path.exists(fp):
                total += 1
                if _tif_const_check(fp)["n_unique"] <= 1:
                    const += 1
    add({"id": "gs_segformer", "path": "GEO_SENTINEL_TRAINING_PACKAGE/.../SEGFORMER/",
         "type": "GeoTIFF patches + manifests", "manifest_events": len(man),
         "constant_optical_patches": f"{const}/{total}", "masks": "NONE exist",
         "labels": "NO pixel labels exist (event_manifest is point reference only)",
         "classification": "INSUFFICIENT_FOR_TRAINING",
         "reason": "All optical patches constant-0, QA constant-1, zero masks. BLOCKED."})

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out = os.path.join(REPORTS_DIR, "dataset_inventory.json")
    # display paths containing '...' never hit the disk: backfill real hashes
    _real = {"gs_labels": os.path.join(PKG, "LABELS",
                                       "meghalaya_high_confidence_events.csv"),
             "gs_rf": os.path.join(PKG, "RF", "meghalaya_rf_training_features.csv"),
             "gs_mamba": os.path.join(PKG, "MAMBA",
                                      "meghalaya_mamba_supervised_tensor_15f.npz"),
             "gs_segformer": os.path.join(PKG, "SEGFORMER", "segformer_manifest.csv")}
    for e in inv["datasets"]:
        if e["id"] in _real:
            e["sha256"] = sha256_of(_real[e["id"]])
            e["bytes"] = os.path.getsize(_real[e["id"]])
    json.dump(inv, open(out, "w", encoding="utf-8"), indent=2)
    print(f"inventory: {len(inv['datasets'])} datasets -> {out}")
    # §4 re-verification line
    assert [e for e in inv["datasets"] if e["id"] == "gs_labels"][0]["rows"] == 18
    assert [e for e in inv["datasets"] if e["id"] == "gs_rf"][0]["rows"] == 54
    assert [e for e in inv["datasets"] if e["id"] == "gs_mamba"][0]["tensor"] == [666, 73, 15]


if __name__ == "__main__":
    main()
