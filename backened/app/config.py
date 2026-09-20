"""Central configuration + calibration parameters.

Thresholds are CALIBRATION PARAMETERS, not validated constants —
documented in docs/ARCHITECTURE.md and unit-tested in test_fusion.py.
"""
import os
from dataclasses import dataclass

import yaml

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()  # development | production
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./geo_sentinel.db")
# Test-time override: when set, the app, worker and tests all bind to this
# DB (deterministic, disposable). CI sets sqlite:///./.pytest/geosentinel-test.db.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")
# Phase 2/5/8/9 knobs (all safe demo defaults; production sets them explicitly)
RAIN_PROVIDER = os.getenv("RAIN_PROVIDER", "mock")  # mock | openmeteo
SATELLITE_LIVE = os.getenv("SATELLITE_LIVE", "false").lower() == "true"
MAMBA_LIVE = os.getenv("MAMBA_LIVE", "false").lower() == "true"
MAMBA_WEIGHTS = os.getenv("MAMBA_WEIGHTS", "")
ALERT_COOLDOWN_MIN = float(os.getenv("ALERT_COOLDOWN_MIN", "360"))
# Provider switches (env-driven, demo-safe defaults; all labeled in /data-status)
WEATHER_PROVIDER = os.getenv("WEATHER_PROVIDER", RAIN_PROVIDER)  # openmeteo | imd | demo
SOIL_PROVIDER = os.getenv("SOIL_PROVIDER", "modeled")  # sensor | smap | modeled | demo
SATELLITE_PROVIDER = os.getenv("SATELLITE_PROVIDER", "demo")  # sentinel1 | demo
PUSH_PROVIDER = os.getenv("PUSH_PROVIDER", "mock")  # mock | fcm
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
WORKER_INTERVAL_MIN = float(os.getenv("WORKER_INTERVAL_MIN", "15"))
# Max distance (m) a request point may snap to the road graph. Points farther
# than this are OUT_OF_COVERAGE — they must never yield a route. Demo default
# covers rural Meghalaya dead-reckoning while rejecting other districts, let
# alone other continents ((0,0) snaps ~8600 km away).
ROUTE_MAX_SNAP_DISTANCE_M = float(os.getenv("ROUTE_MAX_SNAP_DISTANCE_M", "5000"))

THRESHOLDS_PATH = os.path.join(os.path.dirname(__file__), "..", "risk_thresholds.yaml")
with open(THRESHOLDS_PATH) as f:
    THRESHOLDS = yaml.safe_load(f)

STATIC_WEIGHT = float(os.getenv("STATIC_WEIGHT", THRESHOLDS["fusion"]["static_weight"]))
DYNAMIC_WEIGHT = float(os.getenv("DYNAMIC_WEIGHT", THRESHOLDS["fusion"]["dynamic_weight"]))

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)


@dataclass
class Settings:
    environment: str = ENVIRONMENT
    demo_mode: bool = DEMO_MODE
    database_url: str = DATABASE_URL
    sms_provider: str = SMS_PROVIDER
    static_weight: float = STATIC_WEIGHT
    dynamic_weight: float = DYNAMIC_WEIGHT
    media_dir: str = MEDIA_DIR
    rain_provider: str = RAIN_PROVIDER
    satellite_live: bool = SATELLITE_LIVE
    mamba_live: bool = MAMBA_LIVE
    alert_cooldown_min: float = ALERT_COOLDOWN_MIN
    weather_provider: str = WEATHER_PROVIDER
    soil_provider: str = SOIL_PROVIDER
    satellite_provider: str = SATELLITE_PROVIDER
    push_provider: str = PUSH_PROVIDER


settings = Settings()
