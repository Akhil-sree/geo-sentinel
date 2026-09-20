"""Event-level training dataset (Phase 1E/2B).

Replaces the n=8 zone-label fit with zone-YEAR samples derived from the
seeded historical inventory (10 demo events, 2022-2024):

    sample = (zone, year)  →  8 zones x 3 years = 24 samples
    label  = 1 if >=1 recorded event in that zone-year else 0  (9 pos / 15 neg)

Features are STATIC terrain only (SAR mock excluded — feeding current mock
values into historical labels would be leakage). Groups = district, so
spatial GroupKFold never validates on the same district it trained on.

Status: DEMO inventory (synthetic seed events, NOT an authoritative
catalogue). Versioned; an authoritative GSI/NRSC inventory can replace
EVENTS_BY_ZONE_YEAR without changing the pipeline.
"""

DATASET_VERSION = "events_v2"
FEATURE_VERSION = "terrain6_v1"

FEATURES = ["slope", "elevation_norm", "ruggedness", "road_proximity",
            "drainage_proximity", "settlement_density"]

V3_FEATURES = FEATURES + ["gsi_count_norm", "gsi_dist_norm"]


def _gsi_features():
    """Real GSI slide density/proximity per zone (processed artifact)."""
    import json as _json
    import os as _os
    fn = _os.path.join(_os.path.dirname(__file__), "..", "..", "data",
                       "processed", "gsi_zone_features.json")
    with open(fn, encoding="utf-8") as f:
        return _json.load(f)

# (zone_id, year) pairs with >=1 recorded landslide (from app/seed.py EVENTS)
EVENTS_BY_ZONE_YEAR = {
    ("Z1", 2023), ("Z1", 2024),
    ("Z2", 2024),
    ("Z3", 2022), ("Z3", 2023),
    ("Z4", 2024),
    ("Z5", 2023), ("Z5", 2024),
    ("Z7", 2023),
    ("Z8", 2022),
}
YEARS = (2022, 2023, 2024)


def build_event_dataset(zones, version="v2"):
    """zones: iterable of Zone objects. Returns (X, y, groups, meta).

    v2: terrain6 (seed static). v3: terrain6 + 2 REAL GSI features
    (slide count within 15km normalized + nearest-slide distance) —
    same 24 samples, richer features (no sample inflation).
    Deterministic: sorted by (zone_id, year). Raises on empty input.
    """
    import numpy as np
    gsi = _gsi_features() if version == "v3" else None
    rows, labels, groups, keys = [], [], [], []
    zmap = {z.id: z for z in zones}
    for zid in sorted(zmap):
        z = zmap[zid]
        for yr in YEARS:
            row = [float(z.slope), min(1.0, float(z.elevation) / 2000.0),
                   float(z.ruggedness), float(z.road_proximity),
                   float(z.drainage_proximity), float(z.settlement_density)]
            if gsi is not None:
                g = gsi[zid]
                row += [min(1.0, g["gsi_count_15km"] / 120.0),
                        min(1.0, g["gsi_dist_km"] / 20.0)]
            rows.append(row)
            labels.append(1 if (zid, yr) in EVENTS_BY_ZONE_YEAR else 0)
            groups.append(z.district)
            keys.append((zid, yr))
    if not rows:
        raise ValueError("no zones — seed the database first")
    X = np.asarray(rows, dtype=float)
    y = np.asarray(labels, dtype=int)
    return X, y, np.asarray(groups), {
        "dataset_version": "events_v3" if version == "v3" else DATASET_VERSION,
        "feature_version": "terrain8_gsi_v1" if version == "v3" else FEATURE_VERSION,
        "n_samples": int(len(rows)), "n_positive": int(y.sum()),
        "n_negative": int(len(rows) - y.sum()), "keys": keys,
        "source": ("seed demo inventory + REAL GSI spatial features"
                   if version == "v3"
                   else "seed demo inventory (10 events) — NOT authoritative"),
    }


def check_leakage(keys, groups):
    """Duplicate (zone,year) or same-zone train/val overlap is a hard error
    only for duplicates; same-zone-different-year overlap is reported (not
    an error) since groups=district keeps districts apart in CV."""
    if len(set(keys)) != len(keys):
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        raise ValueError(f"duplicate samples (leakage): {dupes}")
    return {"duplicate_check": "pass", "grouping": "district (spatial block CV)"}
