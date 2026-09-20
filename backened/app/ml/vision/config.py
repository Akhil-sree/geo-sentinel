"""Vision module configuration — all thresholds in one place."""
import os

VISION_MODEL = os.getenv("VISION_MODEL", "segformer-b0")
VISION_MODE = os.getenv("VISION_MODE", "demo")
VISION_CHECKPOINT = os.getenv("VISION_CHECKPOINT", "")
VISION_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_CONFIDENCE_THRESHOLD", "0.5"))
VISION_MIN_REGION_AREA = int(os.getenv("VISION_MIN_REGION_AREA", "100"))
VISION_INPUT_SIZE = (512, 512)
VISION_MAX_FILE_SIZE_MB = 10
VISION_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}

STATUS_WEIGHT = {
    "OPEN": 1.0,
    "UNDER_REPAIR": 1.5,
    "DAMAGED": 3.0,
    "BLOCKED": float("inf"),
}

OBSERVATION_SEVERITY_THRESHOLDS = {
    "HIGH": 0.6,
    "MODERATE": 0.3,
    "LOW": 0.0,
}
