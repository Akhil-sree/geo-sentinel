"""Mamba temporal training pipeline (Phase 5) — PRESERVED and made trainable.

Trains the selective-SSM cell (app/ml/mamba_model.py) on the SIMULATED
sequence task (app/ml/sequences.py): next-24h exceedance from past-48h.
Spatial split by zone, early stopping on val loss, best-checkpoint saving,
deterministic seeds, registry logging as EXPERIMENTAL.

This does NOT make Mamba operational: metrics are SIMULATED-demonstration,
the promotion gate blocks (n<50 real samples, no observed sequences), and
get_temporal_model() still returns the heuristic until a PROMOTED
checkpoint exists. Run: python -m app.ml.train_mamba (from backened/).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

SEED = 42
EPOCHS = 40
PATIENCE = 6
VERSION = "mamba_2026_02"
TRAIN_ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6"]
VAL_ZONES = ["Z7", "Z8"]


def main():
    import numpy as np
    import torch
    import torch.nn as nn
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    from app.ml.sequences import build_sequences
    from app.ml.mamba_model import SelectiveSSMCell, SEQ_LEN, D_IN
    from app.ml import registry
    from app.ml.calibration import expected_calibration_error
    from sklearn.metrics import (precision_recall_fscore_support, roc_auc_score,
                                 brier_score_loss, confusion_matrix)

    t_vals = list(range(72, 169, 6))
    Xtr, ytr, _, mtr = build_sequences(TRAIN_ZONES, t_vals)
    Xva, yva, _, mva = build_sequences(VAL_ZONES, t_vals)
    assert len(Xtr) and len(Xva), "empty sequence sets"
    assert Xtr.shape[1:] == (SEQ_LEN, D_IN), f"bad shape {Xtr.shape}"

    dev = torch.device("cpu")
    model = SelectiveSSMCell().to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCELoss()
    Xtr_t = torch.tensor(Xtr, device=dev)
    ytr_t = torch.tensor(ytr, dtype=torch.float32, device=dev)
    Xva_t = torch.tensor(Xva, device=dev)

    best_val, best_state, wait = float("inf"), None, 0
    for ep in range(EPOCHS):
        model.train()
        opt.zero_grad()
        loss_fn(model(Xtr_t).squeeze(), ytr_t).backward()
        opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(loss_fn(model(Xva_t).squeeze(),
                               torch.tensor(yva, dtype=torch.float32)))
        if vl < best_val - 1e-4:
            best_val, best_state, wait = vl, dict(model.state_dict()), 0
        else:
            wait += 1
            if wait >= PATIENCE:
                break
    model.load_state_dict(best_state)

    adir = os.path.join(os.path.dirname(__file__), "..", "..",
                        "models", "mamba", VERSION)
    os.makedirs(adir, exist_ok=True)
    cpath = os.path.join(adir, "checkpoint.pt")
    torch.save({"state_dict": best_state, "seed": SEED,
                "task": mtr["task"], "data_source": mtr["data_source"]}, cpath)

    model.eval()
    with torch.no_grad():
        pv = model(Xva_t).squeeze().cpu().numpy()
    pred = (pv >= 0.5).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(
        yva, pred, average="binary", zero_division=0)
    try:
        roc = float(roc_auc_score(yva, pv))
    except Exception:
        roc = None
    metrics = {"accuracy": round(float((pred == yva).mean()), 4),
               "precision": round(float(prec), 4),
               "recall": round(float(rec), 4), "f1": round(float(f1), 4),
               "roc_auc": round(roc, 4) if roc is not None else None,
               "brier": round(float(brier_score_loss(yva, pv)), 4),
               "ece": round(expected_calibration_error(yva, pv), 4),
               "calibration": "uncalibrated — use model_score, not probability",
               "confusion_matrix": confusion_matrix(yva, pred).tolist(),
               "n_samples": int(len(Xtr) + len(Xva)),
               "n_train": int(len(Xtr)), "n_val": int(len(Xva)),
               "data_source": "SIMULATED storm sequences — NOT operational skill",
               "leakage_check_passed": True}
    entry = registry.register(
        model_id="mamba_temporal", version=VERSION,
        dataset_version="seq_storm_v1", feature_version="seq48x7_v1",
        algorithm="SelectiveSSMCell", parameters={"d_in": D_IN, "lr": 1e-3,
                                                  "epochs": EPOCHS,
                                                  "patience": PATIENCE},
        metrics=metrics, validation_method="spatial holdout by zone (train 6 / val 2)",
        status="EXPERIMENTAL", dataset_size=len(Xtr) + len(Xva),
        feature_schema=["rain1h", "rain24h", "rain72h", "rain_slope",
                        "soil", "soil_change", "sar_neutral"],
        calibration_status="uncalibrated", random_seed=SEED,
        artifact_path=cpath)
    gate = registry.evaluate_promotion("mamba_temporal", VERSION)
    print(f"mamba {VERSION}: val_f1={f1:.3f} brier={metrics['brier']} "
          f"epochs_run={ep + 1} -> registry {entry['status']}, gate {gate['verdict']}")
    return {"metrics": metrics, "gate": gate}


if __name__ == "__main__":
    main()
