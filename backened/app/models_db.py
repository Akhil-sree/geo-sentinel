from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class Zone(Base):
    __tablename__ = "zones"
    id = Column(String, primary_key=True)              # e.g. "Z1"
    name = Column(String, nullable=False)
    district = Column(String, nullable=False, index=True)
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

    __table_args__ = (
        Index("ix_zones_district_state", "district", "state"),
    )

class RainfallObservation(Base):
    __tablename__ = "rainfall_observations"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    timestamp = Column(DateTime, index=True)
    rainfall_mm_per_hr = Column(Float)
    source = Column(String, default="IMD_MOCK")
    quality_flag = Column(String, default="DEMO_DATA")   # never silently mixed with real data

    __table_args__ = (
        Index("ix_rainfall_zone_ts", "zone_id", "timestamp"),
        Index("ix_rainfall_source_ts", "source", "timestamp"),
    )

class SoilMoistureObservation(Base):
    __tablename__ = "soil_moisture_observations"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    timestamp = Column(DateTime, index=True)
    soil_moisture = Column(Float)          # 0..1 saturation proxy
    source = Column(String, default="SMAP_MOCK")
    quality_flag = Column(String, default="DEMO DATA — regional proxy, coarse resolution")

    __table_args__ = (
        Index("ix_soil_zone_ts", "zone_id", "timestamp"),
        Index("ix_soil_source_ts", "source", "timestamp"),
    )

class LandslideEvent(Base):
    __tablename__ = "landslide_events"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, index=True)
    event_date = Column(DateTime, index=True)
    landslide_type = Column(String)
    trigger = Column(String, default="Rainfall")
    source = Column(String, default="GSI/NRSC_DEMO")
    confidence = Column(String, default="medium")

    __table_args__ = (
        Index("ix_landslide_zone_date", "zone_id", "event_date"),
    )

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

    __table_args__ = (
        Index("ix_risk_zone_ts", "zone_id", "timestamp"),
        Index("ix_risk_severity_ts", "severity", "timestamp"),
    )

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

    __table_args__ = (
        Index("ix_report_status_ts", "status", "created_at"),
        Index("ix_report_zone_ts", "status", "created_at"),  # zone not directly stored, but can be derived
    )

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

    __table_args__ = (
        Index("ix_alert_zone_ts", "zone_id", "created_at"),
        Index("ix_alert_status_ts", "status", "created_at"),
    )

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

    __table_args__ = (
        Index("ix_ingestion_source_ts", "source", "ran_at"),
    )

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

    __table_args__ = (
        Index("ix_road_status_type", "status", "road_type"),
        Index("ix_road_from_to", "from_zone", "to_zone"),
    )


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

    __table_args__ = (
        Index("ix_task_zone_status", "zone_id", "status"),
        Index("ix_task_priority_ts", "priority", "created_at"),
    )


class SchemaVersion(Base):
    """Versioned migration ledger (Phase 17). Every applied step is recorded;
    steps are idempotent and never destructive."""
    __tablename__ = "schema_versions"
    version = Column(Integer, primary_key=True)
    applied_at = Column(DateTime, server_default=func.now())
    note = Column(String, default="")


class TerrainDEM(Base):
    """Real DEM derivatives per zone (SRTM 30m via OpenTopodata).

    STATIC seed profiles stay authoritative for the legacy RF path;
    these observed values feed new features + provenance. One row/zone.
    """
    __tablename__ = "terrain_dem"
    zone_id = Column(String, ForeignKey("zones.id"), primary_key=True)
    dem_source = Column(String, default="SRTM GL1 30m via OpenTopodata")
    resolution_m = Column(Float, default=30.0)
    retrieved_at = Column(DateTime, nullable=True)
    elevation_m = Column(Float, nullable=True)   # grid center
    slope_deg = Column(Float, nullable=True)     # Horn 3x3 on center
    aspect_deg = Column(Float, nullable=True)    # downslope direction
    ruggedness_m = Column(Float, nullable=True)  # std of 5x5 window
    relief_m = Column(Float, nullable=True)      # max-min of 5x5 window


class SatScene(Base):
    """Real Sentinel-1 acquisition METADATA (ASF discovery).

    Metadata only — no imagery processed, nothing enters the risk path.
    """
    __tablename__ = "sat_scenes"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    granule = Column(String, unique=True, index=True)
    start_time = Column(DateTime, index=True)
    beam_mode = Column(String, default="IW")
    flight_direction = Column(String, nullable=True)
    polarization = Column(String, nullable=True)
    download_url = Column(String, nullable=True)
    md5 = Column(String, nullable=True)
    source = Column(String, default="ASF Vertex discovery")


class MediaHash(Base):
    """Content-hash dedup for uploads (offline re-uploads, double submits)."""
    __tablename__ = "media_hashes"
    id = Column(Integer, primary_key=True)
    report_id = Column(String, ForeignKey("citizen_reports.id"), index=True)
    sha256 = Column(String, index=True, unique=True)


class VisionObservation(Base):
    """CV observation records — SegFormer segmentation results on citizen/field photos."""
    __tablename__ = "vision_observations"
    id = Column(Integer, primary_key=True)
    report_id = Column(String, ForeignKey("citizen_reports.id"), nullable=True, index=True)
    model_name = Column(String, default="segformer-b0")
    model_mode = Column(String, default="demo")
    confidence = Column(Float, default=0.0)
    pixel_ratio = Column(Float, default=0.0)
    severity = Column(String, default="NONE")
    landslide_detected = Column(Boolean, default=False)
    geometry_json = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    zone_id = Column(String, ForeignKey("zones.id"), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    warning = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Sensor(Base):
    """IoT sensor registry — soil-moisture, rainfall, tilt/inclinometer,
    pore-pressure. Health derived from last reading age (ONLINE/STALE/OFFLINE)."""
    __tablename__ = "sensors"
    id = Column(String, primary_key=True)          # e.g. "SM-Z1-01"
    sensor_type = Column(String, index=True)       # soil_moisture | rainfall | tilt | pore_pressure
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    depth_cm = Column(Float, nullable=True)
    unit = Column(String, default="")
    status = Column(String, default="OFFLINE")     # ONLINE | STALE | OFFLINE
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SensorReading(Base):
    """Normalized sensor readings — dedup on (sensor_id, timestamp)."""
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True)
    sensor_id = Column(String, ForeignKey("sensors.id"), index=True)
    timestamp = Column(DateTime, index=True)
    value = Column(Float)
    unit = Column(String, default="")
    quality = Column(String, default="OK")         # OK | OUTLIER | STALE | DEMO


class Village(Base):
    """Village/exposure points — STATIC indicative demo data, not census."""
    __tablename__ = "villages"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    population = Column(Integer, default=0)
    criticality = Column(String, default="normal")  # normal | high | critical


class Infrastructure(Base):
    """Critical infrastructure points — schools, hospitals, bridges, shelters."""
    __tablename__ = "infrastructure"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, index=True)              # school | hospital | bridge | shelter | road | other
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    criticality = Column(String, default="normal")  # normal | high | critical


class SpatialInventory(Base):
    """Spatial-only landslide inventory (e.g. GSI year-unknown slides).

    NEVER used as temporal training labels — GIS display + spatial prior only.
    Temporal labels live in landslide_events (dated) by design."""
    __tablename__ = "spatial_inventory"
    id = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    district = Column(String, nullable=True)
    source = Column(String, default="GSI")
    data_quality = Column(String, default="spatial-only, year-unknown")
    external_id = Column(String, nullable=True, index=True)


class SatelliteFeature(Base):
    """Satellite-derived features per zone/acquisition — change-detection
    outputs. MODELED/DEMO unless a credentialed provider marks OBSERVED."""
    __tablename__ = "satellite_features"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), index=True)
    acquisition_date = Column(DateTime, index=True)
    scene_id = Column(String, nullable=True)
    change_score = Column(Float, default=0.0)
    candidate = Column(Boolean, default=False)     # landslide-candidate flag
    status = Column(String, default="DEMO")        # OBSERVED | MODELED | DEMO
    source = Column(String, default="SATELLITE_DEMO")


class NerInventory(Base):
    """NER-scale landslide inventory (SIH data-pipeline §3).

    Unified table with record_kind split: TEMPORAL rows (EXACT_DATE) may
    train temporal models; SPATIAL rows never become temporal labels.
    Dedup via canonical_event_id (uncertain pairs stay separate + flagged).
    """
    __tablename__ = "ner_inventory"
    id = Column(Integer, primary_key=True)
    record_kind = Column(String, index=True)       # TEMPORAL | SPATIAL
    source = Column(String, index=True)            # coolr | gsi | nrsc | demo
    source_event_id = Column(String, nullable=True, index=True)
    canonical_event_id = Column(String, nullable=True, index=True)
    source_count = Column(Integer, default=1)
    event_date = Column(DateTime, nullable=True, index=True)
    date_quality = Column(String, default="UNKNOWN")  # EXACT/YEAR_ONLY/MONTH_ONLY/UNKNOWN/ESTIMATED
    latitude = Column(Float)
    longitude = Column(Float)
    district = Column(String, nullable=True)
    state = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    source_url = Column(String, nullable=True)
    data_quality = Column(String, default="")
    review_flag = Column(String, nullable=True)
    provenance_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class DatasetVersion(Base):
    """Immutable dataset release ledger (SIH §24). Never overwritten;
    new versions append."""
    __tablename__ = "dataset_versions"
    version = Column(String, primary_key=True)     # e.g. ner_v1
    region = Column(String, default="NER")
    created_at = Column(DateTime, server_default=func.now())
    sources_json = Column(Text, nullable=True)
    counts_json = Column(Text, nullable=True)
    feature_version = Column(String, default="")
    code_version = Column(String, default="")
    checksum = Column(String, nullable=True)
    status = Column(String, default="DRAFT")       # DRAFT | VALIDATED | BLOCKED


class TrainingSample(Base):
    """Versioned training feature store (SIH §20-21): one row per
    event/control with full provenance + missingness record."""
    __tablename__ = "training_samples"
    id = Column(Integer, primary_key=True)
    dataset_version = Column(String, ForeignKey("dataset_versions.version"), index=True)
    sample_id = Column(String, index=True)
    event_id = Column(Integer, ForeignKey("ner_inventory.id"), nullable=True)
    label = Column(String, index=True)             # RECORDED_LANDSLIDE | NO_RECORDED_LANDSLIDE
    event_date = Column(DateTime, nullable=True)
    latitude = Column(Float)
    longitude = Column(Float)
    features_json = Column(Text)
    provenance_json = Column(Text, nullable=True)
    missingness_json = Column(Text, nullable=True)
    split = Column(String, nullable=True)          # train | val | test
    group_id = Column(String, nullable=True)       # spatial group (district/state block)
