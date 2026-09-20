"""Pydantic schemas for the vision module."""
from pydantic import BaseModel
from typing import Optional


class VisionAnalyzeRequest(BaseModel):
    report_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone_id: Optional[str] = None


class VisionObservation(BaseModel):
    model_config = {"protected_namespaces": ()}

    report_id: Optional[str] = None
    model_name: str = "segformer-b0"
    model_mode: str = "demo"
    landslide_detected: bool
    confidence: float
    affected_pixel_ratio: float
    observation_severity: str
    bbox: list[int] = []
    num_regions: int = 0
    geometry: Optional[dict] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    timestamp: str = ""
    warning: Optional[str] = None


class VisionReport(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    report_id: Optional[str] = None
    model_name: str
    model_mode: str
    confidence: float
    pixel_ratio: float
    severity: str
    geometry: Optional[dict] = None
    image_path: Optional[str] = None
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
