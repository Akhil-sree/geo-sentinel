from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class Zone(Base):
    __tablename__ = "zones"
    id = Column(String, primary_key=True)              # e.g. "Z1"
    name = Column(String, nullable=False)
    district = Column(String, nullable=False)
    state = Column(String, default="Meghalaya")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    # static terrain/exposure features (in production: terrain_features + exposure_features tables)
    slope = Column(Float)
    elevation = Column(Float)
    ruggedness = Column(Float)
    road_proximity = Column(Float)
    drainage_proximity = Column(Float)
    settlement_density = Column(Float)
    population = Column(Integer, default=0)
    sar_change_score = Column(Float, default=0.0)
    sar_acquisition_date = Column(String, nullable=True)
    sar_previous_acquisition_date = Column(String, nullable=True)
    geom = Column(Text)   # WKT polygon; demo-generated

class RainfallObservation(Base):
    __tablename__ = "rainfall_observations"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    timestamp = Column(DateTime, index=True)
    rainfall_mm_per_hr = Column(Float)
    source = Column(String, default="IMD_MOCK")
    quality_flag = Column(String, default="DEMO_DATA")   # never silently mixed with real data

class SoilMoistureObservation(Base):
    __tablename__ = "soil_moisture_observations"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    timestamp = Column(DateTime, index=True)
    soil_moisture = Column(Float)          # 0..1 saturation proxy
    source = Column(String, default="SMAP_MOCK")
    quality_flag = Column(String, default="DEMO DATA — regional proxy, coarse resolution")

class LandslideEvent(Base):
    __tablename__ = "landslide_events"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, index=True)
    event_date = Column(DateTime, index=True)
    landslide_type = Column(String)
    trigger = Column(String, default="Rainfall")
    source = Column(String, default="GSI/NRSC_DEMO")
    confidence = Column(String, default="medium")

class RiskScore(Base):
    __tablename__ = "risk_scores"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    static_score = Column(Float)
    dynamic_score = Column(Float)
    risk_score = Column(Float)
    severity = Column(String)
    escalated = Column(Boolean, default=False)
    confidence = Column(Float)             # model probability, labeled as such
    rf_version = Column(String)
    mamba_version = Column(String)
    fusion_version = Column(String, default="fusion_v1")
    drivers_json = Column(Text)            # XAI output

class CitizenReport(Base):
    __tablename__ = "citizen_reports"
    id = Column(String, primary_key=True)  # client-generated (offline-first)
    latitude = Column(Float)
    longitude = Column(Float)
    accuracy = Column(Float)
    description = Column(Text)
    landslide_type = Column(String)
    severity_observed = Column(String)
    photo_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING/REVIEWING/VERIFIED/REJECTED/USED_FOR_TRAINING
    client_timestamp = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    synced_at = Column(DateTime, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, index=True)
    severity = Column(String)
    message = Column(Text)
    language = Column(String, default="en")
    recipient = Column(String)
    recipient_name = Column(String)
    provider = Column(String, default="MockSMSProvider")
    status = Column(String, default="DELIVERED")   # SENT/FAILED/DELIVERED
    created_at = Column(DateTime, server_default=func.now())

class Recipient(Base):
    __tablename__ = "recipients"
    id = Column(Integer, primary_key=True)
    phone_number = Column(String)          # DEMO DATA — masked
    preferred_language = Column(String, default="en")
    zone_id = Column(String, index=True)
    name = Column(String)
    consent_status = Column(String, default="GRANTED_DEMO")
    active = Column(Boolean, default=True)

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id = Column(Integer, primary_key=True)
    source = Column(String, index=True)
    status = Column(String)                 # OK/FAILED/STALE
    detail = Column(Text, nullable=True)
    ran_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    action = Column(String, index=True)
    detail = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class ZoneFeature(Base):
    """Derived per-zone features computed from latest observations."""
    __tablename__ = "zone_features"
    zone_id = Column(String, ForeignKey("zones.id"), primary_key=True)
    rainfall_24h = Column(Float, default=0.0)
    rainfall_72h = Column(Float, default=0.0)
    rainfall_7d = Column(Float, default=0.0)
    rainfall_slope = Column(Float, default=0.0)
    soil_moisture = Column(Float, default=0.34)
    sar_change_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now())

# Backward-compat aliases used by ingest/runner.py and older routers
IngestionLog = IngestionRun
RainfallObs = RainfallObservation
SoilMoistureObs = SoilMoistureObservation

class SARObs(Base):
    """SAR observations stored by Sentinel-1 adapter."""
    __tablename__ = "sar_observations"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    acquisition_date = Column(DateTime)
    previous_ac = Column(String, nullable=True)
    sar_change_score = Column(Float)
    source = Column(String, default="Sentinel1_MOCK")

# AlertLog alias (older routers/alerts.py used this name)
AlertLog = Alert


class RoadSegment(Base):
    """Road segments between zones — status tracking for connectivity dashboard."""
    __tablename__ = "road_segments"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    from_zone = Column(String, ForeignKey("zones.id"), index=True)
    to_zone = Column(String, ForeignKey("zones.id"), index=True)
    road_type = Column(String, default="district")     # national / state / district / village
    length_km = Column(Float, default=0.0)
    status = Column(String, default="OPEN")             # OPEN / BLOCKED / DAMAGED / UNDER_REPAIR
    blockage_reason = Column(String, nullable=True)     # landslide / flood / slope_failure / maintenance
    last_updated = Column(DateTime, server_default=func.now())
    reported_by = Column(String, default="SYSTEM")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


class EmergencyTask(Base):
    """Emergency response tasks — assigned to zones based on risk priority."""
    __tablename__ = "emergency_tasks"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    task_type = Column(String, nullable=False)          # evacuation / road_clear / shelter_setup / patrol / supply
    title = Column(String, nullable=False)
    description = Column(Text)
    priority = Column(String, default="MEDIUM")         # CRITICAL / HIGH / MEDIUM / LOW
    status = Column(String, default="PENDING")          # PENDING / IN_PROGRESS / COMPLETED / CANCELLED
    assigned_team = Column(String, nullable=True)
    estimated_time = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
