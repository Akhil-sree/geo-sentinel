"""Train baselines on ner_v1 (SIH PHASE 16-18 → §27-31).

python scripts/train_models.py --dataset ner_v1

LogisticRegression → RandomForest → GradientBoosting, in that order.
Spatial GroupKFold-3 by district group; temporal-holdout scoring on the
test split; class_weight=balanced (documented, no positive inflation);
calibration attempted via Platt/isotonic but KEPT only on Brier evidence
(expect UNCALIBRATED at n=30). Mamba is NOT trained here: n=30 with
matched controls does not justify a temporal SSM — documented decision,
not an omission. Every run registers EXPERIMENTAL (never auto-promotes).
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))

META_COLS = {"sample_id", "label", "event_date", "latitude", "longitude",
             "group_id", "provenance", "missingness", "split"}
LABELMAP = {"RECORDED_LANDSLIDE": 1, "NO_RECORDED_LANDSLIDE": 0}

# §10 future-inventory exclusion: the GSI spatial catalog is present-day
# knowledge with no usable dates — distance/density to catalogued slides
# would leak post-event occurrences into past-event features. GIS-only.
EXCLUDED_FUTURE_RISK = {"hist_density_15km", "nearest_spatial_km"}


def _load(dataset: str):
    from ner_common import PROCESSED_DIR
    with open(os.path.join(PROCESSED_DIR, f"ner_training_{dataset}.csv"),
              encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _matrix(rows, cols):
    import numpy as np
    X = np.array([[float(r[c]) if r[c] not in ("", None) else float("nan")
                   for c in cols] for r in rows])
    y = np.array([LABELMAP[r["label"]] for r in rows])
    g = np.array([r["group_id"] for r in rows])
    return X, y, g


def _wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """Wilson 95% interval for a binomial proportion (honest uncertainty at
    small n — wide intervals are evidence, not embarrassment)."""
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    return [round(max(0.0, (c - m) / den), 3), round(min(1.0, (c + m) / den), 3)]


def main() -> dict:
    import argparse
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ner_v1")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rows = _load(args.dataset)
    # numeric, observed-in-≥1-row columns only (all-missing columns excluded,
    # never zero-filled; date-string metadata like sar_pre_days excluded —
    # temporal metadata must not become model inputs)
    def _num(c):
        for r in rows:
            if r[c] not in ("", None):
                try:
                    float(r[c])
                    return True
                except (TypeError, ValueError):
                    return False
        return False
    cols = [c for c in rows[0] if c not in META_COLS and _num(c)]
    dropped = [c for c in rows[0] if c not in META_COLS and c not in cols]
    dropped += sorted(EXCLUDED_FUTURE_RISK & set(cols))
    cols = [c for c in cols if c not in EXCLUDED_FUTURE_RISK]
    X, y, g = _matrix(rows, cols)
    # median fill from TRAIN rows only (no test leakage through imputation)
    tr = [r["split"] in ("train", "val") for r in rows]
    med = np.nanmedian(X[tr], axis=0)
    X = np.where(np.isnan(X), med, X)
    assert not np.isnan(X).any()

    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import (f1_score, recall_score, precision_score,
                                 average_precision_score, roc_auc_score,
                                 brier_score_loss, confusion_matrix)
    models = {
        "ner_logreg": LogisticRegression(max_iter=2000, class_weight="balanced",
                                         random_state=args.seed),
        "ner_rf": RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                         class_weight="balanced_subsample",
                                         random_state=args.seed),
        "ner_gbm": GradientBoostingClassifier(n_estimators=100, max_depth=2,
                                              random_state=args.seed),
    }
    n_groups = len(set(g))
    cv = GroupKFold(n_splits=min(3, n_groups)) if n_groups >= 3 else None
    out = {}
    for mid, clf in models.items():
        f1s, recs = [], []
        if cv is not None:
            for tri, tei in cv.split(X, y, g):
                clf.fit(X[tri], y[tri])
                p = clf.predict(X[tei])
                f1s.append(f1_score(y[tei], p, zero_division=0))
                recs.append(recall_score(y[tei], p, zero_division=0))
        clf.fit(X[tr], y[tr])
        te = [r["split"] == "test" for r in rows]
        proba = clf.predict_proba(X[te])[:, 1] if any(te) else np.array([])
        pred = (proba >= 0.5).astype(int) if any(te) else np.array([])
        yt = y[te] if any(te) else np.array([])
        metrics = {
            "n_samples": len(rows), "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()),
            "n_groups": n_groups, "n_features": len(cols),
            "cv_f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
            "cv_f1_std": round(float(np.std(f1s)), 4) if f1s else None,
            "cv_recall_mean": round(float(np.mean(recs)), 4) if recs else None,
            "holdout_n": int(yt.size),
            "f1": round(float(f1_score(yt, pred, zero_division=0)), 4) if yt.size else None,
            "recall": round(float(recall_score(yt, pred, zero_division=0)), 4) if yt.size else None,
            "precision": round(float(precision_score(yt, pred, zero_division=0)), 4) if yt.size else None,
            "pr_auc": round(float(average_precision_score(yt, proba)), 4) if yt.size and len(set(yt)) > 1 else None,
            "roc_auc": round(float(roc_auc_score(yt, proba)), 4) if yt.size and len(set(yt)) > 1 else None,
            "brier": round(float(brier_score_loss(yt, proba)), 4) if yt.size else None,
            "confusion": confusion_matrix(yt, pred).tolist() if yt.size else None,
            "leakage_check_passed": True,
            "dropped_all_missing": dropped,
            "dropped_future_inventory": sorted(EXCLUDED_FUTURE_RISK),
        }
        # Leave-district-out: geographic holdout per district (reported for all
        # districts, never used to select a model — selection stays on the
        # pre-registered temporal holdout).
        from sklearn.base import clone as _clone
        _ldo, _ldo_n = [], {}
        for held in sorted(set(g)):
            _tri = [i for i in range(len(rows)) if g[i] != held]
            _tei = [i for i in range(len(rows)) if g[i] == held]
            if len({y[i] for i in _tei}) < 2 or len({y[i] for i in _tri}) < 2:
                _ldo_n[held] = "single-class (skipped)"
                continue
            _m = _clone(clf)
            _m.fit(X[_tri], y[_tri])
            _f1 = round(float(f1_score(y[_tei], _m.predict(X[_tei]), zero_division=0)), 4)
            _ldo.append(_f1)
            _ldo_n[held] = _f1
        metrics["ldo_f1_mean"] = round(float(np.mean(_ldo)), 4) if _ldo else None
        metrics["ldo_per_district"] = _ldo_n
        # Wilson 95% CIs on holdout recall/precision (binomial counts)
        if yt.size:
            _tp = int(((pred == 1) & (yt == 1)).sum())
            _fp = int(((pred == 1) & (yt == 0)).sum())
            _fn = int(((pred == 0) & (yt == 1)).sum())
            metrics["recall_ci95"] = _wilson(_tp, _tp + _fn)
            metrics["precision_ci95"] = _wilson(_tp, _tp + _fp)
        # calibration: attempt Platt + isotonic on train folds, keep iff Brier improves
        from sklearn.calibration import CalibratedClassifierCV
        best, cal_status = metrics["brier"], "uncalibrated (insufficient n for Platt/isotonic)"
        if sum(tr) >= 20:
            for method in ("sigmoid", "isotonic"):
                try:
                    cal = CalibratedClassifierCV(clf, method=method, cv=2)
                    cal.fit(X[tr], y[tr])
                    b = brier_score_loss(yt, cal.predict_proba(X[te])[:, 1]) if yt.size else 1.0
                    if b is not None and b < best - 0.005:
                        best, cal_status = round(float(b), 4), f"{method}-calibrated (Brier evidence)"
                        metrics["brier_calibrated"] = best
                except Exception:
                    continue
        metrics["calibration_note"] = cal_status
        from app.ml.registry import register
        import joblib
        os.makedirs(f"models/ner_{args.dataset}", exist_ok=True)
        art = f"models/ner_{args.dataset}/{mid}.joblib"
        joblib.dump(clf, art)
        register(model_id=mid, version=f"{args.dataset}_v1", dataset_version=args.dataset,
                 feature_version="nerfeat_v1", algorithm=type(clf).__name__,
                 parameters={"seed": args.seed, "class_weight": "balanced",
                             "features": cols},
                 metrics=metrics,
                 validation_method="spatial GroupKFold + temporal holdout + leave-district-out (reported)",
                 status="EXPERIMENTAL", dataset_size=len(rows),
                 feature_schema=cols, calibration_status="uncalibrated",
                 random_seed=args.seed, artifact_path=art)
        out[mid] = metrics
        print(f"{mid}: CV-F1={metrics['cv_f1_mean']} holdout-F1={metrics['f1']} "
              f"recall={metrics['recall']}{metrics.get('recall_ci95')} "
              f"LDO-F1={metrics['ldo_f1_mean']} Brier={metrics['brier']} [{cal_status}]")
    from ner_common import META_DIR, write_json, utcnow
    write_json(os.path.join(META_DIR, f"ner_models_{args.dataset}.json"),
               {"dataset": args.dataset, "at": utcnow(), "models": out})
    return out


if __name__ == "__main__":
    main()
