"""
Administrative API routes.

Provides:
    - Data freshness / ingestion status
    - Model metrics
    - Risk thresholds
    - Citizen-report moderation
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import _client_ip, rate_limit, require_role
from ..config import THRESHOLDS, settings
from ..database import get_db
from ..models_db import (
    AuditLog,
    CitizenReport,
    IngestionRun,
)

router = APIRouter()


# =============================================================
# DATA STATUS
# =============================================================

@router.get("/admin/data")
def data_status(
    db: Session = Depends(get_db),
):
    """
    Show data-source freshness.

    Stale sources are explicitly marked and are never
    presented as live observations.
    """

    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.ran_at.desc())
        .limit(10)
        .all()
    )

    # Single honesty source: live provider_states, not hardcoded strings
    # (which previously claimed Fresh/2d/6d regardless of provider mode).
    from app.ingest.runner import provider_states
    live = [{"source": p.get("source"), "state": p.get("freshness"),
             "note": p.get("quality"), "is_live": p.get("is_live"),
             "is_simulated": p.get("is_simulated")}
            for p in provider_states(db)]

    return {
        "mode": (
            "DEMO_MODE"
            if settings.demo_mode
            else "PRODUCTION"
        ),

        "freshness": live,

        "recent_ingestion_runs": [
            {
                "source": run.source,
                "status": run.status,
                "detail": run.detail,
                "at": (
                    run.ran_at.isoformat()
                    if run.ran_at
                    else None
                ),
            }
            for run in runs
        ],
    }


# =============================================================
# MODEL METRICS
# =============================================================

@router.get("/admin/model/metrics")
def model_metrics():
    """Serve ONLY measured metrics: model registry + stored RF metadata.

    No hardcoded numbers — unmeasured claims were removed (they previously
    returned fabricated roc_auc/pr_auc/f1). Anything without a registry
    entry is reported as UNMEASURED.
    """
    from app.ml import registry as _reg
    from app.ml.rf_model import load_metrics as _rf_meta

    rf_meta = _rf_meta()
    return {
        "positioning": (
            "Zone-level early-warning classification across unmonitored "
            "zones. Temporal Mamba is research-only until a trained "
            "checkpoint passes the promotion gate."
        ),
        "production_static": {
            "version": "rf_2026_01",
            "status": "Active (n=8 zone labels)",
            "cv_accuracy": rf_meta.get("cv_accuracy"),
            "cv_f1_macro": rf_meta.get("cv_f1_macro"),
            "calibration": rf_meta.get("calibration", "uncalibrated"),
        },
        "registry": _reg.all_models() or "UNMEASURED — run app.ml.train_rf.main_event()",
        "fusion": {
            "version": "fusion_v1",
            "weights": {"static": 0.4, "dynamic": 0.6},
            "validation": ("NOT ML-validated on held-out data — rule-based combination; "
                           "end-to-end escalation behaviour covered by integration tests. "
                           "Outcome-validated comparison requires a larger event dataset."),
        },
        "early_warning_focus": (
            "FN-weighted evaluation — false negatives "
            "and lead time matter more than raw accuracy."
        ),
        "thresholds_note": (
            "Class boundaries and escalation rules are "
            "calibration parameters from risk_thresholds.yaml, "
            "not validated universal constants."
        ),
    }


# =============================================================
# RISK THRESHOLDS
# =============================================================

@router.get("/admin/thresholds")
def thresholds():
    """
    Return configured risk thresholds.
    """

    return THRESHOLDS


@router.get("/models")
def model_versions():
    """Model versioning + promotion gates: every version, its dataset,
    validation, and whether it may serve production (none promoted while
    gates BLOCK: n≥50, F1≥0.60, spatial+temporal validation, no leakage,
    calibrated). Served versions are rf_2026_01 + heuristic + fusion_v1."""
    from app.ml import registry as _reg
    try:
        prod = _reg.production_model()
    except Exception:
        prod = None
    return {"served": {"static": "rf_2026_01", "temporal": "mamba_2026_01_mock (heuristic)",
                       "fusion": "fusion_v1",
                       "calibration": "UNCALIBRATED RISK SCORE — not a probability"},
            "promotion_gate": {"min_dataset_size": 50, "min_f1": 0.60,
                               "requires": ["spatial-CV", "holdout", "leakage-check",
                                            "calibration", "reproducibility"]},
            "production_model": prod,
            "registry": _reg.all_models() or "UNMEASURED"}


# =============================================================
# MODERATE CITIZEN REPORT
# =============================================================

@router.post("/admin/moderate/{report_id}")
def moderate(
    report_id: str,
    decision: str,
    db: Session = Depends(get_db),
    request: Request = None,
    x_api_key: str | None = Header(default=None),
    role: str = Depends(require_role("operator", "admin")),
):
    rate_limit(_client_ip(request),
               limit=30)
    """
    Moderate a citizen report. Guarded by API key when configured.

    Allowed decisions:
        PENDING
        VERIFIED
        REJECTED
        USED_FOR_TRAINING

    A report is only eligible for training when explicitly
    marked USED_FOR_TRAINING. Promotion to the training set happens
    only via the dataset-builder job after re-validation — never
    automatically (see docs: feedback-loop).
    """
    from app.auth import guard as _guard
    _guard(x_api_key)

    allowed = {
        "PENDING",
        "VERIFIED",
        "REJECTED",
        "USED_FOR_TRAINING",
    }

    decision = decision.upper()

    if decision not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid decision. Allowed values: "
                + ", ".join(sorted(allowed))
            ),
        )

    report = db.get(
        CitizenReport,
        report_id,
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen report not found",
        )

    report.status = decision

    db.add(
        AuditLog(
            action="REPORT_MODERATED",
            detail=(
                f"{report_id} -> {decision}"
            ),
        )
    )

    db.commit()

    return {
        "id": report_id,
        "status": report.status,
        "training_eligible": (
            decision == "USED_FOR_TRAINING"
        ),
    }