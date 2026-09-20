"""Vision observation service — compare visual evidence with existing risk."""
from sqlalchemy.orm import Session
from app.models_db import Zone, RiskScore


def corroborate(db: Session, zone_id: str, observation_severity: str, confidence: float) -> dict:
    """Compare visual observation with existing zone risk.

    Returns corroboration status:
    - CORROBORATED: both risk and observation agree
    - VISUAL_ANOMALY: observation shows danger but risk model doesn't
    - INCONCLUSIVE: risk is high but no visual evidence (absence ≠ safety)
    """
    zone = db.get(Zone, zone_id)
    if not zone:
        return {
            "zone_id": zone_id,
            "corroboration": "NO_ZONE_DATA",
            "explanation": f"Zone {zone_id} not found",
        }

    latest = (
        db.query(RiskScore)
        .filter(RiskScore.zone_id == zone_id)
        .order_by(RiskScore.timestamp.desc())
        .first()
    )

    zone_risk = latest.risk_score if latest else 0.0
    zone_severity = latest.severity if latest else "LOW"

    obs_score = _severity_to_score(observation_severity)

    # Corroboration logic
    if obs_score >= 0.6 and zone_risk >= 0.5:
        status = "CORROBORATED"
        explanation = (
            f"Zone risk is {zone_severity} ({zone_risk:.0%}) and visual observation "
            f"is {observation_severity} — field evidence corroborates model assessment."
        )
    elif obs_score >= 0.6 and zone_risk < 0.4:
        status = "VISUAL_ANOMALY"
        explanation = (
            f"Visual observation shows {observation_severity} evidence but zone risk "
            f"is only {zone_severity} ({zone_risk:.0%}). Requires field verification — "
            f"possible early-stage failure not yet captured by environmental sensors."
        )
    elif zone_risk >= 0.5 and obs_score < 0.3:
        status = "INCONCLUSIVE"
        explanation = (
            f"Zone risk remains {zone_severity} ({zone_risk:.0%}) based on terrain, rainfall, "
            f"and SAR data. Visual evidence is inconclusive — absence of visible landslide "
            f"does not reduce the assessed hazard."
        )
    else:
        status = "LOW_CONCERN"
        explanation = (
            f"Both risk model ({zone_severity}, {zone_risk:.0%}) and visual observation "
            f"({observation_severity}) indicate limited concern."
        )

    return {
        "zone_id": zone_id,
        "zone_risk_score": round(zone_risk, 4),
        "zone_severity": zone_severity,
        "observation_score": round(obs_score, 4),
        "observation_severity": observation_severity,
        "corroboration": status,
        "explanation": explanation,
    }


def _severity_to_score(severity: str) -> float:
    return {"HIGH": 0.85, "MODERATE": 0.5, "LOW": 0.2, "NONE": 0.0}.get(severity, 0.0)
