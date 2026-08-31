"""Central configuration + calibration parameters.

Thresholds are CALIBRATION PARAMETERS, not validated constants —
documented in docs/ARCHITECTURE.md and unit-tested in test_fusion.py.
"""
import os
import yaml
from dataclasses import dataclass, field

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./geo_sentinel.db")
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")

THRESHOLDS_PATH = os.path.join(os.path.dirname(__file__), "..", "risk_thresholds.yaml")
with open(THRESHOLDS_PATH) as f:
    THRESHOLDS = yaml.safe_load(f)

STATIC_WEIGHT = float(os.getenv("STATIC_WEIGHT", THRESHOLDS["fusion"]["static_weight"]))
DYNAMIC_WEIGHT = float(os.getenv("DYNAMIC_WEIGHT", THRESHOLDS["fusion"]["dynamic_weight"]))

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)


@dataclass
class Settings:
    demo_mode: bool = DEMO_MODE
    database_url: str = DATABASE_URL
    sms_provider: str = SMS_PROVIDER
    static_weight: float = STATIC_WEIGHT
    dynamic_weight: float = DYNAMIC_WEIGHT
    media_dir: str = MEDIA_DIR


settings = Settings()
