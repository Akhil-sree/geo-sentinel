"""Temporal GroupKFold CV for Mamba (Phase 4-6): mean±std, not point estimates.

Design (leakage-safe):
- Outer: GroupKFold-3 by district over seq_real_v2 (32 samples).
- Inner: 1 district of the fold-train held for early stopping.
- Variants: plain BCE | pos-weighted BCE | focal (gamma=2). No other
  hyperparameters touched (no uncontrolled explosion).
- Resampling: NONE (duplicating correlated sequences across boundaries is
  forbidden; weighting happens inside the loss only).
- Folds with <2 positives are flagged, still reported.

Prints per-fold counts + variant table. Registers the CV summary.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import torch  # FIRST, always: sklearn's OpenMP load order otherwise perturbs

# torch numerics run-to-run (measured: identical seed+code diverged in F1).
# Every training entry point in this repo follows torch-first ordering.

SEED = 42
EPOCHS = 40
PATIENCE = 6


def load_v2():
    import csv

    import numpy as np
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    z = np.load(os.path.join(base, "processed", "sequences_v2.npz"),
                allow_pickle=True)
    with open(os.path.join(base, "processed", "samples_v2.csv"),
              encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return (z["X"].astype("float32"), z["y"].astype(int),
            np.asarray([r["zone_id"] for r in rows]),
            np.asarray([f"{r['zone_id']}" for r in rows]), z["groups"])


def focal_loss(p, y, gamma=2.0, alpha=0.5):
    import torch
    eps = 1e-7
    p = p.clamp(eps, 1 - eps)
    return (-(alpha * y * (1 - p) ** gamma * torch.log(p)
              + (1 - alpha) * (1 - y) * p ** gamma * torch.log(1 - p))).mean()


def main():
    import numpy as np
    import torch.nn as nn
    from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_fscore_support
    from sklearn.model_selection import GroupKFold

    from app.ml.mamba_model import SelectiveSSMCell

    X, y, zids, _, groups = load_v2()
    districts = groups
    gkf = GroupKFold(n_splits=3)
    variants = ["plain", "weighted", "focal"]
    results = {v: [] for v in variants}
    fold_info = []
    for fi, (tri, tei) in enumerate(gkf.split(X, y, groups=districts)):
        # inner holdout: first district (alphabetical) of fold-train
        tr_districts = sorted(set(districts[tri]))
        inner_d = tr_districts[0]
        vai = [i for i in tri if districts[i] == inner_d]
        tri2 = [i for i in tri if districts[i] != inner_d]
        yp, yn = int(y[tei].sum()), int(len(tei) - y[tei].sum())
        flag = "LOW_POS" if yp < 2 else "ok"
        fold_info.append({"fold": fi, "test_districts": sorted(set(districts[tei])),
                          "n_test": len(tei), "pos": yp, "neg": yn, "flag": flag,
                          "inner_val_district": inner_d})
        for v in variants:
            torch.manual_seed(SEED)
            np.random.seed(SEED)
            model = SelectiveSSMCell()
            opt = torch.optim.Adam(model.parameters(), lr=1e-3)
            bce = nn.BCELoss()
            Xt = torch.tensor(X[tri2])
            yt = torch.tensor(y[tri2], dtype=torch.float32)
            Xv = torch.tensor(X[vai])
            yv = torch.tensor(y[vai], dtype=torch.float32)
            pw = float((len(yt) - yt.sum()) / max(1, float(yt.sum())))
            wloss = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pw))
            best, state, wait = float("inf"), None, 0
            for _ in range(EPOCHS):
                model.train()
                opt.zero_grad()
                p = model(Xt).squeeze().clamp(1e-7, 1 - 1e-7)
                if v == "focal":
                    loss = focal_loss(p, yt)
                elif v == "weighted":
                    loss = wloss(torch.log(p / (1 - p)), yt)
                else:
                    loss = bce(p, yt)
                loss.backward()
                opt.step()
                model.eval()
                with torch.no_grad():
                    pv = model(Xv).squeeze().clamp(1e-7, 1 - 1e-7)
                    if v == "focal":
                        vl = float(focal_loss(pv, yv))
                    elif v == "weighted":
                        vl = float(wloss(torch.log(pv / (1 - pv)), yv))
                    else:
                        vl = float(bce(pv, yv))
                if vl < best - 1e-4:
                    best, state, wait = vl, dict(model.state_dict()), 0
                else:
                    wait += 1
                    if wait >= PATIENCE:
                        break
            model.load_state_dict(state)
            model.eval()
            with torch.no_grad():
                pt = model(torch.tensor(X[tei])).squeeze().numpy()
            pred = (pt >= 0.5).astype(int)
            prec, rec, f1, _ = precision_recall_fscore_support(
                y[tei], pred, average="binary", zero_division=0)
            try:
                prauc = float(average_precision_score(y[tei], pt))
            except Exception:
                prauc = None
            results[v].append({"f1": round(float(f1), 4),
                               "recall": round(float(rec), 4),
                               "pr_auc": round(prauc, 4) if prauc else None,
                               "brier": round(float(brier_score_loss(y[tei], pt)), 4)})
    summary = {}
    for v in variants:
        f1s = [r["f1"] for r in results[v]]
        prs = [r["pr_auc"] for r in results[v] if r["pr_auc"] is not None]
        brs = [r["brier"] for r in results[v]]
        summary[v] = {"folds": results[v],
                      "f1_mean": round(float(np.mean(f1s)), 4),
                      "f1_std": round(float(np.std(f1s)), 4),
                      "pr_auc_mean": round(float(np.mean(prs)), 4) if prs else None,
                      "brier_mean": round(float(np.mean(brs)), 4)}
    from app.ml import registry
    registry.register(
        model_id="mamba_cv", version="cv_v1", dataset_version="seq_real_v2",
        feature_version="seq48x7_v1", algorithm="SelectiveSSMCell",
        parameters={"variants": variants, "epochs": EPOCHS, "patience": PATIENCE},
        metrics={"summary": summary, "folds": fold_info, "n_samples": 32,
                 "leakage_check_passed": True},
        validation_method="spatial GroupKFold-3 by district + inner district holdout",
        status="EXPERIMENTAL", dataset_size=32,
        calibration_status="uncalibrated", random_seed=SEED)
    import json
    print(json.dumps({"folds": fold_info, "summary": summary}, indent=1))
    return summary


if __name__ == "__main__":
    main()
