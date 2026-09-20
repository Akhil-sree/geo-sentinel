"""GEO-SENTINEL gs_v1 inference endpoints (SIH §18). DB-free, additive.

GET  /risk/gs_point?lat=..&lon=..        static susceptibility at a coordinate
POST /risk/gs_tabular  {features:{...}}   full 14-feature package assessment
POST /risk/gs_sequence {sequence:[[..x15]..], lat?, lon?, r24?, r72?, soil?}

Error semantics: invalid input -> 422, missing/unreadable model artifact ->
503 (structured, no stack traces or paths). A valid coordinate outside SRTM
coverage returns 200 with `"risk_score": null` (data-unavailable, not an
error). `temporal_risk` is always null (Mamba chance-level, unwired).
"""
import logging as _log

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..ml.gs_inference import assess_point, assess_sequence, assess_tabular

router = APIRouter()

MODEL_MISSING = "model artifact missing or unreadable (deployment without models volume?)"


def _safe(fn, *a, **k):
    import time as _t
    t0 = _t.perf_counter()
    try:
        return fn(*a, **k)
    except ValueError as e:
        return JSONResponse({"error": str(e)[:500], "risk_level": "UNKNOWN"},
                            status_code=422)
    except OSError as e:
        return JSONResponse({"error": MODEL_MISSING, "detail": str(e)[:200],
                             "risk_level": "UNKNOWN"}, status_code=503)
    finally:
        try:
            from app.observability import record_ml_inference
            record_ml_inference(round((_t.perf_counter() - t0) * 1000, 2))
        except Exception as e:
            _log.getLogger("geo-sentinel").debug("ML inference recording failed: %s", e)


class TabularIn(BaseModel):
    features: dict = Field(max_length=128)


class SequenceIn(BaseModel):
    sequence: list = Field(min_length=1, max_length=1000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    r24: float = 0.0
    r72: float = 0.0
    soil: float = 0.0


class GsOut(BaseModel):
    """Success contract: risk_score is null outside model coverage;
    temporal_risk is null until a validated temporal model is wired."""
    model_config = {"extra": "allow"}

    risk_score: float | None
    risk_level: str
    temporal_risk: float | None = None


@router.get("/risk/gs_point", response_model=GsOut)
def gs_point(lat: float = Query(..., ge=-90, le=90),
             lon: float = Query(..., ge=-180, le=180)):
    return _safe(assess_point, lat, lon)


@router.post("/risk/gs_tabular", response_model=GsOut)
def gs_tabular(body: TabularIn):
    return _safe(assess_tabular, body.features)


@router.post("/risk/gs_sequence", response_model=GsOut)
def gs_sequence(body: SequenceIn):
    return _safe(assess_sequence, body.sequence, body.lat, body.lon,
                 body.r24, body.r72, body.soil)
