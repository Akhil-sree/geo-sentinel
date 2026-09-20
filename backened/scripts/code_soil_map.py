"""PHASE 4 — Soil map coding + validation (part 1: codes artifact).

Inspects datasets/Meghalaya_Soil.geojson (READ-ONLY): CRS evidence, geometry
validity (shapely), attributes, spatial coverage. Builds the deterministic
soil code table data/processed/soil_codes_v2.json:

- drainage: from explicit drainage words in Soil_Description
  (excessively/well/moderately/imperfectly/poorly/very poorly drained,
  aquic/haplaquepts → poor; UNKNOWN when no drainage evidence).
- texture: fine / coarse-loamy / loamy (explicit words only, else UNKNOWN).
- erosion: none/slight/moderate/severe/very severe (explicit only).
- taxonomy: verbatim Soil_Taxonomy string (no interpretation).

Nothing is guessed: any unit without explicit evidence keeps UNKNOWN for
that axis. Writes data/metadata/soil_v2_validation.json.

Run: python scripts/code_soil_map.py [--write]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

from ner_v2_common import DATASETS_DIR, PROCESSED_DIR, META_DIR, utcnow  # noqa: E402

SOIL_GEOJSON = os.path.join(DATASETS_DIR, "Meghalaya_Soil.geojson")
CODES_JSON = os.path.join(PROCESSED_DIR, "soil_codes_v2.json")
VALID_JSON = os.path.join(META_DIR, "soil_v2_validation.json")

DRAINAGE_PATTERNS = [
    ("excessively drained", "EXCESSIVE"),
    ("somewhat excessively", "EXCESSIVE"),
    ("well drained", "WELL"),
    ("moderately well", "MODERATE"),
    ("imperfectly drained", "IMPERFECT"),
    ("poorly drained", "POOR"),
    ("very poorly drained", "VERY_POOR"),
    ("haplaquepts", "POOR"),
    ("humaquepts", "POOR"),
    ("aquic", "POOR"),
]
TEXTURE_PATTERNS = [
    ("coarse-loamy", "COARSE_LOAMY"),
    ("fine-loamy", "FINE_LOAMY"),
    ("fine silty", "FINE_SILTY"),
    (re.compile(r"\bfine soils?\b"), "FINE"),
    (re.compile(r"\bloamy\b"), "LOAMY"),
    (re.compile(r"\bclayey\b"), "CLAYEY"),
    (re.compile(r"\bsandy\b"), "SANDY"),
]
EROSION_PATTERNS = [
    ("very severe erosion", "VERY_SEVERE"),
    ("severe erosion", "SEVERE"),
    ("moderate erosion", "MODERATE"),
    ("slight erosion", "SLIGHT"),
    ("no erosion", "NONE"),
]


def _match(text: str, patterns) -> str:
    for pat, code in patterns:
        if isinstance(pat, str):
            if pat in text:
                return code
        elif pat.search(text):
            return code
    return "UNKNOWN"


def code_unit(props: dict) -> dict:
    desc = (props.get("Soil_Description") or "").lower()
    tax = (props.get("Soil_Taxonomy") or "").lower()
    joint = desc + " " + tax
    return {
        "Soil_ID": props.get("Soil_ID", "UNKNOWN"),
        "drainage": _match(joint, DRAINAGE_PATTERNS),
        "texture": _match(desc, TEXTURE_PATTERNS),
        "erosion": _match(desc, EROSION_PATTERNS),
        "taxonomy": (props.get("Soil_Taxonomy") or "").strip() or "UNKNOWN",
        "area_sqkm": props.get("Area_sqkm"),
    }


def main() -> dict:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    from shapely.geometry import shape
    gj = json.load(open(SOIL_GEOJSON, encoding="utf-8"))
    feats = gj.get("features", [])
    has_crs = "crs" in gj
    # coords are lon/lat degrees (verified bounds) → scale evidence, not proof
    lons = [c[0] for f in feats for poly in
            (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
             else [ring for p in f["geometry"]["coordinates"] for ring in p])
            for c in poly]
    lats = [c[1] for f in feats for poly in
            (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
             else [ring for p in f["geometry"]["coordinates"] for ring in p])
            for c in poly]
    invalid = 0
    for f in feats:
        try:
            if not shape(f["geometry"]).is_valid:
                invalid += 1
        except Exception:
            invalid += 1
    codes = [code_unit(f.get("properties", {})) for f in feats]
    unk = {k: sum(1 for c in codes if c[k] == "UNKNOWN") for k in ("drainage", "texture", "erosion")}
    areas = [c["area_sqkm"] for c in codes if isinstance(c["area_sqkm"], (int, float))]
    report = {"units": len(feats), "crs_field": has_crs,
              "crs_assumed": "EPSG:4326 (lon/lat degrees — evidence: value ranges, NOT a declared CRS)",
              "lon_range": [round(min(lons), 3), round(max(lons), 3)],
              "lat_range": [round(min(lats), 3), round(max(lats), 3)],
              "area_sum_sqkm": round(sum(areas), 1),
              "invalid_geometries": invalid,
              "unknown_axes": unk,
              "provenance": "UNKNOWN (no agency/date in file or folder)",
              "vintage": "UNKNOWN"}
    print(json.dumps(report, indent=1))
    if args.write:
        with open(CODES_JSON, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(), "method": "explicit-word coding, UNKNOWN on no evidence",
                       "codes": codes}, fh, indent=1)
        with open(VALID_JSON, "w", encoding="utf-8") as fh:
            json.dump({"at": utcnow(), **report}, fh, indent=1)
        print(f"wrote {CODES_JSON}, {VALID_JSON}")
    return report


if __name__ == "__main__":
    main()
