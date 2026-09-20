"""IoT sensor ingestion (soil-moisture, rainfall, tilt, pore-pressure).

POST /api/sensors/soil-moisture — soil-specific convenience endpoint
POST /api/sensors/readings        — generic multi-type ingestion
GET  /api/sensors                 — registry + health (ONLINE/STALE/OFFLINE)
GET  /api/sensors/{id}/readings   — recent readings

Validation: range checks, timestamp parse, duplicate (sensor_id+timestamp)
detection, outlier flagging (never silently dropped — flagged OUTLIER and
excluded from zone aggregates). Writes also mirror into the zone-level
observation tables so the risk pipeline consumes them with source tags
(SENSOR_*) instead of mock data. Rate-limited; mutating POSTs require
operator+ when API keys are configured (open-demo otherwise).
"""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import _client_ip, rate_limit, require_role
from app.database import get_db
from app.models_db import RainfallObservation, Sensor, SensorReading, SoilMoistureObservation, Zone

router = APIRouter()

RANGES = {
    "soil_moisture": (0.0, 1.0),
    "rainfall": (0.0, 500.0),
    "tilt": (-90.0, 90.0),
    "pore_pressure": (0.0, 1000.0),
}
UNITS = {"soil_moisture": "saturation 0..1", "rainfall": "mm/hr",
         "tilt": "degrees", "pore_pressure": "kPa"}


class ReadingIn(BaseModel):
    sensor_id: str
    sensor_type: str = "soil_moisture"
    zone_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timestamp: str | None = None
    value: float
    unit: str | None = None
    depth_cm: float | None = None


def _parse_ts(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(UTC)
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if d > now + timedelta(hours=1) or d < now - timedelta(days=365):
            raise ValueError("timestamp out of range")
        return d
    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid timestamp") from e


def _nearest_zone(db: Session, lat, lng, fallback: str | None) -> str:
    if fallback and db.query(Zone).filter(Zone.id == fallback).first():
        return fallback
    if fallback:
        raise HTTPException(status_code=422, detail=f"Unknown zone_id '{fallback}'")
    if lat is None or lng is None:
        raise HTTPException(status_code=422, detail="zone_id or lat+lng required")
    zones = db.query(Zone).all()
    if not zones:
        raise HTTPException(status_code=422, detail="Empty zone registry")
    return min(zones, key=lambda z: (z.latitude - lat) ** 2 + (z.longitude - lng) ** 2).id


def _ingest_one(db: Session, r: ReadingIn) -> dict:
    if r.sensor_type not in RANGES:
        raise HTTPException(status_code=422, detail=f"Unknown sensor_type '{r.sensor_type}'")
    lo, hi = RANGES[r.sensor_type]
    ts = _parse_ts(r.timestamp)
    outlier = not (lo <= r.value <= hi)
    zid = _nearest_zone(db, r.latitude, r.longitude, r.zone_id)
    sens = db.query(Sensor).filter(Sensor.id == r.sensor_id).first()
    if not sens:
        sens = Sensor(id=r.sensor_id, sensor_type=r.sensor_type, zone_id=zid,
                      latitude=r.latitude, longitude=r.longitude,
                      depth_cm=r.depth_cm, unit=r.unit or UNITS[r.sensor_type])
        db.add(sens)
    dup = (db.query(SensorReading)
           .filter(SensorReading.sensor_id == r.sensor_id,
                   SensorReading.timestamp == ts).first())
    if dup:
        return {"sensor_id": r.sensor_id, "status": "deduplicated",
                "reading_id": dup.id, "outlier": dup.quality == "OUTLIER"}
    # ponytail: naive scan is fine (readings/volume small); index covers lookup
    row = SensorReading(sensor_id=r.sensor_id, timestamp=ts, value=r.value,
                        unit=r.unit or UNITS[r.sensor_type],
                        quality=("OUTLIER" if outlier else "OK"))
    db.add(row)
    db.flush()
    sens.last_seen = ts
    sens.status = "ONLINE"
    if not outlier:
        if r.sensor_type == "soil_moisture":
            db.add(SoilMoistureObservation(zone_id=zid, timestamp=ts,
                                           soil_moisture=r.value,
                                           source="SENSOR_SoilMoisture",
                                           quality_flag="SENSOR — in-situ reading"))
        elif r.sensor_type == "rainfall":
            db.add(RainfallObservation(zone_id=zid, timestamp=ts,
                                       rainfall_mm_per_hr=r.value,
                                       source="SENSOR_Rainfall",
                                       quality_flag="SENSOR — in-situ reading"))
    db.commit()
    return {"sensor_id": r.sensor_id, "status": "stored",
            "reading_id": row.id, "zone_id": zid,
            "outlier": outlier, "quality": row.quality}


@router.post("/sensors/readings")
def post_reading(body: ReadingIn, request: Request,
                 db: Session = Depends(get_db),
                 role: str = Depends(require_role("admin", "operator"))):
    rate_limit(_client_ip(request), limit=120)
    return _ingest_one(db, body)


@router.post("/sensors/soil-moisture")
def post_soil(body: ReadingIn, request: Request,
              db: Session = Depends(get_db),
              role: str = Depends(require_role("admin", "operator"))):
    body.sensor_type = "soil_moisture"
    rate_limit(_client_ip(request), limit=120)
    return _ingest_one(db, body)


@router.get("/sensors")
def list_sensors(db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    out = []
    for s in db.query(Sensor).all():
        health = "OFFLINE"
        if s.last_seen:
            last = s.last_seen.replace(tzinfo=UTC) if s.last_seen.tzinfo is None else s.last_seen
            age_h = (now - last).total_seconds() / 3600
            health = "ONLINE" if age_h < 6 else "STALE"
            s.status = health
        out.append({"sensor_id": s.id, "type": s.sensor_type, "zone_id": s.zone_id,
                    "health": health, "last_seen": s.last_seen.isoformat() if s.last_seen else None,
                    "unit": s.unit})
    db.commit()
    return {"sensors": out, "note": "ONLINE <6h since reading; STALE ≥6h; OFFLINE never seen"}


@router.get("/sensors/{sensor_id}/readings")
def sensor_readings(sensor_id: str, limit: int = 48, db: Session = Depends(get_db)):
    rows = (db.query(SensorReading).filter(SensorReading.sensor_id == sensor_id)
            .order_by(SensorReading.timestamp.desc()).limit(limit).all())
    return {"sensor_id": sensor_id,
            "readings": [{"timestamp": r.timestamp.isoformat(), "value": r.value,
                          "unit": r.unit, "quality": r.quality} for r in reversed(rows)]}
