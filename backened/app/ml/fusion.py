"""FusionEngine.

risk = STATIC_WEIGHT * static + DYNAMIC_WEIGHT * dynamic   (hazard)
Exposure kept separate from hazard. Extreme-event rule may escalate advisory.
All thresholds from risk_thresholds.yaml — calibration parameters.
"""
from ..config import THRESHOLDS, STATIC_WEIGHT, DYNAMIC_WEIGHT

FUSION_VERSION = "fusion_v1"

def classify(score: float) -> str:
    b = THRESHOLDS["classes"]["boundaries"]
    if score < b[0]: return "LOW"
    if score < b[1]: return "MODERATE"
    if score < b[2]: return "HIGH"
    return "VERY_HIGH"

def escalation_rule(static_score, r24, r72, soil_moisture):
    """Returns (fired: bool, reasons: list[str], boost: float)."""
    cfg = THRESHOLDS
    reasons, min_s = [], cfg["escalation"]["min_static_susceptibility"]
    if static_score < min_s:
        return False, [], 0.0
    if r24 > cfg["rainfall"]["r24_escalation_mm"]:
        reasons.append(f"24h rainfall {r24:.0f}mm > {cfg['rainfall']['r24_escalation_mm']}mm threshold")
    if r72 > cfg["rainfall"]["r72_escalation_mm"]:
        reasons.append(f"72h rainfall {r72:.0f}mm > {cfg['rainfall']['r72_escalation_mm']}mm threshold")
    if soil_moisture > cfg["soil_moisture"]["saturation_fraction"]:
        reasons.append(f"soil saturation {soil_moisture*100:.0f}% > {cfg['soil_moisture']['saturation_fraction']*100:.0f}%")
    return bool(reasons), reasons, cfg["escalation"]["boost"] if reasons else 0.0

def fuse(static_score: float, dynamic_score: float, r24: float, r72: float,
         soil_moisture: float):
    static_w, dynamic_w = STATIC_WEIGHT, DYNAMIC_WEIGHT
    risk = static_w * static_score + dynamic_w * dynamic_score
    fired, reasons, boost = escalation_rule(static_score, r24, r72, soil_moisture)
    risk = min(1.0, risk + boost)
    return {"risk_score": round(risk, 4), "severity": classify(risk),
            "escalated": fired, "escalation_reasons": reasons,
            "weights": {"static": static_w, "dynamic": dynamic_w},
            "fusion_version": FUSION_VERSION}
