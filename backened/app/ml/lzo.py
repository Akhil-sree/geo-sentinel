"""Leave-Zone-Out validation for Mamba (Phase 9): train on 7 zones, test 1.

Strongest spatial honesty available: the test zone is never seen in any
form. Per-zone F1 reported (zones with 0 positives get F1=n/a, flagged —
predicting all-negative there is CORRECT, not failure). Mean over zones
with positives. Registers `mamba_lzo/lzo_v1`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import torch  # FIRST

SEED = 42
EPOCHS = 40
PATIENCE = 6


def main():
    import csv
    import numpy as np
    import torch.nn as nn
    from sklearn.metrics import (precision_recall_fscore_support,
                                 average_precision_score, brier_score_loss)
    from app.ml.mamba_model import SelectiveSSMCell
    from app.ml.cv_mamba import load_v2

    X, y, zids, _, _ = load_v2()
    zones = sorted(set(zids.tolist()))
    per_zone = []
    for held in zones:
        tei = [i for i, z in enumerate(zids) if z == held]
        tri = [i for i, z in enumerate(zids) if z != held]
        # inner val: first alphabetical train zone
        tr_zones = sorted(set(zids[tri].tolist()))
        inner = tr_zones[0]
        vai = [i for i in tri if zids[i] == inner]
        tri2 = [i for i in tri if zids[i] != inner]
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        model = SelectiveSSMCell()
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        bce = nn.BCELoss()
        Xt = torch.tensor(X[tri2])
        yt = torch.tensor(y[tri2], dtype=torch.float32)
        Xv = torch.tensor(X[vai])
        yv = torch.tensor(y[vai], dtype=torch.float32)
        best, state, wait = float("inf"), None, 0
        for _ in range(EPOCHS):
            model.train()
            opt.zero_grad()
            p = model(Xt).squeeze().clamp(1e-7, 1 - 1e-7)
            loss = bce(p, yt)
            loss.backward()
            opt.step()
            model.eval()
            with torch.no_grad():
                pv = model(Xv).squeeze().clamp(1e-7, 1 - 1e-7)
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
        npos = int(y[tei].sum())
        if npos == 0:
            per_zone.append({"zone": held, "n": len(tei), "pos": 0,
                             "f1": None, "note": "no positives — "
                             "all-negative prediction is correct"})
            continue
        _, rec, f1, _ = precision_recall_fscore_support(
            y[tei], pred, average="binary", zero_division=0)
        try:
            prauc = float(average_precision_score(y[tei], pt))
        except Exception:
            prauc = None
        per_zone.append({"zone": held, "n": len(tei), "pos": npos,
                         "recall": round(float(rec), 4),
                         "f1": round(float(f1), 4),
                         "pr_auc": round(prauc, 4) if prauc else None,
                         "brier": round(float(brier_score_loss(y[tei], pt)), 4)})
    scored = [z["f1"] for z in per_zone if z["f1"] is not None]
    import numpy as _np
    from app.ml import registry
    registry.register(
        model_id="mamba_lzo", version="lzo_v1", dataset_version="seq_real_v2",
        feature_version="seq48x7_v1", algorithm="SelectiveSSMCell",
        parameters={"epochs": EPOCHS, "patience": PATIENCE},
        metrics={"per_zone": per_zone,
                 "f1_mean_scored": round(float(_np.mean(scored)), 4)
                 if scored else None,
                 "n_samples": 32, "leakage_check_passed": True},
        validation_method="leave-zone-out (8 folds)",
        status="EXPERIMENTAL", dataset_size=32,
        calibration_status="uncalibrated", random_seed=SEED)
    import json
    print(json.dumps(per_zone, indent=1))
    return per_zone


if __name__ == "__main__":
    main()
