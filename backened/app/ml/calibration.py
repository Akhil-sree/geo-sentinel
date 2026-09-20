"""Calibration metrics (Phase 7) — stdlib + numpy + sklearn only.

ECE, reliability bins, and calibration-curve points from measured
out-of-fold probabilities. No invented curves: bins with zero samples are
reported as empty, never interpolated.
"""
import numpy as np


def expected_calibration_error(y_true, y_proba, n_bins: int = 5) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_proba = np.asarray(y_proba, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (y_proba > lo) & (y_proba <= hi if hi < 1.0 else y_proba <= hi + 1e-9)
        if m.sum() == 0:
            continue
        ece += (m.sum() / len(y_proba)) * abs(y_true[m].mean() - y_proba[m].mean())
    return float(ece)


def reliability_bins(y_true, y_proba, n_bins: int = 5) -> list[dict]:
    """Per-bin accuracy vs confidence for reliability diagrams (measured)."""
    y_true = np.asarray(y_true, dtype=float)
    y_proba = np.asarray(y_proba, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (y_proba > lo) & (y_proba <= hi + 1e-9)
        out.append({"bin": [round(float(lo), 2), round(float(hi), 2)],
                    "n": int(m.sum()),
                    "accuracy": round(float(y_true[m].mean()), 4) if m.sum() else None,
                    "confidence": round(float(y_proba[m].mean()), 4) if m.sum() else None})
    return out
