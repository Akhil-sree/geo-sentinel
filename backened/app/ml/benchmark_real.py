"""5-way benchmark on comparable held-out data (Phase 7).

Same held-out ZONES (Z7, Z8) for every model, native inputs each
("appropriately equivalent" — a sequence model and a terrain model cannot
take identical inputs):
  heuristic  — MockTemporalModel dynamic score on real sequences (>=0.5)
  logreg/rf/gbm — retrained on non-holdout zone-years (events_v2, Z1–Z6),
                   predicted on holdout zone-years (Z7,Z8 × 2022–24)
  mamba      — mamba_2026_03 checkpoint on holdout sequences
  fusion     — expert 0.4/0.6 of event-RF static + mamba dynamic on the
               6 holdout sequence samples (illustrative, labeled)

Reports precision/recall/F1/PR-AUC/Brier/CM per model. Prints JSON.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

VAL_ZONES = ["Z7", "Z8"]


def _scores(y_true, proba):
    import numpy as np
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        confusion_matrix,
        precision_recall_fscore_support,
        roc_auc_score,
    )
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    pred = (proba >= 0.5).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, pred, average="binary", zero_division=0)
    try:
        roc = float(roc_auc_score(y_true, proba))
    except Exception:
        roc = None
    try:
        prauc = float(average_precision_score(y_true, proba))
    except Exception:
        prauc = None
    return {"precision": round(float(prec), 4), "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(roc, 4) if roc is not None else None,
            "pr_auc": round(prauc, 4) if prauc is not None else None,
            "brier": round(float(brier_score_loss(y_true, proba)), 4),
            "confusion_matrix": confusion_matrix(y_true, pred).tolist(),
            "n": len(y_true)}


def main():
    import csv
    import json

    import numpy as np
    import torch  # FIRST: native libs must load before sklearn's OpenMP
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    from app.database import SessionLocal
    from app.ml.dataset import build_event_dataset
    from app.ml.mamba_model import (
        get_temporal_model,  # noqa: E402 (after TORCH ok)
    )
    from app.models_db import Zone

    out = {}
    # ---- static models: retrain on Z1–Z6 zone-years, test Z7/Z8 ----
    db = SessionLocal()
    zones = db.query(Zone).all()
    db.close()
    X, y, groups, meta = build_event_dataset(zones)
    keys = meta["keys"]
    tr = [i for i, (zid, _) in enumerate(keys) if zid not in VAL_ZONES]
    va = [i for i, (zid, _) in enumerate(keys) if zid in VAL_ZONES]
    statics = {
        "logreg": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "rf": RandomForestClassifier(n_estimators=300, max_depth=6,
                                     min_samples_leaf=2, class_weight="balanced",
                                     random_state=42, n_jobs=-1),
        "gbm": GradientBoostingClassifier(n_estimators=100, max_depth=2,
                                          random_state=42),
    }
    static_proba = {}
    for name, clf in statics.items():
        clf.fit(X[tr], y[tr])
        p = clf.predict_proba(X[va])[:, 1]
        static_proba[name] = p
        out[name] = {"inputs": "terrain6 (events_v2 holdout zone-years)",
                     **_scores(y[va], p)}

    # ---- sequence models on real holdout sequences ----
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    z = np.load(os.path.join(base, "processed", "sequences_v1.npz"),
                allow_pickle=True)
    Xs, ys = z["X"], z["y"]
    with open(os.path.join(base, "processed", "samples_v1.csv"),
              encoding="utf-8") as f:
        zids = [r["zone_id"] for r in csv.DictReader(f)]
    hva = [i for i, zid in enumerate(zids) if zid in VAL_ZONES]
    Xh, yh = Xs[hva], ys[hva]

    tm = get_temporal_model()
    hp = np.asarray([tm.predict(list(seq))["dynamic_score"] for seq in Xh])
    out["heuristic"] = {"inputs": "real 48h sequences (heuristic saturation)",
                        "backend": tm.backend(), **_scores(yh, hp)}

    ckpt = os.path.join(os.path.dirname(__file__), "..", "..",
                        "models", "mamba", "mamba_2026_03", "checkpoint.pt")
    from app.ml.mamba_model import SelectiveSSMCell
    # Local trusted artifact, dict-only access below — safe deserialization.
    ckpt_data = torch.load(ckpt, map_location="cpu", weights_only=True)
    model = SelectiveSSMCell()
    model.load_state_dict(ckpt_data["state_dict"])
    model.eval()
    with torch.no_grad():
        mp = model(torch.tensor(Xh)).squeeze().numpy()
    out["mamba"] = {"inputs": "real 48h sequences (mamba_2026_03)",
                    **_scores(yh, mp)}

    # ---- fusion on the 6 holdout sequence samples ----
    # static score per sample = event-RF proba for that zone's terrain
    db = SessionLocal()
    zones = {zz.id: zz for zz in db.query(Zone).all()}
    db.close()
    from app.ml.rf_model import RFModel
    rf_full = RFModel()
    static_s, dyn_s, yt = [], [], []
    for i, zid in enumerate([zids[k] for k in hva]):
        try:
            static_s.append(rf_full.predict(zones[zid])["static_score"])
        except Exception:
            static_s.append(0.5)
        dyn_s.append(float(mp[i]))
        yt.append(int(yh[i]))
    fused = [0.4 * s + 0.6 * d for s, d in zip(static_s, dyn_s, strict=False)]
    out["fusion_expert"] = {"inputs": "static RF + mamba (0.4/0.6)",
                            "note": "illustrative n=6 (not validation)",
                            **_scores(yt, fused)}
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main()
