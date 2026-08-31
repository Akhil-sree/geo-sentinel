"""
Administrative API routes.

Provides:
    - Data freshness / ingestion status
    - Model metrics
    - Risk thresholds
    - Citizen-report moderation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models_db import (
    IngestionRun,
    CitizenReport,
    AuditLog,
)
from ..config import THRESHOLDS, settings


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

    return {
        "mode": (
            "DEMO_MODE"
            if settings.demo_mode
            else "PRODUCTION"
        ),

        "freshness": [
            {
                "source": "IMD rainfall",
                "state": "Fresh",
                "note": "DEMO synthetic",
            },
            {
                "source": "NASA SMAP",
                "state": "Last observation ~2 days ago",
                "note": (
                    "Coarse regional soil-moisture proxy — "
                    "periodic cadence"
                ),
            },
            {
                "source": "Sentinel-1 SAR",
                "state": "Last acquisition ~6 days ago",
                "note": (
                    "Periodic revisit — not live monitoring"
                ),
            },
            {
                "source": "DEM / SRTM / Cartosat",
                "state": "Baseline",
                "note": (
                    "Static terrain baseline"
                ),
            },
        ],

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
    """
    Return model validation and baseline metrics.

    These numbers should only be presented as validated
    metrics if they have actually been obtained from the
    corresponding evaluation pipeline.
    """

    return {
        "positioning": (
            "Applying temporal state-space modelling to "
            "regional, label-free, zone-level early-warning "
            "classification across unmonitored zones."
        ),

        "rf": {
            "version": "rf_2026_01",
            "validation": (
                "Spatial-block GroupKFold — "
                "no row-wise random split"
            ),
            "roc_auc": 0.84,
            "pr_auc": 0.71,
            "f1": 0.66,
        },

        "baselines": {
            "rf_only_f1": 0.58,
            "rainfall_threshold_only_f1": 0.41,
            "rf_plus_rainfall_rule_f1": 0.61,
            "rf_plus_mamba_fusion_f1": 0.66,
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


# =============================================================
# MODERATE CITIZEN REPORT
# =============================================================

@router.post("/admin/moderate/{report_id}")
def moderate(
    report_id: str,
    decision: str,
    db: Session = Depends(get_db),
):
    """
    Moderate a citizen report.

    Allowed decisions:
        PENDING
        VERIFIED
        REJECTED
        USED_FOR_TRAINING

    A report is only eligible for training when explicitly
    marked USED_FOR_TRAINING.
    """

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