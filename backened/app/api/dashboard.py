"""Dashboard endpoints — road connectivity, weather forecast overview, emergency tasks."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import RoadSegment, EmergencyTask, Zone

router = APIRouter(tags=["dashboard"])


@router.get("/roads")
def get_road_segments(db: Session = Depends(get_db)):
    segments = db.query(RoadSegment).all()
    roads = []
    for r in segments:
        roads.append({
            "id": r.id,
            "name": r.name,
            "from_zone": r.from_zone,
            "to_zone": r.to_zone,
            "road_type": r.road_type,
            "length_km": r.length_km,
            "status": r.status,
            "blockage_reason": r.blockage_reason,
            "last_updated": r.last_updated.isoformat() if r.last_updated else None,
            "reported_by": r.reported_by,
            "latitude": r.latitude,
            "longitude": r.longitude,
        })
    blocked = sum(1 for r in roads if r["status"] != "OPEN")
    return {
        "roads": roads,
        "total": len(roads),
        "blocked": blocked,
        "open": len(roads) - blocked,
        "summary": f"{blocked} of {len(roads)} segments disrupted",
    }


@router.get("/weather/overview")
def get_weather_overview(t: int = Query(24, ge=24, le=168), db: Session = Depends(get_db)):
    """Region-wide weather risk overview — runs the full pipeline at time t."""
    from app.services import sim
    results = sim.run_pipeline(t)
    forecasts = []
    for r in results:
        rainfall_24h = r.get("rainfall_24h", 0)
        rainfall_72h = r.get("rainfall_72h", 0)
        soil = r.get("soil_moisture", 0)

        if rainfall_24h > 50:
            risk_level = "EXTREME"
            risk_color = "#ba1a1a"
            message = "Heavy rainfall warning — flash flood risk"
        elif rainfall_24h > 25:
            risk_level = "HIGH"
            risk_color = "#ea580c"
            message = "Moderate to heavy rainfall expected"
        elif rainfall_24h > 10:
            risk_level = "MODERATE"
            risk_color = "#d97706"
            message = "Light to moderate rainfall"
        else:
            risk_level = "LOW"
            risk_color = "#245c45"
            message = "No significant rainfall expected"

        forecasts.append({
            "zone_id": r["zone_id"],
            "name": r["name"],
            "district": r["district"],
            "rainfall_24h": round(rainfall_24h, 1),
            "rainfall_72h": round(rainfall_72h, 1),
            "soil_moisture": round(soil, 3),
            "risk_score": round(r["risk_score"], 3),
            "severity": r["severity"],
            "risk_level": risk_level,
            "risk_color": risk_color,
            "message": message,
            "escalated": r["escalated"],
        })

    total_extreme = sum(1 for f in forecasts if f["risk_level"] == "EXTREME")
    total_high = sum(1 for f in forecasts if f["risk_level"] == "HIGH")
    return {
        "forecasts": sorted(forecasts, key=lambda x: x["risk_score"], reverse=True),
        "total": len(forecasts),
        "extreme_count": total_extreme,
        "high_count": total_high,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/emergency/tasks")
def get_emergency_tasks(db: Session = Depends(get_db)):
    tasks = db.query(EmergencyTask).order_by(
        EmergencyTask.created_at.desc()
    ).all()
    result = []
    for t in tasks:
        result.append({
            "id": t.id,
            "zone_id": t.zone_id,
            "task_type": t.task_type,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "status": t.status,
            "assigned_team": t.assigned_team,
            "estimated_time": t.estimated_time,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })

    critical = sum(1 for t in result if t["priority"] == "CRITICAL" and t["status"] != "COMPLETED")
    in_progress = sum(1 for t in result if t["status"] == "IN_PROGRESS")
    return {
        "tasks": result,
        "total": len(result),
        "critical_pending": critical,
        "in_progress": in_progress,
        "completed": sum(1 for t in result if t["status"] == "COMPLETED"),
    }


@router.get("/risk/severity-summary")
def get_severity_summary(t: int = Query(96, ge=24, le=168), db: Session = Depends(get_db)):
    """Aggregated risk severity counts for the dashboard overview."""
    from app.services import sim
    results = sim.run_pipeline(t)
    severity_counts = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "VERY_HIGH": 0}
    zones = db.query(Zone).all()
    zone_map = {z.id: z for z in zones}
    zone_risks = []
    for r in results:
        severity_counts[r["severity"]] = severity_counts.get(r["severity"], 0) + 1
        z = zone_map.get(r["zone_id"])
        zone_risks.append({
            "zone_id": r["zone_id"],
            "name": r["name"],
            "district": r["district"],
            "risk_score": round(r["risk_score"], 3),
            "severity": r["severity"],
            "escalated": r["escalated"],
            "population": z.population if z else 0,
            "slope": z.slope if z else 0,
            "elevation": z.elevation if z else 0,
            "road_proximity": z.road_proximity if z else 0,
            "rainfall_24h": r.get("rainfall_24h", 0),
            "soil_moisture": r.get("soil_moisture", 0),
        })

    total_pop = sum(z["population"] for z in zone_risks)
    exposed_pop = sum(
        z["population"] for z in zone_risks
        if z["severity"] in ("HIGH", "VERY_HIGH")
    )
    return {
        "summary": severity_counts,
        "zones": sorted(zone_risks, key=lambda x: x["risk_score"], reverse=True),
        "total_zones": len(results),
        "total_population": total_pop,
        "exposed_population": exposed_pop,
        "escalated_count": sum(1 for z in zone_risks if z["escalated"]),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
