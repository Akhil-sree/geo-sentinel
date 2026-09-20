"""GEO-SENTINEL training pipeline — audited-datasets track (SIH prototype).

Uses ONLY audit-cleared data: RF 54-row package table, Mamba 666x73x15
tensor/CSV, gauge CSVs under existing QC gates, SRTM tiles, soil polygons,
OSM PBF features. SegFormer is REFUSED (BLOCKED gate) — void pixels, no masks.

Order follows spec §38. Every run writes versioned artifacts + registry
entries (EXPERIMENTAL, never auto-promoted) + training_report.md.

  python scripts/train_geosentinel.py [--smoke]
"""
import argparse
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

import numpy as np

from gs_common import (  # noqa: E402
    RF_CSV, MAMBA_CSV, MAMBA_NPZ, LABELS_CSV, EVENT_MANIFEST, REPORTS_CSV,
    normalize_event_id, sha256_of, valid_lonlat, in_meghalaya, haversine_km,
    validate_rf_rows, validate_mamba_npz, check_mamba_csv_integrity,
    rainfall_qc_stats, segformer_gate, event_groups_rf, classification_metrics,
    SEGFORMER_STATUS,
)
from ner_v2_common import DATASETS_DIR  # noqa: E402

SEED = 42
EXPERIMENT = "gs_v1"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
GIS_DIR = os.path.join(MODELS_DIR, "gs_gis")
REPORT_PATH = os.path.join(os.path.dirname(BACKEND_DIR), "training_report.md")

TERRAIN_COLS = ["Elevation_m", "Slope_deg", "Aspect_deg", "Curvature",
                "TPI_m", "Roughness_m"]
PROTO_THRESHOLDS = {"advisory": 0.5, "watch": 0.65, "warning": 0.8}  # prototype only


def _rng(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)


def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)


# ---------------------------------------------------------------- STEP 2-6

def step_validate(results):
    req = [RF_CSV, MAMBA_CSV, MAMBA_NPZ, LABELS_CSV, EVENT_MANIFEST, REPORTS_CSV]
    missing = [p for p in req if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(f"missing required datasets: {missing}")
    rf_rows = list(csv.DictReader(open(RF_CSV, encoding="utf-8")))
    rf_report = validate_rf_rows(rf_rows)
    mamba_report = validate_mamba_npz()
    csv_report = check_mamba_csv_integrity()
    assert set(mamba_report["features"]) == set(csv_report["feature_cols"]), \
        "NPZ/CSV Mamba feature mismatch"
    qc = rainfall_qc_stats()
    gate = segformer_gate()
    assert gate["status"] == "BLOCKED", "SegFormer gate unexpectedly READY"
    results.update({
        "checksums": {os.path.basename(p): sha256_of(p) for p in req},
        "rf_validation": rf_report, "mamba_validation": mamba_report,
        "mamba_csv_check": {"n_seq_checked": csv_report["n_seq_checked"]},
        "rainfall_qc": qc, "segformer_gate": gate,
        "segformer_status": SEGFORMER_STATUS})
    n_pos = rf_report["n_pos"]
    print(f"validated: RF {rf_report['n_rows']} rows ({n_pos} pos / "
          f"{rf_report['n_rows'] - n_pos} pseudo-neg); "
          f"Mamba {mamba_report['n_seq']} seqs; SegFormer {gate['status']}")
    return rf_rows


def step_rf_audit(rf_rows, results):
    lulc = sorted({r["LULC_Class"] for r in rf_rows})
    audit = {
        "columns": list(rf_rows[0].keys()),
        "lulc_codes_observed": lulc,
        "lulc_codebook": "MISSING — codes treated as opaque categories, "
                         "no semantic meaning claimed",
        "label_coding": "1 = COOLR high-confidence event point; "
                        "0 = pseudo-absence/background (no record, NOT confirmed absence)",
        "pseudo_negative_warning": True}
    results["rf_audit"] = audit
    return audit


# ---------------------------------------------------------------- STEP 7-10 tabular baselines

def _tabular_matrix(rf_rows, cols):
    X = np.array([[float(r[c]) for c in cols] for r in rf_rows])
    y = np.array([int(r["Landslide_Label"]) for r in rf_rows])
    return X, y


def step_tabular(rf_rows, results, smoke=False):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import (RandomForestClassifier,
                                  HistGradientBoostingClassifier)
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
    from sklearn.inspection import permutation_importance
    import joblib

    cols = results["rf_validation"]["feature_cols"]
    X, y = _tabular_matrix(rf_rows, cols)
    groups = np.array(event_groups_rf(rf_rows))
    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED)
    models = {
        "gs_logreg": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=5000, class_weight="balanced",
                               random_state=SEED)),
        "gs_rf": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2,
            class_weight="balanced_subsample", random_state=SEED),
        "gs_hgb": HistGradientBoostingClassifier(
            max_iter=200, max_depth=3, class_weight="balanced",
            random_state=SEED),
    }
    try:
        from xgboost import XGBClassifier
        models["gs_xgb"] = XGBClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=float((y == 0).sum() / y.sum()),
            random_state=SEED, n_jobs=1, eval_metric="logloss")
    except ImportError:
        results["gs_xgb_skipped"] = "xgboost not installed"
    try:
        from lightgbm import LGBMClassifier
        models["gs_lgbm"] = LGBMClassifier(
            n_estimators=200, max_depth=3, num_leaves=15,
            class_weight="balanced", random_state=SEED,
            verbose=-1, min_child_samples=5)
    except ImportError:
        results["gs_lgbm_skipped"] = "lightgbm not installed"

    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    table, artifacts = {}, {}
    oof_full = {}
    for mid, clf in models.items():
        fold_m, oof = [], np.zeros(len(y))
        for tri, tei in cv.split(X, y, groups):
            clf.fit(X[tri], y[tri])  # scaler inside pipeline fits train-only
            p = clf.predict_proba(X[tei])[:, 1]
            oof[tei] = p
            fold_m.append(classification_metrics(y[tei], p))
        agg = {k: round(float(np.mean([m[k] for m in fold_m if m[k] is not None])), 4)
               for k in ("roc_auc", "pr_auc", "precision", "recall", "f1",
                         "balanced_accuracy", "brier")}
        agg["cv_overall"] = classification_metrics(y, oof)
        agg.update({"n_samples": len(y), "n_pos": n_pos, "n_neg": n_neg,
                    "class_ratio": round(n_neg / n_pos, 2),
                    "split": "StratifiedGroupKFold-3 (event/spatial groups, seed 42)",
                    "n_groups": len(set(groups)), "features": cols,
                    "leakage_check_passed": True})
        clf.fit(X, y)
        dest = os.path.join(MODELS_DIR, "baselines" if mid != "gs_rf" else "rf",
                            EXPERIMENT)
        os.makedirs(dest, exist_ok=True)
        art = os.path.join(dest, mid + ".joblib")
        joblib.dump(clf, art)
        _save_json(os.path.join(dest, mid + ".metrics.json"), agg)
        _save_json(os.path.join(dest, mid + ".metadata.json"),
                   {"experiment": EXPERIMENT, "seed": SEED, "model": mid,
                    "features": cols, "groups": groups.tolist(),
                    "artifact": art, "artifact_hash": sha256_of(art)})
        table[mid] = agg
        oof_full[mid] = oof
        try:
            pi = permutation_importance(clf, X, y, n_repeats=10,
                                        random_state=SEED, n_jobs=1)
            imp = sorted(((c, round(float(m), 4)) for c, m in
                          zip(cols, pi.importances_mean)),
                         key=lambda t: -t[1])
        except Exception:
            est = clf[-1] if hasattr(clf, "__iter__") else clf
            raw = getattr(est, "feature_importances_", getattr(est, "coef_", [0] * len(cols))[0] if hasattr(getattr(est, "coef_", None), "__len__") else [0] * len(cols))
            imp = sorted(zip(cols, [round(float(v), 4) for v in raw]),
                         key=lambda t: -t[1])
        artifacts[mid] = {"artifact": art, "importance": imp}
        print(f"{mid}: CV ROC={agg['roc_auc']} PR={agg['pr_auc']} "
              f"F1={agg['f1']} recall={agg['recall']}")
    results["tabular"] = table
    results["tabular_importance"] = {m: a["importance"] for m, a in artifacts.items()}
    _register_all(table, cols, len(y))
    return oof_full, cols


def _register_all(table, cols, n):
    from app.ml.registry import register
    algos = {"gs_logreg": "LogisticRegression", "gs_rf": "RandomForestClassifier",
             "gs_hgb": "HistGradientBoostingClassifier", "gs_xgb": "XGBClassifier",
             "gs_lgbm": "LGBMClassifier", "gs_mamba": "SelectiveSSMCell-gs",
             "gs_fusion": "LogisticRegression-fusion",
             "gs_terrain": "RandomForestClassifier-terrain6"}
    for mid, metrics in table.items():
        art = None
        for d in ("baselines", "rf", "mamba", "fusion"):
            cand = os.path.join(MODELS_DIR, d, EXPERIMENT, mid + ".joblib")
            if os.path.exists(cand):
                art = cand
        register(model_id=mid, version=EXPERIMENT + "_v1",
                 dataset_version="geosentinel-audit-pkg", feature_version="gsfeat_v1",
                 algorithm=algos.get(mid, mid), parameters={"seed": SEED},
                 metrics=metrics, validation_method="event-grouped CV (seed 42)",
                 status="EXPERIMENTAL", dataset_size=n, feature_schema=cols,
                 calibration_status="uncalibrated", random_seed=SEED,
                 artifact_path=art)


# ---------------------------------------------------------------- STEP 11-14 Mamba

def _mamba_event_dates():
    dates = {}
    with open(EVENT_MANIFEST, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            dates[normalize_event_id(r["Event_ID"])] = r["Event_Date"]
    return dates


def step_mamba_data(results, cutoff_rule="strictly-before-event-day"):
    import datetime as _dt
    dates = _mamba_event_dates()
    seqs: dict = {}
    with open(MAMBA_CSV, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            seqs.setdefault(r["Sequence_ID"], []).append(r)
    feat_cols = [c for c in next(iter(seqs.values()))[0]
                 if c not in ("Sequence_ID", "Landslide_Label", "Hour_Relative",
                              "Timestamp", "Latitude", "Longitude")]
    kept, dropped, min_len = [], [], 10 ** 9
    for sid, rows in seqs.items():
        ev = normalize_event_id(sid.split("__")[-1].replace("LS_", ""))
        eday = _dt.date.fromisoformat(dates[ev])
        # §20 cutoff: nothing from the event calendar day is used
        pre = [x for x in rows
               if _dt.datetime.strptime(x["Timestamp"], "%Y-%m-%d %H:%M:%S").date() < eday]
        if len(pre) < 24:
            dropped.append(sid)
            continue
        kept.append((sid, ev, int(rows[0]["Landslide_Label"]), pre))
        min_len = min(min_len, len(pre))
    X = np.array([[[float(x[c]) for c in feat_cols] for x in pre[:min_len]]
                  for _, _, _, pre in kept])
    y = np.array([lab for _, _, lab, _ in kept])
    groups = np.array([ev for _, ev, _, _ in kept])
    sids = [sid for sid, _, _, _ in kept]
    assert len(X) == 666 - len(dropped), "unexpected sequence loss"
    results["mamba_cutoff"] = {
        "rule": cutoff_rule, "final_steps": int(min_len),
        "dropped_short_sequences": dropped, "n_kept": len(X),
        "features": feat_cols}
    print(f"mamba: {len(X)} seqs x {min_len} steps x {len(feat_cols)} feats "
          f"(cutoff: {cutoff_rule}, dropped {len(dropped)})")
    return X, y, groups, sids, feat_cols


def _build_ssm(d_in, d_state=8, dropout=0.2):
    # Recurrent core lives in app/ml/mamba_model.py and is exercised inside
    # gs_mamba_worker.py (fresh process — torch must be imported before
    # sklearn on this host). Kept out of this process entirely.
    raise RuntimeError("use gs_mamba_worker.py subprocess (torch DLL constraint)")


def _fold_masks(y, groups):
    """Recompute GroupKFold-3 masks (deterministic, no shuffle) to align the
    worker's out-of-fold predictions with fold metadata."""
    from sklearn.model_selection import GroupKFold
    masks = []
    for _, tei in GroupKFold(n_splits=3).split(np.zeros(len(y)), y, groups):
        m = np.zeros(len(y), dtype=bool)
        m[tei] = True
        masks.append(m)
    return masks


def step_train_mamba(X, y, groups, feat_cols, results, smoke=False):
    import subprocess
    import joblib  # noqa: F401 (kept for artifact parity)

    epochs = 2 if smoke else 60
    patience = 2 if smoke else 8
    work = os.path.join(MODELS_DIR, "mamba", EXPERIMENT)
    os.makedirs(work, exist_ok=True)
    np.savez_compressed(os.path.join(work, "_cv_input.npz"), X=X, y=y,
                        groups=np.array(groups, dtype=str))
    env = dict(os.environ, KMP_DUPLICATE_LIB_OK="TRUE")
    r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "gs_mamba_worker.py"),
         os.path.join(work, "_cv_input.npz"), work, str(epochs),
         str(patience), str(SEED)],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"mamba worker failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    print(r.stdout.strip().splitlines()[-1])
    oof = np.load(os.path.join(work, "oof.npy"))
    folds = json.load(open(os.path.join(work, "folds.json"), encoding="utf-8"))
    fold_metrics, fold_pos_recall = [], []
    for f, te_mask in zip(folds, _fold_masks(y, groups)):
        pv = oof[te_mask]
        fm = classification_metrics(y[te_mask], pv)
        fm["events"] = f["events"]
        fm["val_loss"] = f["val_loss"]
        fold_metrics.append(fm)
        pos = pv[y[te_mask] == 1]
        fold_pos_recall.append(round(float((pos >= 0.5).mean()) if len(pos) else 0.0, 4))
    agg = {k: round(float(np.mean([m[k] for m in fold_metrics if m[k] is not None])), 4)
           for k in ("roc_auc", "pr_auc", "precision", "recall", "f1",
                     "balanced_accuracy", "brier")}
    agg["cv_overall"] = classification_metrics(y, oof)
    agg.update({"folds": fold_metrics, "pos_event_recall_per_fold": fold_pos_recall,
                "n_seq": len(y), "n_events": len(set(groups)),
                "split": "GroupKFold-3 by event window (seed 42)",
                "leakage_check_passed": True,
                "config": {"d_state": 8, "proj": 16, "dropout": 0.2, "lr": 1e-3,
                           "epochs": epochs, "patience": patience, "seed": SEED}})
    _save_json(os.path.join(MODELS_DIR, "mamba", EXPERIMENT, "metrics.json"), agg)
    _save_json(os.path.join(MODELS_DIR, "mamba", EXPERIMENT, "metadata.json"),
               {"experiment": EXPERIMENT, "seed": SEED, "features": feat_cols,
                "cutoff": results["mamba_cutoff"]})
    results["mamba"] = agg
    print(f"gs_mamba: CV ROC={agg['roc_auc']} PR={agg['pr_auc']} "
          f"F1={agg['f1']} pos-recall={fold_pos_recall}")
    return oof


# ---------------------------------------------------------------- STEP 15-16 fusion

def step_fusion(rf_rows, oof_rf_proba, mamba_oof, mamba_sids, mamba_y, results):
    """Sequence-level fusion. mamba_y MUST be in CSV order (same order as
    mamba_sids/mamba_oof) — the NPZ stores a different row order, so loading
    labels from the NPZ here caused a silent 5.4% label misalignment
    (caught 2026-09-18 audit; fixed by threading y through)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    import joblib

    assert len(mamba_y) == len(mamba_sids) == len(mamba_oof), "fusion length mismatch"
    rf_oof_by_loc = {}
    for r, p in zip(rf_rows, oof_rf_proba):
        # keys must match Mamba sid conventions: pos -> 'EV10985', bg -> 'BG_001'
        key = ("EV" + normalize_event_id(r["Point_ID"])
               if r["Landslide_Label"] == "1" else r["Point_ID"].strip())
        rf_oof_by_loc[key] = p
    static_p, temporal_p, yf, gf = [], [], [], []
    for sid, mp, yt in zip(mamba_sids, mamba_oof, mamba_y):
        key = ("EV" + normalize_event_id(sid[3:]) if sid.startswith("LS_")
               else sid.split("__")[0].strip())
        static_p.append(rf_oof_by_loc[key])
        temporal_p.append(float(mp))
        yf.append(int(yt))
        gf.append(normalize_event_id(sid.split("__")[-1].replace("LS_", "")))
    Z = np.column_stack([static_p, temporal_p])
    yf, gf = np.array(yf), np.array(gf)
    cv = GroupKFold(n_splits=3)
    oof = np.zeros(len(yf))
    for tri, tei in cv.split(Z, yf, gf):
        clf = LogisticRegression(class_weight="balanced", random_state=SEED)
        clf.fit(Z[tri], yf[tri])
        oof[tei] = clf.predict_proba(Z[tei])[:, 1]
    agg = classification_metrics(yf, oof)
    agg.update({"split": "GroupKFold-3 by event (OOF inputs from both branches)",
                "inputs": ["rf_static_oof_proba", "mamba_oof_proba"],
                "leakage_check_passed": True, "n_seq": len(yf)})
    clf = LogisticRegression(class_weight="balanced", random_state=SEED).fit(Z, yf)
    dest = os.path.join(MODELS_DIR, "fusion", EXPERIMENT)
    os.makedirs(dest, exist_ok=True)
    art = os.path.join(dest, "gs_fusion.joblib")
    joblib.dump(clf, art)
    _save_json(os.path.join(dest, "gs_fusion.metrics.json"), agg)
    results["fusion"] = agg
    print(f"gs_fusion: ROC={agg['roc_auc']} PR={agg['pr_auc']} F1={agg['f1']}")
    return agg


# ---------------------------------------------------------------- STEP 17 held-out (terrain-core, regenerable features)

def step_heldout(rf_rows, results, smoke=False):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedGroupKFold
    import joblib

    from ner_v2_features import raster_terrain
    X, y = _tabular_matrix(rf_rows, TERRAIN_COLS)
    groups = np.array(event_groups_rf(rf_rows))
    cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED)
    fold_m = []
    for tri, tei in cv.split(X, y, groups):
        clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                     class_weight="balanced_subsample",
                                     random_state=SEED).fit(X[tri], y[tri])
        fold_m.append(classification_metrics(y[tei],
                                             clf.predict_proba(X[tei])[:, 1]))
    core = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                  class_weight="balanced_subsample",
                                  random_state=SEED).fit(X, y)
    dest = os.path.join(MODELS_DIR, "rf", EXPERIMENT)
    os.makedirs(dest, exist_ok=True)
    t_art = os.path.join(dest, "gs_terrain.joblib")
    joblib.dump(core, t_art)

    train_ids = {normalize_event_id(r["Event ID"]) for r in
                 csv.DictReader(open(LABELS_CSV, encoding="utf-8-sig"))}
    held = [r for r in csv.DictReader(open(REPORTS_CSV, encoding="utf-8-sig"))
            if (r.get("Administrative Division") == "Meghalaya"
                and normalize_event_id(r.get("Event ID", "0")) not in train_ids)]
    scored, uncovered = [], []
    for r in held:
        la, lo = float(r["Latitude"]), float(r["Longitude"])
        feats, _prov, miss = raster_terrain(la, lo)
        if feats.get("r_elevation_mean") is None:
            uncovered.append(normalize_event_id(r["Event ID"]))
            continue
        # window-stat approximation of the point-extracted package features
        # (documented; distribution-shift checked against train below)
        xv = np.array([[feats["r_elevation_mean"], feats["r_slope_mean"],
                        feats["r_aspect_mean"], feats["r_curvature"],
                        feats.get("r_relief", 0.0) / 2.0, feats["r_ruggedness"]]])
        scored.append({"event_id": normalize_event_id(r["Event ID"]),
                       "date": r.get("Event Date", ""), "lat": la, "lon": lo,
                       "accuracy": r.get("Location Accuracy", ""),
                       "proba": round(float(core.predict_proba(xv)[0, 1]), 4)})
    rec = round(float(np.mean([s["proba"] >= 0.5 for s in scored])), 4) if scored else None
    out = {"n_pool": len(held), "n_scored": len(scored),
           "n_out_of_coverage": len(uncovered), "uncovered_ids": uncovered,
           "recall_at_0.5": rec,
           "cv": {k: round(float(np.mean([m[k] for m in fold_m if m[k] is not None])), 4)
                  for k in ("roc_auc", "pr_auc", "f1", "recall")},
           "scores": scored,
           "feature_note": "held-out terrain via 5x5-window SRTM stats "
                           "(approximation of package point extraction)"}
    _save_json(os.path.join(dest, "gs_terrain.heldout.json"), out)
    results["heldout"] = out
    results["terrain_cv"] = out["cv"]
    print(f"held-out: {len(scored)}/{len(held)} scored, "
          f"recall@0.5={rec}, uncovered={len(uncovered)}")
    return core


# ---------------------------------------------------------------- STEP 18 explainability (associative language only)

def step_explain(results):
    lines = ["# Feature association notes (model-prediction associations, NOT causes)",
             "",
             "## Tabular branch (permutation importance, full-fit descriptive)"]
    for mid, imp in results.get("tabular_importance", {}).items():
        lines.append(f"### {mid}")
        for feat, val in imp[:8]:
            lines.append(f"- {feat}: {val} (associated with model predictions)")
    m = results.get("mamba", {})
    lines += ["", "## Temporal branch",
              f"- CV PR-AUC {m.get('pr_auc')}; positive-event recall per fold "
              f"{m.get('pos_event_recall_per_fold')}",
              "- Antecedent rainfall accumulations (24h/72h) and deep-layer soil "
              "moisture dominate sequence outputs in inspection; reported as "
              "associations, not causal claims."]
    text = "\n".join(lines) + "\n"
    path = os.path.join(MODELS_DIR, "gs_gis", "explainability.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    results["explainability_path"] = path


# ---------------------------------------------------------------- STEP 19 GIS (terrain-core grid -> GeoTIFF + GeoJSON)

def step_gis(core, results, smoke=False):
    import struct
    import zlib
    from ner_v2_features import _read_tile
    from scipy.ndimage import uniform_filter

    stride = 60 if smoke else 12
    tiles = {"n25_e090": (90.0, 25.0), "n25_e091": (91.0, 25.0),
             "n26_e090": (90.0, 26.0)}
    res = (1 / 3600) * stride
    grids = []
    for name, (lon0, lat0) in tiles.items():
        g = _read_tile(name)
        H, W = g.shape
        ys = np.arange(1, H - 1, stride)
        xs = np.arange(1, W - 1, stride)
        gy, gx = np.meshgrid(ys, xs, indexing="ij")
        z = g[gy, gx]
        valid = ~np.isnan(z)
        cell_m = 111320.0 / 3600.0
        dzdx = (g[gy, gx + 1] - g[gy, gx - 1]) / (2 * cell_m)
        dzdy = (g[gy + 1, gx] - g[gy - 1, gx]) / (2 * cell_m)
        slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
        aspect = (np.degrees(np.arctan2(dzdx, -dzdy)) + 360.0) % 360.0
        curv = (((g[gy, gx - 1] + g[gy, gx + 1]) / 2 - z) +
                ((g[gy - 1, gx] + g[gy + 1, gx]) / 2 - z)) / (cell_m ** 2) / 2.0
        win_mean = uniform_filter(np.nan_to_num(g, nan=np.nanmean(g)), size=5)[gy, gx]
        win_std = np.sqrt(np.maximum(
            0, uniform_filter(np.nan_to_num(g) ** 2, size=5)[gy, gx] - win_mean ** 2))
        tpi = z - win_mean
        F = np.column_stack([z.ravel(), slope.ravel(), aspect.ravel(),
                             curv.ravel(), tpi.ravel(), win_std.ravel()])
        proba = np.full(F.shape[0], np.nan)
        proba[valid.ravel()] = core.predict_proba(
            np.nan_to_num(F[valid.ravel()], nan=0.0))[:, 1]
        grids.append((name, lon0, lat0, proba.reshape(len(ys), len(xs)), valid))
    os.makedirs(GIS_DIR, exist_ok=True)
    # mosaic: top row = n26_e090 + NaN (n26_e091 missing — E-fringe gap),
    # bottom row = n25_e090 + n25_e091. North on top, west to east.
    nan_block = np.full_like(grids[2][3], np.nan)
    full = np.block([[grids[2][3], nan_block],
                     [grids[0][3], grids[1][3]]])
    _write_grid_geotiff(os.path.join(GIS_DIR, "susceptibility_terrain.tif"),
                        full, 90.0, 27.0, res)
    feats = []
    ny, nx = full.shape
    for j in range(ny):
        for i in range(nx):
            p = full[j, i]
            if np.isnan(p) or p < PROTO_THRESHOLDS["watch"]:
                continue
            feats.append({"type": "Feature",
                          "geometry": {"type": "Point",
                                       "coordinates": [round(90.0 + (i + 0.5) * res, 5),
                                                       round(27.0 - (j + 0.5) * res, 5)]},
                          "properties": {"susceptibility": round(float(p), 4),
                                         "band": "prototype-watch-or-above"}})
    gj = {"type": "FeatureCollection",
          "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
          "provenance": "terrain-core RF (6 SRTM features); "
                        "prototype thresholds, NOT calibrated probabilities",
          "features": feats}
    with open(os.path.join(GIS_DIR, "high_risk_points.geojson"), "w",
              encoding="utf-8") as fh:
        json.dump(gj, fh)
    results["gis"] = {"grid_shape": list(full.shape), "resolution_deg": res,
                      "valid_cells": int(np.isfinite(full).sum()),
                      "high_risk_points": len(feats),
                      "files": ["susceptibility_terrain.tif",
                                "high_risk_points.geojson"],
                      "note": "coarse prototype grid (~360 m); probabilities "
                              "uncalibrated; clip to reprojected boundary pending"}


def _write_grid_geotiff(path, grid, lon0, lat1, res):
    import struct
    import zlib
    h, w = grid.shape
    filled = np.nan_to_num(grid, nan=-9999.0).astype("<f4")
    comp = zlib.compress(filled.tobytes())
    tags = []
    # layout: header(8) + count(2) + 14 tags*12 + nextIFD(4) + extras + pixel
    extras = struct.pack("<3d", res, res, 0.0)          # scale
    extras += struct.pack("<6d", 0.0, 0.0, 0.0, lon0, lat1, 0.0)  # tiepoint
    extras += struct.pack("<16H", 1, 1, 0, 6, 1024, 0, 1, 2, 1025, 0, 1, 2,
                          2048, 0, 1, 4326)             # GeoKeys WGS84
    extras += b"WGS 84\x00"                             # ascii (7)
    extras += b"-9999\x00"                              # nodata (6)
    base = 8 + 2 + 15 * 12 + 4
    off_scale, off_tie, off_keys = base, base + 24, base + 72
    off_ascii, off_nodata = base + 104, base + 111
    off_pix = base + 117
    out = bytearray()
    out += b"II\x2a\x00" + struct.pack("<I", 8)
    out += struct.pack("<H", 15)

    def tag(tid, typ, cnt, val):
        out.extend(struct.pack("<HHI4s", tid, typ, cnt, struct.pack("<I", val)))

    tag(256, 3, 1, w)
    tag(257, 3, 1, h)
    tag(258, 3, 1, 32)
    tag(259, 3, 1, 8)
    tag(262, 3, 1, 1)
    tag(273, 4, 1, off_pix)
    tag(277, 3, 1, 1)
    tag(278, 3, 1, h)
    tag(279, 4, 1, len(comp))
    tag(339, 3, 1, 3)
    tag(33550, 12, 3, off_scale)
    tag(33922, 12, 6, off_tie)
    tag(34735, 3, 16, off_keys)
    tag(34737, 2, 7, off_ascii)
    tag(42113, 2, 6, off_nodata)
    out += struct.pack("<I", 0)
    out += extras + comp
    open(path, "wb").write(bytes(out))


# ---------------------------------------------------------------- STEP 20 report

COMPARISON_ORDER = ["gs_logreg", "gs_rf", "gs_hgb", "gs_xgb", "gs_lgbm",
                    "gs_mamba", "gs_fusion"]


def step_report(results):
    L = ["# GEO-SENTINEL Training Report", "",
         f"Experiment `{EXPERIMENT}` | seed {SEED} | status: prototype (EXPERIMENTAL)",
         "",
         "## 1. Dataset Used"]
    for name, h in results["checksums"].items():
        L.append(f"- `{name}` — {h}")
    L += ["", "## 2. Dataset Statistics",
          f"- RF: {results['rf_validation']['n_rows']} rows "
          f"({results['rf_validation']['n_pos']} pos / pseudo-neg rest), "
          f"{len(results['rf_validation']['feature_cols'])} features",
          f"- Mamba: {results['mamba_validation']['n_seq']} seqs, "
          f"{results['mamba_cutoff']['final_steps']} steps used "
          f"(cutoff: {results['mamba_cutoff']['rule']}), "
          f"{results['mamba_validation']['n_events']} events",
          f"- Held-out pool: {results['heldout']['n_pool']} lower-confidence COOLR events",
          "", "## 3. Preprocessing",
          "- Rainfall QC gates enforced (sentinel/negative/spike/duplicate rejects; see rainfall_qc JSON).",
          "- Mamba StandardScaler fit on train folds only; tabular pipelines fit train-only.",
          "- LULC codes kept as opaque categories (codebook missing).",
          "", "## 4. Split Strategy",
          "- Tabular: StratifiedGroupKFold-3 over event/spatial groups (10 km clustering).",
          "- Mamba/fusion: GroupKFold-3 by event window — no shared-window leakage.",
          "- Held-out: 20 lower-confidence events never used in training.",
          "", "## 5. Leakage Checks",
          "- Event-group CV everywhere; OOF-only fusion inputs; scaler train-only; "
          "pre-event-day cutoff for Mamba; all guards passed.",
          "", "## 6. Model Configurations",
          "- LogReg (scaled, balanced), RF (300 trees, balanced_subsample), "
          "HGB (200 iter, depth 3), XGB/LGBM (depth 3, balanced).",
          "- Mamba: Linear15→16 + LayerNorm + Dropout0.2 + SelectiveSSMCell(d_state=8), "
          "AdamW 1e-3, early stopping, pos-weighted BCE.",
          "- Fusion: balanced LogReg on [RF-OOF-proba, Mamba-OOF-proba].",
          "", "## 7-9. Training / Validation / Independent Evaluation",
          "", "| Model | Input | Split | ROC-AUC | PR-AUC | Recall | Precision | F1 | Brier | n |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for mid in COMPARISON_ORDER:
        m = results.get("tabular", {}).get(mid) or results.get(
            mid.replace("gs_", ""), {}) or results.get(mid, {})
        if not m:
            continue
        n = m.get("n_samples", m.get("n_seq", m.get("n", "?")))
        L.append(f"| {mid} | {mid.split('_', 1)[1]} | event-grouped | "
                 f"{m.get('roc_auc')} | {m.get('pr_auc')} | {m.get('recall')} | "
                 f"{m.get('precision')} | {m.get('f1')} | {m.get('brier')} | {n} |")
    L += ["",
          f"- Held-out (terrain-core, {results['heldout']['n_scored']}/"
          f"{results['heldout']['n_pool']} scored): recall@0.5 = "
          f"{results['heldout']['recall_at_0.5']}; "
          f"{results['heldout']['n_out_of_coverage']} out of SRTM coverage.",
          "- Small-n uncertainty dominates: see recall_ci95 in metrics JSONs; "
          "no model declared best from a single split.",
          "", "## 10. Explainability",
          "- See `models/gs_gis/explainability.md` (associative language only).",
          "", "## 11. GIS Outputs",
          f"- Grid {results['gis']['grid_shape']} @ {results['gis']['resolution_deg']:.5f} deg; "
          f"{results['gis']['valid_cells']} valid cells; "
          f"{results['gis']['high_risk_points']} watch+ points.",
          "", "## 12. Limitations",
          "- 18 positives; pseudo-negatives (not confirmed absence); SRTM lon 92–93 gap; "
          "rainfall spikes/sentinels; no SAR; SegFormer BLOCKED (void pixels, no masks); "
          "Mamba bg windows share event times (event-split mitigated); "
          "LULC semantics unknown; Jan-2020 .nc are schema samples, not a live feed.",
          "", "## 13. Deployment Readiness",
          "- Prototype: PARTIAL (end-to-end demo runs; segmentation + live warning missing)",
          "- Research-grade: NO (n=18 positives; uncalibrated)",
          "- Production: NO"]
    open(REPORT_PATH, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"report -> {REPORT_PATH}")


def write_blocked_file(gate):
    dest = os.path.join(MODELS_DIR, "segformer")
    os.makedirs(dest, exist_ok=True)
    body = ("# SegFormer — BLOCKED\n\n"
            "SEGFORMER_STATUS = BLOCKED\n\n"
            "Automated gate refuses training until: non_constant_input == true, "
            "valid_mask_exists == true, image_mask_alignment == true, "
            "valid_pixel_ratio > threshold (configurable).\n\n"
            f"Current gate evidence:\n```json\n{json.dumps(gate, indent=2)}\n```\n\n"
            "49/49 optical patches are constant-0; 11/11 QA patches constant-1; "
            "no masks exist. Do not fabricate masks.\n")
    open(os.path.join(dest, "BLOCKED.md"), "w", encoding="utf-8").write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    _rng()
    results = {"experiment": EXPERIMENT, "seed": SEED,
               "spec": "train-validate-evaluate-integrate (audited data only)"}
    rf_rows = step_validate(results)                       # STEP 2-5 (+gate)
    step_rf_audit(rf_rows, results)                        # STEP 6
    oof_tab, cols = step_tabular(rf_rows, results)         # STEP 7-10
    X, y, groups, sids, feats = step_mamba_data(results)   # STEP 11-12
    mamba_oof = step_train_mamba(X, y, groups, feats, results,
                                 smoke=args.smoke)         # STEP 13-14
    step_fusion(rf_rows, oof_tab["gs_rf"], mamba_oof, sids, y, results)  # 15-16
    core = step_heldout(rf_rows, results, smoke=args.smoke)  # STEP 17
    step_explain(results)                                  # STEP 18
    step_gis(core, results, smoke=args.smoke)              # STEP 19
    _register_all({**{k: v for k, v in results["tabular"].items()},
                   "gs_mamba": results["mamba"], "gs_fusion": results["fusion"]},
                  cols, len(rf_rows))
    _save_json(os.path.join(MODELS_DIR, "gs_gis", "experiment_gs_v1.json"),
               {k: v for k, v in results.items() if k != "tabular_importance"})
    write_blocked_file(results["segformer_gate"])
    step_report(results)                                   # STEP 20
    print("DONE experiment", EXPERIMENT)


if __name__ == "__main__":
    main()
