"""Standalone training entry points.

- main(): legacy n=8 zone-label RF (kept for the production static path).
- main_event(): event-level baseline comparison — LogisticRegression vs
  RandomForest on the zone-year dataset (n=24) with spatial GroupKFold by
  district, Platt calibration attempt, registry logging. Honest small-data
  ML: metrics are what they are; winner stays DEMO until the promotion
  gate (n>=50, validated F1/PR-AUC, calibration) passes.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.ml.rf_model import MODEL_DIR, VERSION, train
from app.models_db import Zone
from app.seed import ZONES


def main():
    db = SessionLocal()
    zones = db.query(Zone).all()
    if not zones:
        raise RuntimeError("no zones — run seed() first (app startup does this)")
    labels = [next(z["label"] for z in ZONES if z["id"] == zz.id) for zz in zones]
    meta = train(zones, labels, version=VERSION)
    db.close()
    print("trained →", os.path.join(MODEL_DIR, VERSION), "| cv_accuracy =", meta["cv_accuracy"])
    return meta


def main_event(tag="v2"):
    """Compare LogReg/RF/GBM on the event dataset; register all.

    tag=v2: terrain6. tag=v3: terrain6 + 2 REAL GSI spatial features
    (same 24 samples — feature enrichment, not sample inflation).
    Model ids gain a _v3 suffix for v3 so the registry keeps both."""
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        brier_score_loss,
        confusion_matrix,
        precision_recall_fscore_support,
        roc_auc_score,
    )
    from sklearn.model_selection import GroupKFold, cross_val_predict

    from app.ml import registry
    from app.ml.calibration import expected_calibration_error, reliability_bins
    from app.ml.dataset import FEATURES, V3_FEATURES, build_event_dataset, check_leakage

    db = SessionLocal()
    zones = db.query(Zone).all()
    db.close()
    X, y, groups, meta = build_event_dataset(zones, version=tag)
    check_leakage(meta["keys"], groups)
    schema = V3_FEATURES if tag == "v3" else FEATURES
    suffix = "_v3" if tag == "v3" else ""

    cands = {
        "logreg": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "rf_event": RandomForestClassifier(n_estimators=300, max_depth=6,
                                           min_samples_leaf=2,
                                           class_weight="balanced",
                                           random_state=42, n_jobs=-1),
        # Gradient boosting: sklearn-native, no new dependency (rule: prefer
        # stdlib/installed deps; XGBoost unjustified at n=24).
        "gbm_event": GradientBoostingClassifier(n_estimators=100, max_depth=2,
                                                random_state=42),
    }
    cv = GroupKFold(n_splits=3)
    out = {}
    for name, clf in cands.items():
        try:
            proba = cross_val_predict(clf, X, y, groups=groups, cv=cv,
                                      method="predict_proba")[:, 1]
            pred = (proba >= 0.5).astype(int)
        except Exception as e:
            out[name] = {"error": str(e)[:200]}
            continue
        prec, rec, f1, _ = precision_recall_fscore_support(
            y, pred, average="binary", zero_division=0)
        _f1m = precision_recall_fscore_support(
            y, pred, average="macro", zero_division=0)[2]
        _f1w = precision_recall_fscore_support(
            y, pred, average="weighted", zero_division=0)[2]
        try:
            roc = float(roc_auc_score(y, proba))
        except Exception:
            roc = None
        try:
            pr = float(average_precision_score(y, proba))
        except Exception:
            pr = None
        brier = float(brier_score_loss(y, proba))
        ece = expected_calibration_error(y, proba)
        # Calibration bake-off: Platt (sigmoid) vs isotonic; keep the winner
        # only if Brier improves, else stay honestly uncalibrated.
        best = {"method": "uncalibrated", "brier": brier, "proba": proba}
        for method in ("sigmoid", "isotonic"):
            try:
                cal = CalibratedClassifierCV(clf, method=method, cv=2)
                cp = cross_val_predict(cal, X, y, groups=groups, cv=cv,
                                       method="predict_proba")[:, 1]
                cb = float(brier_score_loss(y, cp))
                if cb < best["brier"]:
                    best = {"method": method, "brier": cb, "proba": cp}
            except Exception:
                continue
        cal_status = (f"{best['method']} (Brier {best['brier']:.3f})"
                      if best["method"] != "uncalibrated"
                      else "uncalibrated — use model_score, not probability")
        metrics = {"accuracy": round(float(accuracy_score(y, pred)), 4),
                   "precision": round(float(prec), 4),
                   "recall": round(float(rec), 4), "f1": round(float(f1), 4),
                   "f1_macro": round(float(_f1m), 4),
                   "f1_weighted": round(float(_f1w), 4),
                   "roc_auc": round(roc, 4) if roc is not None else None,
                   "pr_auc": round(pr, 4) if pr is not None else None,
                   "brier": round(brier, 4),
                   "brier_calibrated": round(best["brier"], 4),
                   "ece": round(ece, 4),
                   "calibration": cal_status,
                   "reliability_bins": reliability_bins(y, best["proba"]),
                   "confusion_matrix": confusion_matrix(y, pred).tolist(),
                   "leakage_check_passed": True}
        # Fit final artifact on all data
        clf.fit(X, y)
        import joblib
        mid = f"{name}{suffix}"
        aver = f"event_{mid}_v1"
        adir = os.path.join(MODEL_DIR, aver)
        os.makedirs(adir, exist_ok=True)
        apath = os.path.join(adir, "model.joblib")
        joblib.dump(clf, apath)
        entry = registry.register(
            model_id=mid, version=aver,
            dataset_version=meta["dataset_version"],
            feature_version=meta.get("feature_version", "?"),
            algorithm=type(clf).__name__, parameters=clf.get_params(),
            metrics={**metrics, "n_samples": meta["n_samples"],
                     "n_positive": meta["n_positive"]},
            validation_method="spatial GroupKFold-3 by district",
            status="DEMO",  # DEMO: promotion gate (n>=50) not met
            dataset_size=meta["n_samples"], feature_schema=schema,
            calibration_status=cal_status, random_seed=42,
            artifact_path=apath)
        registry.evaluate_promotion(mid, aver)
        out[mid] = {"metrics": metrics, "registry": entry["status"],
                    "promotion": registry.all_models()[-1]["promotion_status"]}
    print("event comparison ->", {k: v.get("metrics", v) for k, v in out.items()})
    return out

if __name__ == "__main__":
    main()
