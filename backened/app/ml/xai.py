"""Explainability engine — method-labeled driver analysis. Never claims SHAP.

Method ladder (first available wins, always reported in `method`):
  PERMUTATION_IMPORTANCE — measured drop in F1 on events_v2 (n=24) when a
    terrain feature is shuffled (sklearn, seed 42); weather rows use local
    deviation. Strongest honest method available.
  IMPORTANCE_WEIGHTED — RF impurity importances x local deviation.
  HEURISTIC DRIVER ANALYSIS — local deviation only.
Direction arrows: ↑ raises risk, ↓ lowers risk.
"""
import os

_PERM_CACHE: dict = {}


def permutation_bundle():
    """Measured permutation importance of the event RF on events_v2.

    Returns {importances, f1_baseline, source} or None (artifact/DB missing).
    Cached per process; deterministic (random_state=42).
    """
    if _PERM_CACHE.get("done"):
        return _PERM_CACHE.get("bundle")
    _PERM_CACHE["done"] = True
    try:
        import joblib
        from sklearn.inspection import permutation_importance

        from app.database import SessionLocal
        from app.ml.dataset import FEATURES, build_event_dataset
        from app.ml.rf_model import MODEL_DIR
        from app.models_db import Zone
        apath = os.path.join(MODEL_DIR, "event_rf_event", "model.joblib")
        if not os.path.exists(apath):
            return None
        db = SessionLocal()
        try:
            X, y, _, _ = build_event_dataset(db.query(Zone).all())
        finally:
            db.close()
        clf = joblib.load(apath)
        r = permutation_importance(clf, X, y, n_repeats=10,
                                   random_state=42, scoring="f1", n_jobs=-1)
        bundle = {"importances": {f: round(float(v), 4)
                                  for f, v in zip(FEATURES, r.importances_mean, strict=False)},
                  "f1_baseline": round(float(
                      (clf.predict(X) == y).mean()), 4),
                  "source": ("permutation on events_v2 train (in-sample, "
                               "n=24), F1 scoring — near-zero means terrain "
                               "features carry little signal even in-sample")}
        _PERM_CACHE["bundle"] = bundle
        return bundle
    except Exception:
        return None


def _impact(v, lo, hi):
    v = min(1.0, max(0.0, (v - lo) / (hi - lo + 1e-9)))
    return round(v, 4)

def explain(zone, static_res, dynamic_res, rain_feats, soil_feats, escalated, reasons,
            perm_bundle=None):
    imp = static_res.get("importances", {}) or {}
    # Local deviation of this zone's raw signals (0..1) weighted by global RF importance
    local = {
        "slope": _impact(zone.slope, 10, 55),
        "road_proximity": _impact(zone.road_proximity, 0, 1),
        "rainfall_72h": _impact(rain_feats["rainfall_72h"], 0, 400),
        "rainfall_24h": _impact(rain_feats["rainfall_24h"], 0, 200),
        "soil_moisture": _impact(soil_feats["soil_moisture_current"], 0.3, 0.85),
    }
    # Map RF feature names → display factors
    perm = (perm_bundle or {}).get("importances", {}) if perm_bundle else {}
    drivers = [
        {"factor": "Structural susceptibility (RF)", "impact": _impact(static_res["static_score"], 0, 1), "direction": "↑" if static_res["static_score"] >= 0.5 else "↓"},
        {"factor": "Dynamic temporal score (heuristic baseline)", "impact": _impact(dynamic_res["dynamic_score"], 0, 1), "direction": "↑" if dynamic_res["dynamic_score"] >= 0.5 else "↓"},
        {"factor": "72-hour rainfall", "impact": local["rainfall_72h"], "direction": "↑" if local["rainfall_72h"] >= 0.4 else "↓"},
        {"factor": "24-hour rainfall", "impact": local["rainfall_24h"], "direction": "↑" if local["rainfall_24h"] >= 0.4 else "↓"},
        {"factor": "Soil moisture trend", "impact": local["soil_moisture"], "direction": "↑" if local["soil_moisture"] >= 0.5 else "↓"},
        {"factor": "Terrain slope", "impact": local["slope"], "direction": "↑" if local["slope"] >= 0.5 else "↓"},
        {"factor": "Road-cut proximity", "impact": local["road_proximity"], "direction": "↑" if local["road_proximity"] >= 0.5 else "↓"},
    ]
    if perm:
        # Weight terrain rows by MEASURED permutation importance; weather
        # rows stay local-deviation (labeled in method).
        pw = {"Terrain slope": perm.get("slope", 0),
              "Road-cut proximity": perm.get("road_proximity", 0)}
        for d in drivers:
            if d["factor"] in pw:
                d["impact"] = round(d["impact"] * (0.5 + pw[d["factor"]]), 4)
        method = ("PERMUTATION_IMPORTANCE (terrain, events_v2 F1) + "
                  "LOCAL DEVIATION (weather)")
    else:
        method = "IMPORTANCE_WEIGHTED" if imp else "HEURISTIC DRIVER ANALYSIS"
    drivers = sorted(drivers, key=lambda d: -d["impact"])[:5]
    r = reasons
    top = drivers[0]["factor"].lower() if drivers else "conditions"
    second = drivers[1]["factor"].lower() if len(drivers) > 1 else "other factors"
    if escalated:
        summary = (f"Risk escalated by extreme-event rule: {'; '.join(r)}. "
                   f"Zone has high structural susceptibility ({static_res['static_score']:.2f}) — advisory raised.")
    else:
        summary = f"Risk driven primarily by {top} and {second}."
    return {"drivers": drivers, "summary": summary, "method": method}

def plain_language(severity: str, drivers: list[dict]) -> list[str]:
    """Translate technical values into plain language bullets."""
    lines = []
    for d in drivers[:5]:
        lvl = "high" if d["impact"] > 0.6 else "moderate" if d["impact"] > 0.3 else "low"
        arrow = d.get("direction", "")
        lines.append(f"{d['factor']} {arrow} — {lvl} influence".strip())
    return lines
