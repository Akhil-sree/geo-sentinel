"""Evidence-based fusion analysis (Phase 8).

Produces a measured ablation table on events_v2 (spatial GroupKFold-3 by
district — same splits for every row):
  logreg / rf / gbm          — single static models (real CV metrics)
  stacking                   — meta-LogReg on out-of-fold probas (LEARNED fusion)
  expert_rule                — documented separately (needs live dynamic scores;
                               NOT ML-validated; sensitivity note below)

Plus an n=8 ILLUSTRATIVE agreement check: real pipeline outputs
(static/dynamic/fused at t=168) vs seed zone labels. This demonstrates the
comparison machinery on measured outputs — it is NOT validation (n=8).

Expert-weight sensitivity: fusion_v1 weights (0.4/0.6) are config parameters;
the illustrative check reports agreement at 0.2/0.8, 0.4/0.6, 0.6/0.4 so the
choice is examined, not assumed.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import (precision_recall_fscore_support, roc_auc_score,
                             average_precision_score, brier_score_loss)


def _row(y, proba):
    pred = (np.asarray(proba) >= 0.5).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y, pred, average="binary", zero_division=0)
    try:
        roc = float(roc_auc_score(y, proba))
    except Exception:
        roc = None
    try:
        prauc = float(average_precision_score(y, proba))
    except Exception:
        prauc = None
    return {"precision": round(float(prec), 4), "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(roc, 4) if roc is not None else None,
            "pr_auc": round(prauc, 4) if prauc is not None else None,
            "brier": round(float(brier_score_loss(y, proba)), 4)}


def run_ablation():
    from app.database import SessionLocal
    from app.models_db import Zone
    from app.ml.dataset import build_event_dataset, check_leakage, FEATURES
    from app.ml import registry

    db = SessionLocal()
    zones = db.query(Zone).all()
    db.close()
    X, y, groups, meta = build_event_dataset(zones)
    check_leakage(meta["keys"], groups)
    cv = GroupKFold(n_splits=3)
    models = {
        "logreg": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "rf": RandomForestClassifier(n_estimators=300, max_depth=6,
                                     min_samples_leaf=2, class_weight="balanced",
                                     random_state=42, n_jobs=-1),
        "gbm": GradientBoostingClassifier(n_estimators=100, max_depth=2,
                                          random_state=42),
    }
    table, oof = {}, {}
    for name, clf in models.items():
        p = cross_val_predict(clf, X, y, groups=groups, cv=cv,
                              method="predict_proba")[:, 1]
        oof[name] = p
        table[name] = {"kind": "single static model", **_row(y, p)}
    # LEARNED fusion: stacking meta-model on OOF probas (same splits)
    S = np.column_stack([oof["logreg"], oof["rf"], oof["gbm"]])
    meta_clf = LogisticRegression(max_iter=2000)
    sp = cross_val_predict(meta_clf, S, y, groups=groups, cv=cv,
                           method="predict_proba")[:, 1]
    meta_clf.fit(S, y)  # weights evidence (not deployed)
    table["stacking"] = {"kind": "LEARNED fusion (OOF stacking)",
                         **_row(y, sp),
                         "meta_weights": [round(float(w), 3)
                                          for w in meta_clf.coef_[0]]}
    registry.register(
        model_id="fusion_stacking", version="stack_v1",
        dataset_version=meta["dataset_version"],
        feature_version=meta.get("feature_version", "?"),
        algorithm="LogisticRegression-on-OOF", parameters={},
        metrics={**table["stacking"], "n_samples": meta["n_samples"]},
        validation_method="spatial GroupKFold-3 by district",
        status="DEMO", dataset_size=meta["n_samples"],
        feature_schema=["oof_logreg", "oof_rf", "oof_gbm"],
        calibration_status="uncalibrated", random_seed=42)
    table["expert_rule"] = {
        "kind": "config weights static=0.4/dynamic=0.6 (fusion_v1)",
        "note": ("NOT ML-validated on held-out labels — combines static ML "
                 "with live dynamic scores that have no historical ground "
                 "truth. See illustrative agreement below + sensitivity.")}

    # Illustrative n=8 agreement on measured pipeline outputs
    table["illustrative_n8"] = _illustrative()
    return table


def _illustrative():
    """Real pipeline outputs (t=168) vs seed HIGH labels — machinery demo."""
    from app.services.sim import run_pipeline
    from app.seed import ZONES
    label = {z["id"]: (1 if z["label"] == 2 else 0) for z in ZONES}
    try:
        pipe = {r["zone_id"]: r for r in run_pipeline(168)}
    except Exception as e:
        return {"status": "pipeline failed", "error": str(e)[:150]}
    from app.ml.fusion import fuse
    rows = {}
    for sw, dw in [(0.2, 0.8), (0.4, 0.6), (0.6, 0.4)]:
        agree_s = agree_d = agree_f = n = 0
        for zid, lab in label.items():
            r = pipe.get(zid)
            if not r:
                continue
            n += 1
            agree_s += ((r["static_score"] >= 0.5) == lab)
            agree_d += ((r["dynamic_score"] >= 0.5) == lab)
            f = (sw * r["static_score"] + dw * r["dynamic_score"])
            agree_f += ((f >= 0.5) == lab)
        rows[f"w{sw}/{dw}"] = {"static_only": round(agree_s / n, 3),
                               "dynamic_only": round(agree_d / n, 3),
                               "fused": round(agree_f / n, 3), "n": n}
    return {"status": "ILLUSTRATIVE n=8 agreement (not validation)",
            "weights_sensitivity": rows}
