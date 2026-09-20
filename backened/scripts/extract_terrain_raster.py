"""PHASE 3 — SRTM raster terrain extraction for v2 candidates.

For each TRAINING_ELIGIBLE candidate: sample the datasets/ SRTM tiles
(READ-ONLY) via ner_v2_features.raster_terrain and write
data/processed/terrain_raster_v2.json ({source_event_id: feats+coverage}).
Uncovered points are flagged OUT_OF_COVERAGE (rim gap), never filled.

Run: python scripts/extract_terrain_raster.py [--write]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_v2_common import PROCESSED_DIR, META_DIR, utcnow  # noqa: E402
from ner_v2_features import raster_terrain  # noqa: E402

CAND_JSON = os.path.join(PROCESSED_DIR, "reports_v2_candidates.json")
TERR_JSON = os.path.join(PROCESSED_DIR, "terrain_raster_v2.json")
TERR_META = os.path.join(META_DIR, "terrain_raster_v2.json")


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    cands = [c for c in json.load(open(CAND_JSON, encoding="utf-8"))
             if c.get("status") == "TRAINING_ELIGIBLE"]
    out, covered, failed = {}, 0, 0
    for c in cands:
        feats, prov, miss = raster_terrain(c["latitude"], c["longitude"])
        ok = feats.get("r_elevation_mean") is not None
        covered += ok
        failed += not ok
        out[c["source_event_id"]] = {"feats": feats, "prov": prov, "miss": miss,
                                     "covered": ok}
    rep = {"candidates": len(cands), "covered": covered,
           "out_of_coverage": failed, "at": utcnow(),
           "method": "SRTM 1-arcsec raster, 5x5 window, Horn slope/aspect, ZT curvature",
           "gap": "rim tiles e089/e092/n24 missing; TWI needs catchment routing (not computed)"}
    print(json.dumps(rep, indent=1))
    if args.write:
        with open(TERR_JSON, "w", encoding="utf-8") as fh:
            json.dump(out, fh)
        with open(TERR_META, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1)
        print(f"wrote {TERR_JSON}, {TERR_META}")
    return rep


if __name__ == "__main__":
    main()
