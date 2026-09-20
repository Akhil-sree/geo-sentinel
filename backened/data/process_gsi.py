"""GSI landslide inventory pipeline (real data, CC0-1.0 via bharatlas).

Source: GSI_Landslide_Inventory.parquet (30,842 pan-India slides), filtered
to STATE=Meghalaya (865 rows, all with coordinates).

Outputs:
  data/raw/gsi_meghalaya.parquet      — verbatim Meghalaya subset (raw kept)
  data/processed/gsi_slides_meghalaya.csv — compact id/lat/lng/district/
      year-or-unknown/trigger/activity
  data/processed/gsi_zone_features.json   — per-zone: slide count within
      15km of centroid + distance to nearest slide (real spatial signal
      for events_v3 features)
  data/metadata/gsi.json                  — source/license/provenance

No dates below year resolution exist in the source (INITIATION=0 means
unknown) — so GSI feeds SPATIAL features + GIS display, never temporal
sequences (documented boundary).
Run: python data/process_gsi.py (needs data/raw/GSI_Landslide_Inventory.parquet;
see SOURCES.md for download URL).
"""
import json
import math
import os
import sys

# Portable source resolution (P2): explicit env override wins, otherwise the
# repo-local raw file. Never a developer-machine absolute path.
SRC = os.getenv(
    "GSI_PARQUET",
    os.path.join(os.path.dirname(__file__), "raw",
                 "GSI_Landslide_Inventory.parquet"),
)
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))

RAW_OUT = os.path.join(HERE, "raw", "gsi_meghalaya.parquet")


def _haversine(lat1, lng1, lat2, lng2):
    d1, d2 = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = (math.sin(d1 / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(d2 / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def main():
    import pandas as pd
    from app.seed import ZONES
    df = pd.read_parquet(SRC)
    ml = df[df["STATE"].str.upper().str.contains("MEGHALAYA", na=False)].copy()
    assert len(ml) > 0 and ml[["LATITUDE", "LONGITUDE"]].notnull().all().all()
    ml.to_parquet(RAW_OUT)
    comp = pd.DataFrame({
        "slide_id": ml["OBJECTID"].astype(int),
        "lat": ml["LATITUDE"].astype(float), "lng": ml["LONGITUDE"].astype(float),
        "district": ml["DISTRICT"].fillna("").astype(str),
        "year": ml["INITIATION"].astype(int),
        "trigger": ml["TRIGGERING"].fillna("").astype(str),
        "activity": ml["ACTIVITY"].fillna("").astype(str)})
    comp.to_csv(os.path.join(HERE, "processed", "gsi_slides_meghalaya.csv"),
                index=False)
    zf = {}
    for z in ZONES:
        d = [_haversine(z["lat"], z["lng"], r.lat, r.lng)
             for r in comp.itertuples()]
        zf[z["id"]] = {"gsi_count_15km": sum(1 for x in d if x <= 15.0),
                       "gsi_dist_km": round(min(d), 2)}
    json.dump(zf, open(os.path.join(HERE, "processed",
                                    "gsi_zone_features.json"), "w"), indent=1)
    meta = {"source_name": "GSI landslide inventory via bharatlas",
            "source_url": ("https://bharatlas.com/view/gsi_landslide_inventory "
                           "(parquet mirror of GSI NGDR/Bhukosh data)"),
            "license": "CC0-1.0", "retrieval_date": "2026-09-15",
            "n_meghalaya": int(len(ml)),
            "year_known": int((ml["INITIATION"] > 0).sum()),
            "year_unknown": int((ml["INITIATION"] == 0).sum()),
            "geographic_coverage": "Meghalaya bbox 24.5–26.5N 89.5–93.0E",
            "label_definition": "catalogued slide occurrence (no exact dates)",
            "boundary": "year-or-unknown resolution → spatial features + GIS "
                        "display only; NOT temporal sequences",
            "citation": ("Geological Survey of India via NGDR/Bhukosh; "
                         "accessed via bharatlas CC0-1.0 mirror")}
    json.dump(meta, open(os.path.join(HERE, "metadata", "gsi.json"),
                         "w"), indent=1)
    print(f"gsi: {len(ml)} slides -> compact csv + zone features {zf}")


if __name__ == "__main__":
    main()
