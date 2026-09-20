"""Pydantic schemas for the vision module."""

from pydantic import BaseModel


class VisionAnalyzeRequest(BaseModel):
    report_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    zone_id: str | None = None


class VisionObservation(BaseModel):
    model_config = {"protected_namespaces": ()}

    report_id: str | None = None
    model_name: str = "segformer-b0"
    model_mode: str = "demo"
    landslide_detected: bool
    confidence: float
    affected_pixel_ratio: float
    observation_severity: str
    bbox: list[int] = []
    num_regions: int = 0
    geometry: dict | None = None
    image_width: int | None = None
    image_height: int | None = None
    timestamp: str = ""
    warning: str | None = None


class VisionReport(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    report_id: str | None = None
    model_name: str
    model_mode: str
    confidence: float
    pixel_ratio: float
    severity: str
    geometry: dict | None = None
    image_path: str | None = None
    landslide_detected: bool
    created_at: str


class CorroborationResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    zone_id: str
    zone_risk_score: float
    zone_severity: str
    observation_score: float
    observation_severity: str
    corroboration: str  # "CORROBORATED" | "VISUAL_ANOMALY" | "INCONCLUSIVE"
    explanation: str
