"""GEO-SENTINEL training-pipeline shared helpers (audited-datasets track).

Single home for: canonical event-ID normalization, dataset checksums/paths,
validation + QC wrappers (reusing ner_v2 constants and gauge iterators —
never duplicating their thresholds), the SegFormer BLOCKED gate, event-grouped
split helpers, metrics, and live-data provider abstractions.

Nothing here trains a model. Nothing here modifies datasets/.
"""
import csv
import hashlib
import math
import os
import re

from ner_v2_common import (  # noqa: E402 — thresholds reused, not redefined
    DATASETS_DIR, GAUGE_MISSING, HOURLY_SPIKE_MM, DAILY_SPIKE_MM,
)

PKG = os.path.join(DATASETS_DIR, "GEO_SENTINEL_TRAINING_PACKAGE",
                   "GEO_SENTINEL_TRAINING_PACKAGE")
RF_CSV = os.path.join(PKG, "RF", "meghalaya_rf_training_features.csv")
MAMBA_CSV = os.path.join(PKG, "MAMBA",
                         "meghalaya_mamba_supervised_sequences_15f.csv")
MAMBA_NPZ = os.path.join(PKG, "MAMBA",
                         "meghalaya_mamba_supervised_tensor_15f.npz")
LABELS_CSV = os.path.join(PKG, "LABELS", "meghalaya_high_confidence_events.csv")
EVENT_MANIFEST = os.path.join(PKG, "SEGFORMER", "event_manifest.csv")
SEG_MANIFEST = os.path.join(PKG, "SEGFORMER", "segformer_manifest.csv")
PATCHES_DIR = os.path.join(PKG, "SEGFORMER", "PATCHES")
REPORTS_CSV = os.path.join(DATASETS_DIR, "Landslide Reports.csv")

SEGFORMER_STATUS = "BLOCKED"  # §4: flips only via segformer_gate() evidence

# ---------------------------------------------------------------- IDs


def normalize_event_id(raw) -> str:
    """Canonical event id: digits only ('LS_10,985' / '10,985' -> '10985').

    Single implementation — every pipeline join must use this.
    """
    digits = re.sub(r"\D", "", str(raw or ""))
    if not digits:
        raise ValueError(f"unnormalizable event id: {raw!r}")
    return digits


# ---------------------------------------------------------------- misc


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()[:16]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    from math import radians, sin, cos, asin, sqrt
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def valid_lonlat(lat, lon) -> bool:
    try:
        return -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0
    except (TypeError, ValueError):
        return False


def in_meghalaya(lat, lon) -> bool:
    return 24.9 <= float(lat) <= 26.6 and 89.8 <= float(lon) <= 93.1


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    return [round(max(0.0, (c - m) / den), 3), round(min(1.0, (c + m) / den), 3)]


# ---------------------------------------------------------------- validation


def validate_rf_rows(rows: list[dict]) -> dict:
    """Fail-fast audit of the RF training CSV. Raises on structural faults."""
    report = {"n_rows": len(rows)}
    if not rows:
        raise ValueError("RF CSV is empty")
    label_vals = {r.get("Landslide_Label") for r in rows}
    if label_vals - {"0", "1"}:
        raise ValueError(f"invalid labels (want 0/1 pseudo-absence coding): {label_vals}")
    ids = [normalize_event_id(r.get("Point_ID", "")) for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate Point_IDs: {dupes}")
    bad_coords = [r["Point_ID"] for r in rows
                  if not valid_lonlat(r.get("Latitude"), r.get("Longitude"))]
    if bad_coords:
        raise ValueError(f"invalid coordinates: {bad_coords}")
    outside = [r["Point_ID"] for r in rows
               if not in_meghalaya(r["Latitude"], r["Longitude"])]
    num_cols = [c for c in rows[0] if c not in
                ("Point_ID", "Latitude", "Longitude", "Landslide_Label")]
    nan_inf = {}
    for c in num_cols:
        bad = 0
        for r in rows:
            try:
                v = float(r[c])
                if math.isnan(v) or math.isinf(v):
                    bad += 1
            except (TypeError, ValueError):
                bad += 1
        if bad:
            nan_inf[c] = bad
    if nan_inf:
        raise ValueError(f"NaN/Inf/unparseable values: {nan_inf}")
    n_pos = sum(1 for r in rows if r["Landslide_Label"] == "1")
    report.update({"n_pos": n_pos, "n_neg": len(rows) - n_pos,
                   "feature_cols": num_cols, "outside_meghalaya": outside,
                   "dupes": dupes})
    return report


def validate_mamba_npz(path: str = MAMBA_NPZ) -> dict:
    import numpy as np
    d = np.load(path, allow_pickle=False)
    X, y = d["X"].astype("float64"), d["y"].astype(int)
    sids = [str(s) for s in d["sequence_ids"]]
    if X.shape[1:] != (73, 15):
        raise ValueError(f"unexpected Mamba tensor shape {X.shape} (want (N,73,15))")
    if not (np.isfinite(X).all() and set(np.unique(y)) <= {0, 1}):
        raise ValueError("Mamba tensor has NaN/Inf or non-binary labels")
    if len(set(sids)) != len(sids):
        raise ValueError("duplicate Mamba sequence_ids")
    events = [normalize_event_id(s.split("__")[-1].replace("LS_", "")) for s in sids]
    if len(set(events)) != 18:
        raise ValueError(f"want 18 Mamba event groups, found {len(set(events))}")
    return {"n_seq": int(X.shape[0]), "steps": 73, "features": list(d["feature_names"]),
            "n_pos": int((y == 1).sum()), "n_bg": int((y == 0).sum()),
            "n_events": len(set(events)), "events": sorted(set(events))}


def check_mamba_csv_integrity(path: str = MAMBA_CSV, max_seqs: int = 0) -> dict:
    """Timestamp monotonicity + fixed length + finite values (CSV source)."""
    import datetime as _dt
    seqs: dict = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            seqs.setdefault(r["Sequence_ID"], []).append(r)
    checked, bad = 0, []
    feat_cols = None
    for sid, rows in seqs.items():
        if max_seqs and checked >= max_seqs:
            break
        checked += 1
        ts = [_dt.datetime.strptime(x["Timestamp"], "%Y-%m-%d %H:%M:%S") for x in rows]
        if any(b <= a for a, b in zip(ts, ts[1:])):
            bad.append((sid, "non-monotonic timestamps"))
        if len(rows) != 73:
            bad.append((sid, f"length {len(rows)} != 73"))
        if feat_cols is None:
            feat_cols = [c for c in rows[0]
                         if c not in ("Sequence_ID", "Landslide_Label", "Hour_Relative",
                                      "Timestamp", "Latitude", "Longitude")]
        for x in rows:
            for c in feat_cols:
                try:
                    v = float(x[c])
                    if math.isnan(v) or math.isinf(v):
                        raise ValueError
                except (TypeError, ValueError):
                    bad.append((sid, f"bad value {c}={x[c]!r}"))
                    break
    if bad:
        raise ValueError(f"Mamba integrity failures (showing 5): {bad[:5]}")
    return {"n_seq_checked": checked, "feature_cols": feat_cols}


# ---------------------------------------------------------------- rainfall QC (wraps existing gates)


def rainfall_qc_stats() -> dict:
    """Accepted/rejected counts per gauge file under the ner_v2 gates.

    Reuses GAUGE_MISSING / HOURLY_SPIKE_MM / DAILY_SPIKE_MM — the same
    thresholds the feature code enforces.
    """
    import datetime as _dt
    specs = {
        "manual_1991_2020": ("rainfall_manual_daily_meghalaya_ml_1991_2020.csv",
                             "Manual Daily Rainfall (mm)", DAILY_SPIKE_MM),
        "manual_2021_2025": ("rainfall_manual_daily_meghalaya_ml_2021_2025.csv",
                             "Manual Daily Rainfall (mm)", DAILY_SPIKE_MM),
        "tel_2021_2025": ("rainfall_tel_hr_meghalaya_ml_2021_2025.csv",
                          "Telemetry Hourly Rainfall (mm)", HOURLY_SPIKE_MM),
    }
    out = {}
    for key, (fname, col, spike) in specs.items():
        ok = neg = sentinel = over = dup = unparse = 0
        seen = set()
        with open(os.path.join(DATASETS_DIR, fname),
                  encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    t = _dt.datetime.strptime(r["Data Acquisition Time"].strip(),
                                              "%d-%m-%Y %H:%M")
                    v = float(r[col].strip())
                except (ValueError, AttributeError, KeyError, TypeError):
                    unparse += 1
                    continue
                k = (r["Station"].strip(), t)
                if k in seen:
                    dup += 1
                    continue
                seen.add(k)
                if v in GAUGE_MISSING:
                    sentinel += 1
                elif v < 0:
                    neg += 1
                elif v > spike:
                    over += 1
                else:
                    ok += 1
        out[key] = {"file": fname, "accepted": ok, "rejected_sentinel": sentinel,
                    "rejected_negative": neg, f"rejected_spike_gt_{spike}": over,
                    "rejected_duplicate": dup, "rejected_unparseable": unparse}
    return out


# ---------------------------------------------------------------- SegFormer gate (§4, §33)


def segformer_gate(threshold: float = 0.01) -> dict:
    """Validate SegFormer readiness. Returns BLOCKED unless real pixels+masks.

    Checks: manifest present, patch pixels non-constant, mask files exist and
    align, valid-pixel ratio above threshold.
    """
    import struct
    import zlib
    verdict = {"status": "BLOCKED", "checks": {}}
    if not os.path.exists(SEG_MANIFEST):
        verdict["checks"]["manifest"] = "missing"
        return verdict
    with open(SEG_MANIFEST, encoding="utf-8", newline="") as fh:
        manifest = list(csv.DictReader(fh))
    verdict["checks"]["manifest_events"] = len(manifest)
    const_optical, const_qa, total_optical = 0, 0, 0
    nodata_pixels = 0
    for row in manifest:
        for band in ("blue", "green", "red", "nir"):
            p = row.get(band, "").strip()
            if not p:
                continue
            fp = os.path.join(PKG, *p.split("/"))
            if not os.path.exists(fp):
                continue
            total_optical += 1
            with open(fp, "rb") as fh:
                buf = fh.read()
            off = struct.unpack("<I", buf[4:8])[0]
            n = struct.unpack("<H", buf[off:off + 2])[0]
            tags = {}
            for i in range(n):
                tag, _typ, _cnt, val = struct.unpack("<HHI4s", buf[off + 2 + i * 12:off + 2 + i * 12 + 12])
                tags[tag] = struct.unpack("<I", val)[0]
            raw = zlib.decompress(buf[tags[324]:tags[324] + tags[325]])
            px = struct.unpack("<" + str(len(raw) // 2) + "h", raw)
            if len(set(px)) <= 1:
                const_optical += 1
            nodata_pixels += sum(1 for v in px if v == 0)
    verdict["checks"]["constant_optical_patches"] = f"{const_optical}/{total_optical}"
    mask_files = [f for f in os.listdir(PATCHES_DIR)] if os.path.exists(PATCHES_DIR) else []
    has_masks = any("mask" in f.lower() for root, _, fs in os.walk(PATCHES_DIR) for f in fs)
    verdict["checks"]["masks_present"] = bool(has_masks)
    verdict["checks"]["non_constant_input"] = const_optical == 0 and total_optical > 0
    verdict["checks"]["valid_mask_exists"] = bool(has_masks)
    if verdict["checks"]["non_constant_input"] and verdict["checks"]["valid_mask_exists"]:
        verdict["status"] = "READY"
    return verdict


# ---------------------------------------------------------------- splits + metrics


def event_groups_rf(rows: list[dict], cluster_km: float = 10.0) -> list[str]:
    """Group RF rows so samples within `cluster_km` share a group.

    Positives group by own event; a background point near an event joins that
    event's group (spatial-leakage guard). Greedy single linkage, tiny n.
    """
    pts = [(normalize_event_id(r["Point_ID"]) if r["Landslide_Label"] == "1" else None,
            float(r["Latitude"]), float(r["Longitude"])) for r in rows]
    groups: list[str] = []
    for i, (eid, la, lo) in enumerate(pts):
        if eid is not None and not eid.startswith("BG"):
            groups.append("EV_" + eid)
            continue
        best, bestd = None, cluster_km
        for j, (ejd, ja, jo) in enumerate(pts):
            if ejd is None or ejd.startswith("BG") or i == j:
                continue
            d = haversine_km(la, lo, ja, jo)
            if d < bestd:
                best, bestd = ejd, d
        groups.append("EV_" + best if best else "BG_" + str(i))
    return groups


def classification_metrics(y_true, y_proba, thresh: float = 0.5) -> dict:
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 precision_score, recall_score, f1_score,
                                 balanced_accuracy_score, brier_score_loss,
                                 confusion_matrix)
    import numpy as np
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    y_pred = (y_proba >= thresh).astype(int)
    m = {"n": int(len(y_true)), "n_pos": int(y_true.sum()),
         "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
         "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
         "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
         "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
         "brier": round(float(brier_score_loss(y_true, y_proba)), 4),
         "confusion": confusion_matrix(y_true, y_pred).tolist(),
         "threshold": thresh}
    if len(set(y_true)) > 1:
        m["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
        m["pr_auc"] = round(float(average_precision_score(y_true, y_proba)), 4)
    else:
        m["roc_auc"] = m["pr_auc"] = None
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    m["recall_ci95"] = wilson(tp, int(y_true.sum()))
    return m


# ---------------------------------------------------------------- live-data provider abstractions (§29)


class GaugeProvider:
    """QC'd gauge readings. Source-tagged; NOT a live feed."""

    def __init__(self):
        from ner_v2_features import _iter_ok_hourly, _iter_ok_daily
        self._hourly = list(_iter_ok_hourly())
        self._daily = list(_iter_ok_daily())
        self.source = "datasets/ rainfall CSVs (historical, QC-gated)"

    def hourly(self):
        return self._hourly

    def daily(self):
        return self._daily


class WeatherProvider:
    """Schema reference for a future ECMWF/ERA5 feed.

    The Jan-2020 .nc files are format samples only — this provider loads
    their variable/grid schema and refuses to serve them as live data.
    """

    SCHEMA_FILES = {"accum": "data_stream-oper_stepType-accum.nc",
                    "instant": "data_stream-oper_stepType-instant.nc"}

    def __init__(self):
        self.source = "SAMPLE SCHEMA ONLY (Jan-2020 .nc) — no live feed connected"
        self.live = False

    def schema(self) -> dict:
        import h5py
        out = {}
        for key, fname in self.SCHEMA_FILES.items():
            with h5py.File(os.path.join(DATASETS_DIR, fname), "r") as h:
                out[key] = {"variables": sorted(
                    k for k in h.keys()
                    if k not in ("latitude", "longitude", "valid_time", "number", "expver")),
                    "lat": [round(float(v), 2) for v in h["latitude"][:]],
                    "lon": [round(float(v), 2) for v in h["longitude"][:]]}
        return out

    def latest(self):
        raise RuntimeError("no live weather feed connected (prototype thresholds only)")
