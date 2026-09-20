"""Mamba CV worker — runs in a FRESH process (torch imported FIRST).

Rationale: importing sklearn before torch in one process breaks torch's DLL
load on this host (OpenMP conflict — see app/ml/mamba_model.py). The parent
pipeline (tabular sklearn stage) therefore delegates here via subprocess.

Usage: gs_mamba_worker.py <in_npz> <out_dir> <epochs> <patience> <seed>
Writes: oof.npy, fold_metrics.json, checkpoints fold{k}.pt + scaler_fold{k}.joblib
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "ml"))

import numpy as np  # noqa: E402

import torch  # noqa: E402 — FIRST heavy import in this process, before sklearn
import torch.nn as nn  # noqa: E402


def build_ssm(d_in, d_state=8, dropout=0.2):
    from mamba_model import SelectiveSSMCell

    class SmallSSM(nn.Module):
        def __init__(self):
            super().__init__()
            self.proj = nn.Linear(d_in, 16)
            self.norm = nn.LayerNorm(16)
            self.drop = nn.Dropout(dropout)
            self.cell = SelectiveSSMCell(d_in=16, d_state=d_state)

        def forward(self, x):
            return self.cell(self.drop(self.norm(self.proj(x))))

    return SmallSSM()


def main():
    import random  # noqa
    in_npz, out_dir, epochs, patience, seed = sys.argv[1:6]
    epochs, patience, seed = int(epochs), int(patience), int(seed)
    os.makedirs(os.path.join(out_dir, "checkpoints"), exist_ok=True)

    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import GroupKFold
    import joblib

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    z = np.load(in_npz, allow_pickle=False)
    X, y, groups = z["X"], z["y"].astype(int), np.array([str(g) for g in z["groups"]])
    ckpt = os.path.join(out_dir, "checkpoints")
    cv = GroupKFold(n_splits=3)
    oof = np.zeros(len(y))
    folds = []
    for fold, (tri, tei) in enumerate(cv.split(X, y, groups)):
        sc = StandardScaler().fit(X[tri].reshape(-1, X.shape[2]))
        Xt = sc.transform(X[tri].reshape(-1, X.shape[2])).reshape(len(tri), -1, X.shape[2])
        Xv = sc.transform(X[tei].reshape(-1, X.shape[2])).reshape(len(tei), -1, X.shape[2])
        pw = float((y[tri] == 0).sum() / max(1, (y[tri] == 1).sum()))
        model = build_ssm(X.shape[2])
        opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
        tX = torch.tensor(Xt, dtype=torch.float32)
        ty = torch.tensor(y[tri], dtype=torch.float32)
        vX = torch.tensor(Xv, dtype=torch.float32)
        vy = torch.tensor(y[tei], dtype=torch.float32)
        w = torch.tensor(np.where(y[tri] == 1, pw, 1.0), dtype=torch.float32)
        wv = torch.tensor(np.where(y[tei] == 1, pw, 1.0), dtype=torch.float32)
        best, best_state, wait = 1e9, None, 0
        for _ in range(epochs):
            model.train()
            opt.zero_grad()
            loss = (nn.BCELoss(reduction="none")(model(tX), ty) * w).mean()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            model.eval()
            with torch.no_grad():
                vl = float((nn.BCELoss(reduction="none")(model(vX), vy) * wv).mean())
            if vl < best - 1e-4:
                best = vl
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                wait = 0
            else:
                wait += 1
                if wait >= patience:
                    break
        model.load_state_dict(best_state)
        torch.save(best_state, os.path.join(ckpt, f"fold{fold}.pt"))
        joblib.dump(sc, os.path.join(ckpt, f"scaler_fold{fold}.joblib"))
        model.eval()
        with torch.no_grad():
            oof[tei] = model(vX).numpy()
        folds.append({"fold": fold, "val_loss": round(best, 5),
                      "events": sorted(set(groups[tei].tolist()))})
    np.save(os.path.join(out_dir, "oof.npy"), oof)
    json.dump(folds, open(os.path.join(out_dir, "folds.json"), "w"))
    print(f"worker done: {len(y)} seqs, folds={len(folds)}")


if __name__ == "__main__":
    main()
