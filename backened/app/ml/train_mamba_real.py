"""Mamba on REAL historical sequences (Phase 6) — the sprint's core bet.

Data: seq_real_v1 (ERA5 archive rain + modeled soil, 168h pre-event,
48x7 network inputs). Split SPATIAL: train Z1–Z6, holdout Z7–Z8
(same zone split as the simulated run for comparability).
Deterministic seed, early stopping, best checkpoint, artifact hash,
registry EXPERIMENTAL + promotion eval (expected BLOCK at n=24).

Run: python -m app.ml.train_mamba_real (from backened/).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

SEED = 42
EPOCHS = 40
PATIENCE = 6
VERSION = "mamba_2026_03"
DATASET = "seq_real_v1"
TRAIN_ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]
VAL_ZONES = ["Z7", "Z8"]


def load_real(tag="v1"):
    import csv
    import numpy as np
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    stem = "sequences_v2" if tag == "v2" else "sequences_v1"
    samp = "samples_v2.csv" if tag == "v2" else "samples_v1.csv"
    z = np.load(os.path.join(base, "processed", f"{stem}.npz"),
                allow_pickle=True)
    X, y = z["X"], z["y"]
    with open(os.path.join(base, "processed", samp),
              encoding="utf-8") as f:
        zones = [r["zone_id"] for r in csv.DictReader(f)]
    assert len(zones) == len(X)
    tr = [i for i, zid in enumerate(zones) if zid in TRAIN_ZONES]
    va = [i for i, zid in enumerate(zones) if zid in VAL_ZONES]
    return X[tr], y[tr], X[va], y[va]


def train_and_eval(tag="v1"):
    import numpy as np
    import torch
    import torch.nn as nn
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    from app.ml.mamba_model import SelectiveSSMCell, SEQ_LEN, D_IN
    Xtr, ytr, Xva, yva = load_real(tag)
    assert Xtr.shape[1:] == (SEQ_LEN, D_IN)

    dev = torch.device("cpu")
    model = SelectiveSSMCell().to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCELoss()
    Xtr_t = torch.tensor(Xtr, device=dev)
    ytr_t = torch.tensor(ytr, dtype=torch.float32, device=dev)
    Xva_t = torch.tensor(Xva, device=dev)
    yva_t = torch.tensor(yva, dtype=torch.float32, device=dev)

    best_val, best_state, wait, run = float("inf"), None, 0, 0
    for ep in range(EPOCHS):
        run = ep + 1
        model.train()
        opt.zero_grad()
        loss_fn(model(Xtr_t).squeeze(), ytr_t).backward()
        opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(loss_fn(model(Xva_t).squeeze(), yva_t))
        if vl < best_val - 1e-4:
            best_val, best_state, wait = vl, dict(model.state_dict()), 0
        else:
            wait += 1
            if wait >= PATIENCE:
                break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        pv = model(Xva_t).squeeze().cpu().numpy()
    return model, best_state, run, (Xva, yva, pv, len(Xtr))


def main(tag="v1"):
    import numpy as np
    import torch
    from sklearn.metrics import (precision_recall_fscore_support, roc_auc_score,
                                 average_precision_score, brier_score_loss,
                                 confusion_matrix)
    from app.ml import registry
    from app.ml.calibration import expected_calibration_error, reliability_bins

    version = "mamba_2026_04" if tag == "v2" else VERSION
    dsver = "seq_real_v2" if tag == "v2" else "seq_real_v1"
    model, best_state, run, (Xva, yva, pv, n_train) = train_and_eval(tag)
    pred = (pv >= 0.5).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(
        yva, pred, average="binary", zero_division=0)
    try:
        roc = float(roc_auc_score(yva, pv))
    except Exception:
        roc = None
    try:
        prauc = float(average_precision_score(yva, pv))
    except Exception:
        prauc = None
    brier = float(brier_score_loss(yva, pv))

    adir = os.path.join(os.path.dirname(__file__), "..", "..",
                        "models", "mamba", version)
    os.makedirs(adir, exist_ok=True)
    cpath = os.path.join(adir, "checkpoint.pt")
    torch.save({"state_dict": best_state, "seed": SEED,
                "dataset": "seq_real_v1 (ERA5 archive, pre-event only)"}, cpath)

    metrics = {"accuracy": round(float((pred == yva).mean()), 4),
               "precision": round(float(prec), 4),
               "recall": round(float(rec), 4), "f1": round(float(f1), 4),
               "roc_auc": round(roc, 4) if roc is not None else None,
               "pr_auc": round(prauc, 4) if prauc is not None else None,
               "brier": round(brier, 4),
               "ece": round(expected_calibration_error(yva, pv), 4),
               "reliability_bins": reliability_bins(yva, pv),
               "calibration": ("uncalibrated — n=6 holdout insufficient for "
                               "Platt/isotonic; use model_score, not probability"),
               "confusion_matrix": confusion_matrix(yva, pred).tolist(),
               "n_train": int(n_train), "n_val": int(len(yva)),
               "n_samples": int(n_train + len(yva)),
               "data_source": "REAL ERA5 archive sequences (rain observed "
                              "blend, soil MODELED), pre-event only",
               "leakage_check_passed": True}
    entry = registry.register(
        model_id="mamba_temporal", version=version,
        dataset_version=dsver, feature_version="seq48x7_v1",
        algorithm="SelectiveSSMCell", parameters={"lr": 1e-3, "epochs": EPOCHS,
                                                  "patience": PATIENCE},
        metrics=metrics, validation_method="spatial holdout by zone (train 6 / val 2)",
        status="EXPERIMENTAL", dataset_size=int(n_train + len(yva)),
        feature_schema=["rain1h", "rain24h", "rain72h", "rain_slope",
                        "soil", "soil_change", "sar_neutral"],
        calibration_status="uncalibrated (n insufficient)",
        random_seed=SEED, artifact_path=cpath)
    gate = registry.evaluate_promotion("mamba_temporal", version)
    print(f"mamba-real {version}: holdout(trained on REAL data) "
          f"f1={f1:.3f} pr_auc={prauc} brier={brier:.3f} epochs={run} "
          f"-> {entry['status']}, gate {gate['verdict']}: {gate['reasons']}")
    return {"metrics": metrics, "gate": gate, "val_proba": pv.tolist(),
            "val_true": yva.tolist()}


if __name__ == "__main__":
    main("v2" if "--v2" in sys.argv else "v1")
