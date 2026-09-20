"""Pydantic response/request schemas — the contract the frontend types/ folder mirrors."""
from pydantic import BaseModel, Field
from typing import Literal

Severity = Literal["LOW", "MODERATE", "HIGH", "VERY_HIGH"]


class Driver(BaseModel):
    factor: str
    impact: float


class ModelVersions(BaseModel):
    rf: str
    mamba: str
    fusion: str


class ZoneRisk(BaseModel):
    model_config = {"protected_namespaces": ()}
    zone_id: str
    name: str
    district: str
    static_score: float
    dynamic_score: float
    risk_score: float
    severity: Severity
    escalated: bool
    confidence: float
    rainfall_24h: float
    rainfall_72h: float
    rainfall_7d: float
    rainfall_slope: float
    soil_moisture: float
    drivers: list[Driver]
    summary: str
    model_versions: ModelVersions
    sim_time: str


class RiskHistoryPoint(BaseModel):
    timestamp: str
    risk_score: float
    static: float
    dynamic: float
    severity: Severity
    escalated: bool


class ZoneOut(BaseModel):
    id: str
    name: str
    district: str
    lat: float
    lng: float
    slope: float
    elevation: float
    population: int
    sar_acquisition_date: str | None
    sar_change_score: float


class ReportIn(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    # P2: typed as float so non-numeric input is a 422, not a server-side 500
    # from float(str) in the handler.
    accuracy: float | None = Field(default=None, ge=0, le=100000)
    landslide_type: str | None = Field(default=None, max_length=64)
    severity_observed: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=2000)
    client_timestamp: str | None = Field(default=None, max_length=64)


class ReportOut(BaseModel):
    id: str
    lat: float
    lng: float
    type: str | None
    severity: str | None
    description: str | None
    photo_url: str | None
    status: str
    at: str | None


class AlertOut(BaseModel):
    severity: str
    zone_id: str
    message: str
    provider: str
    status: str
    lang: str
    to: str
    recipient_name: str
    at: str


class SendAlertIn(BaseModel):
    zone_id: str
    severity: str
    lang: str = "en"


class SendResult(BaseModel):
    sent: int
    provider: str
    results: list[AlertOut]
