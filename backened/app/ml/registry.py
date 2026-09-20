"""Lightweight model registry (Phase 2C/6) — JSON file, no new dependency.

Only status=PROMOTED models may enter the production inference path.
Promotion requires evaluate_promotion() to pass a configurable evidence
gate (samples, F1, recall, Brier, leakage + validation flags) — thresholds
are documented parameters, not universal constants.
"""
import hashlib
import json
import os
from datetime import UTC, datetime

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                             "models", "registry.json")

STATUSES = ("EXPERIMENTAL", "TRAINING", "DEMO", "VALIDATED", "PROMOTED",
            "PRODUCTION", "REJECTED", "RETIRED")

# Promotion evidence gate — configurable, documented, deliberately modest.
PROMOTION_GATE = {
    "minimum_samples": 50,
    "minimum_f1": 0.60,
    "minimum_recall": 0.60,
    "maximum_brier": 0.25,
    "leakage_check_required": True,
    "validation_required": "spatial GroupKFold",
}


def _load() -> dict:
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"models": []}


def _save(reg: dict) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)


def artifact_hash(path: str | None) -> str | None:
    """SHA256 of a model artifact (reproducibility evidence)."""
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()[:16]


def register(*, model_id: str, version: str, dataset_version: str,
             feature_version: str, algorithm: str, parameters: dict,
             metrics: dict, validation_method: str, status: str,
             dataset_size: int | None = None,
             feature_schema: list[str] | None = None,
             calibration_status: str = "uncalibrated",
             random_seed: int | None = None,
             artifact_path: str | None = None) -> dict:
    assert status in STATUSES, f"bad status {status}"
    reg = _load()
    entry = {"model_id": model_id, "version": version,
             "training_dataset": dataset_version,
             "dataset_version": dataset_version,  # back-compat alias
             "dataset_size": dataset_size if dataset_size is not None
             else metrics.get("n_samples"),
             "feature_schema": feature_schema,
             "feature_version": feature_version,
             "training_timestamp": datetime.now(UTC).isoformat(),
             "validation_strategy": validation_method,
             "validation_method": validation_method,  # back-compat alias
             "algorithm": algorithm, "parameters": parameters,
             "metrics": metrics,
             "calibration_status": calibration_status,
             "model_status": status,
             "random_seed": random_seed,
             "artifact_hash": artifact_hash(artifact_path),
             "promotion_status": "NOT_EVALUATED",
             "status": status}  # back-compat alias
    reg["models"] = [m for m in reg["models"]
                     if not (m["model_id"] == model_id and m["version"] == version)]
    reg["models"].append(entry)
    _save(reg)
    return entry


def evaluate_promotion(model_id: str, version: str,
                       gate: dict | None = None) -> dict:
    """Evaluate a registry entry against the promotion gate. Records verdict.

    Never auto-promotes: PASS sets promotion_status=APPROVED_FOR_PROMOTION
    (human still flips status to PROMOTED); anything else records the
    blocking reasons.
    """
    gate = gate or PROMOTION_GATE
    reg = _load()
    entry = next((m for m in reg["models"]
                  if m["model_id"] == model_id and m["version"] == version), None)
    if entry is None:
        return {"verdict": "NOT_FOUND"}
    m = entry.get("metrics", {})
    reasons = []
    n = entry.get("dataset_size") or m.get("n_samples") or 0
    if n < gate["minimum_samples"]:
        reasons.append(f"n={n} < minimum_samples={gate['minimum_samples']}")
    if (m.get("f1") or 0) < gate["minimum_f1"]:
        reasons.append(f"F1={m.get('f1')} < {gate['minimum_f1']}")
    if (m.get("recall") or 0) < gate["minimum_recall"]:
        reasons.append(f"recall={m.get('recall')} < {gate['minimum_recall']}")
    if m.get("brier") is not None and m["brier"] > gate["maximum_brier"]:
        reasons.append(f"Brier={m['brier']} > {gate['maximum_brier']}")
    if gate["leakage_check_required"] and not m.get("leakage_check_passed", True):
        reasons.append("leakage check not passed")
    if gate["validation_required"] not in str(entry.get("validation_strategy", "")):
        reasons.append(f"validation '{entry.get('validation_strategy')}' "
                       f"!= required '{gate['validation_required']}'")
    entry["promotion_status"] = ("APPROVED_FOR_PROMOTION" if not reasons
                                 else "BLOCKED: " + "; ".join(reasons))
    _save(reg)
    return {"verdict": "PASS" if not reasons else "BLOCK",
            "reasons": reasons, "gate": gate}


def retire(model_id: str, version: str, reason: str = "") -> dict | None:
    reg = _load()
    for m in reg["models"]:
        if m["model_id"] == model_id and m["version"] == version:
            m["status"] = m["model_status"] = "RETIRED"
            m["promotion_status"] = f"RETIRED: {reason}"
    _save(reg)
    return next((m for m in reg["models"]
                 if m["model_id"] == model_id and m["version"] == version), None)


def production_model() -> dict | None:
    """The single model allowed in the production inference path."""
    for m in _load().get("models", []):
        if m.get("status") in ("PROMOTED", "PRODUCTION"):
            return m
    return None


def all_models() -> list[dict]:
    return _load().get("models", [])
