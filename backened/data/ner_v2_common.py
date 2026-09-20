"""Shared ner_v2 constants + small helpers (SIH existing-data integration).

Everything here is additive: ner_v1, seq_real_v2, the registry history and
datasets/ are never touched by this module. Statuses follow the integration
spec; UNKNOWN is a first-class outcome, never a guess.
"""
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(DATA_DIR)
DATASETS_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "datasets")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
META_DIR = os.path.join(DATA_DIR, "metadata")

VERSION = "ner_v2"
FEATURE_VERSION = "nerfeat_v2"
CODE_VERSION = "ner-pipeline-2.0"

# Candidate lifecycle (spec §NER_V2 REQUIREMENTS)
ST_RAW = "RAW"
ST_CANDIDATE = "CANDIDATE"
ST_QC_PASSED = "QC_PASSED"
ST_QC_FAILED = "QC_FAILED"
ST_DUPLICATE = "DUPLICATE"
ST_LOCATION_WEAK = "LOCATION_WEAK"
ST_DATE_WEAK = "DATE_WEAK"
ST_SOURCE_UNVERIFIED = "SOURCE_UNVERIFIED"
ST_TRAINING_ELIGIBLE = "TRAINING_ELIGIBLE"

# Reports location-accuracy buckets, km (GLC scheme; anything coarser or
# blank is weak for training alignment)
ACC_KM = {
    "Known exactly": 0.0,
    "Known within 1 km": 1.0,
    "Known within 5 km": 5.0,
    "Known within 10 km": 10.0,
    "Known within 25 km": 25.0,
    "Known within 50 km": 50.0,
    "Known within 100 km": 100.0,
    "Known within 250 km": 250.0,
}
# <=5 km aligns with the existing 2 km dedup radius + honest error margin
TRAINING_ACC_KM = 5.0
DEDUP_KM = 2.0  # same threshold as ner_common.dedup_records

NER_DIVISIONS = {"Assam", "Meghalaya", "Arunachal Pradesh", "Manipur",
                 "Mizoram", "Nagaland", "Sikkim", "Tripura"}

# Gauge QC rules (documented, never silent)
GAUGE_MISSING = {-999.0, -9999.0}
HOURLY_SPIKE_MM = 500.0    # above this an hourly gauge value is flagged, not used
DAILY_SPIKE_MM = 1000.0    # above this a daily gauge value is flagged, not used
HOURLY_NEG_TOL = 0.0       # negatives are sensor faults

# Feature provenance tags for the v2 feature family
PROV_GAUGE = "gauge-unverified"     # observed gauge, origin UNVERIFIED
PROV_OM = "openmeteo-archive"
PROV_SRTM_RASTER = "srtm1arc-raster"
PROV_SOIL_MAP = "soilmap-unverified"  # static polygons, authorship UNKNOWN
PROV_ROAD_PBF = "osm-pbf-unknown-vintage"
ROAD_VINTAGE = "UNKNOWN"


def utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
