"""Supervised sequence dataset for temporal models (Phase 5).

Source: SIMULATED storm curves (app/services/sim.py) — the task validates
the training machinery (shapes, splits, early stopping, checkpointing),
NOT operational skill. Every artifact is tagged data_source=SIMULATED.

Task: from the past-48h 7-dim environmental sequence ending at hour t,
predict whether next-24h rainfall exceeds 80mm (computed from the same
curve — a pipeline-validation target, not a real forecast).

Leakage rules enforced here:
- features use only hours <= t (never the future);
- train/val split BY ZONE (spatial), never by row;
- fixed seeds; no fitted normalization (fixed divisors in features.py).
"""
import numpy as np
import pandas as pd

SEQ_LEN = 48
THRESHOLD_MM = 80.0
VERSION = "seq_storm_v1"


def _hourly_series(zone_id: str, t_end: int, hours: int) -> pd.DataFrame:
    from app.services.sim import storm, BASE
    import datetime as dt
    rows = []
    for h in range(t_end - hours + 1, t_end + 1):
        rows.append({"timestamp": BASE + dt.timedelta(hours=h),
                     "rainfall_mm_per_hr": storm(h)})
    return pd.DataFrame(rows)


def build_sequences(zone_ids: list[str], t_values: list[int]):
    """Returns (X, y, groups, meta). X: (n, 48, 7), y: binary, groups: zone."""
    from app.ml.features import build_model_sequence
    from app.services.sim import storm
    X, y, groups = [], [], []
    for zid in zone_ids:
        for t in t_values:
            rain_df = _hourly_series(zid, t, 48)
            soil_df = pd.DataFrame(
                [{"timestamp": r["timestamp"],
                  "soil_moisture": min(0.92, 0.35 + storm(h) * 0.001)}
                 for h, r in zip(range(t - 47, t + 1), rain_df.to_dict("records"))])
            seq = build_model_sequence(rain_df, soil_df, 0.15, seq_len=SEQ_LEN)
            if len(seq) != SEQ_LEN:
                continue
            nxt = sum(storm(h) for h in range(t + 1, t + 25))
            X.append(seq)
            y.append(1 if nxt > THRESHOLD_MM else 0)
            groups.append(zid)
    return (np.asarray(X, dtype=np.float32), np.asarray(y, dtype=int),
            np.asarray(groups), {
                "dataset_version": VERSION,
                "data_source": "SIMULATED storm curves — pipeline validation only",
                "task": f"next-24h rainfall > {THRESHOLD_MM}mm from past-48h",
                "n_samples": len(X), "n_positive": int(np.asarray(y).sum()),
                "split": "by zone (spatial)",
            })
