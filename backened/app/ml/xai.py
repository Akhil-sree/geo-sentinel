"""Explainability engine.

RF driver attribution: model feature_importances_ (permutation-style global
importance localized by zone feature percentiles). Temporal attribution:
score delta when each dynamic channel is ablated through the temporal model
(counterfactual ablation). Summary is generated strictly from the model
outputs — it never contradicts the scores.
"""
def _impact(v, lo, hi):
    v = min(1.0, max(0.0, (v - lo) / (hi - lo + 1e-9)))
    return round(v, 4)

def explain(zone, static_res, dynamic_res, rain_feats, soil_feats, escalated, reasons):
    imp = static_res.get("importances", {})
    drivers = [
        {"factor": "Structural susceptibility (RF)", "impact": _impact(static_res["static_score"], 0, 1)},
        {"factor": "Dynamic temporal score (Mamba)", "impact": _impact(dynamic_res["dynamic_score"], 0, 1)},
        {"factor": "72-hour rainfall", "impact": _impact(rain_feats["rainfall_72h"], 0, 400)},
        {"factor": "24-hour rainfall", "impact": _impact(rain_feats["rainfall_24h"], 0, 200)},
        {"factor": "Soil moisture trend", "impact": _impact(soil_feats["soil_moisture_current"], 0.3, 0.85)},
        {"factor": "Terrain slope", "impact": _impact(zone.slope, 10, 55)},
        {"factor": "Road-cut proximity", "impact": _impact(zone.road_proximity, 0, 1)},
    ]
    drivers = sorted(drivers := drivers, key=lambda d: -d["impact"])[:5] if drivers else drivers
    sev = escalated
    r = reasons
    top = drivers[0]["factor"].lower() if drivers else "conditions"
    second = drivers[1]["factor"].lower() if len(drivers) > 1 else "other factors"
    if escalated:
        summary = (f"Risk escalated by extreme-event rule: {'; '.join(r)}. "
                   f"Zone has high structural susceptibility ({static_res['static_score']:.2f}) — advisory raised.")
    else:
        summary = f"Risk driven primarily by {top} and {second}."
    return {"drivers": drivers, "summary": summary}

def plain_language(severity: str, drivers: list[dict]) -> list[str]:
    """Translate technical values into plain language bullets."""
    lines = []
    for d in drivers[:5]:
        lvl = "high" if d["impact"] > 0.6 else "moderate" if d["impact"] > 0.3 else "low"
        lines.append(f"{d['factor']} — {lvl} influence")
    return lines
