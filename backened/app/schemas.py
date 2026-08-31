"""Pydantic response/request schemas — the contract the frontend types/ folder mirrors."""
from pydantic import BaseModel
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
    id: str | None = None
    latitude: float
    longitude: float
    accuracy: str | None = None
    landslide_type: str | None = None
    severity_observed: str | None = None
    description: str | None = None
    client_timestamp: str | None = None


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


class SendResult(BaseModel):
    sent: int
    provider: str
    results: list[AlertOut]
