"""NER dataset + training-data APIs (SIH §35).

New (no duplicates of existing routes):
GET /api/datasets, GET /api/datasets/{id}, GET /api/landslides/temporal,
GET /api/landslides/spatial, GET /api/data-quality, GET /api/models/{id},
GET /api/features/{event_id}, GET /api/rainfall/history,
GET /api/soil/history, GET /api/terrain/features

Existing neighbours (reused, not duplicated): /api/landslides/inventory,
/api/models, /api/satellite/*, /api/risk/{z}/rainfall(-windows),
/api/risk/{z}/soil-moisture.
"""
import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import (DatasetVersion, NerInventory, TrainingSample,
                           RainfallObservation, SoilMoistureObservation,
                           TerrainDEM)

router = APIRouter()
META = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "data", "metadata"))
RAW = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..",
                                    "data", "raw"))

_SAFE_META = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.json$")


def _read_json_under(base: str, name: str) -> dict | None:
    """Read a JSON report only if `name` is a plain filename resolving under
    `base`. Blocks `../`, absolute paths, and symlink escape."""
    if not _SAFE_META.match(name or ""):
        return None
    p = os.path.normpath(os.path.join(base, name))
    if os.path.dirname(p) != base:
        return None
    try:
        if not os.path.isfile(p):
            return None
    except (OSError, ValueError):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _meta(name: str) -> dict | None:
    return _read_json_under(META, name)


@router.get("/datasets")
def datasets(db: Session = Depends(get_db)):
    rows = db.query(DatasetVersion).order_by(DatasetVersion.created_at.desc()).all()
    return {"datasets": [{"version": r.version, "region": r.region,
                          "created_at": r.created_at.isoformat() if r.created_at else None,
                          "feature_version": r.feature_version,
                          "code_version": r.code_version, "checksum": r.checksum,
                          "status": r.status,
                          "counts": json.loads(r.counts_json or "{}")}
                         for r in rows]}


@router.get("/datasets/{version}")
def dataset_one(version: str, db: Session = Depends(get_db)):
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", version or ""):
        raise HTTPException(status_code=404, detail="Unknown dataset version")
    r = db.query(DatasetVersion).filter(DatasetVersion.version == version).first()
    if not r:
        raise HTTPException(status_code=404, detail="Unknown dataset version")
    return {"version": r.version, "region": r.region,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "sources": json.loads(r.sources_json or "{}"),
            "counts": json.loads(r.counts_json or "{}"),
            "feature_version": r.feature_version, "code_version": r.code_version,
            "checksum": r.checksum, "status": r.status,
            "metadata": _meta(f"ner_training_{version}.json"),
            "leakage": _meta(f"ner_leakage_{version}.json")}


@router.get("/landslides/temporal")
def landslides_temporal(db: Session = Depends(get_db)):
    """Dated NER events (EXACT_DATE) — the only rows that may train temporal models."""
    rows = (db.query(NerInventory)
            .filter(NerInventory.record_kind == "TEMPORAL")
            .order_by(NerInventory.event_date).all())
    return {"n": len(rows), "use": "temporal training labels (dated only)",
            "events": [{"id": r.id, "canonical": r.canonical_event_id,
                        "event_date": r.event_date.isoformat() if r.event_date else None,
                        "date_quality": r.date_quality, "lat": r.latitude, "lng": r.longitude,
                        "district": r.district, "source": r.source,
                        "confidence": r.confidence, "data_quality": r.data_quality}
                       for r in rows]}


@router.get("/landslides/spatial")
def landslides_spatial(limit: int = Query(500, ge=1, le=2000),
                       db: Session = Depends(get_db)):
    """Year-unknown / undated NER occurrences — GIS + spatial prior ONLY."""
    rows = (db.query(NerInventory)
            .filter(NerInventory.record_kind == "SPATIAL").limit(limit).all())
    total = db.query(NerInventory).filter(NerInventory.record_kind == "SPATIAL").count()
    return {"n": total, "returned": len(rows),
            "use": "GIS display + spatial prior ONLY — never temporal labels",
            "records": [{"id": r.id, "lat": r.latitude, "lng": r.longitude,
                         "district": r.district, "source": r.source,
                         "date_quality": r.date_quality,
                         "data_quality": r.data_quality} for r in rows]}


@router.get("/data-quality")
def data_quality():
    """Dataset quality report: downloaded/parsed/valid/rejected/dupes/
    NER/temporal/spatial per source. Missing file → NOT_RUN (never invented)."""
    return {"inventory": _meta("ner_inventory_report.json") or "NOT_RUN",
            "coolr": (_read_json_under(RAW, "coolr_download_report.json")
                      or "NOT_RUN"),
            "note": "Per-source ingest reports live in data/raw/*_report.json"}


@router.get("/models/{model_id}")
def model_one(model_id: str):
    from app.ml import registry as reg
    rows = [m for m in reg.all_models() if m["model_id"] == model_id]
    if not rows:
        raise HTTPException(status_code=404, detail="Unknown model")
    return {"model_id": model_id, "versions": rows}


@router.get("/features/{sample_id}")
def features_one(sample_id: str, db: Session = Depends(get_db)):
    """Feature provenance for one training sample: every value traceable."""
    r = db.query(TrainingSample).filter(TrainingSample.sample_id == sample_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Unknown sample")
    return {"sample_id": r.sample_id, "label": r.label,
            "dataset_version": r.dataset_version, "split": r.split,
            "group_id": r.group_id,
            "features": json.loads(r.features_json or "{}"),
            "provenance": json.loads(r.provenance_json or "{}"),
            "missingness": json.loads(r.missingness_json or "{}")}


@router.get("/rainfall/history")
def rainfall_history(zone_id: str | None = None,
                     limit: int = Query(168, ge=1, le=2000),
                     db: Session = Depends(get_db)):
    q = db.query(RainfallObservation).order_by(RainfallObservation.timestamp.desc())
    if zone_id:
        q = q.filter(RainfallObservation.zone_id == zone_id)
    rows = q.limit(limit).all()
    return {"n": len(rows),
            "observations": [{"zone_id": r.zone_id,
                              "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                              "rainfall_mm_per_hr": r.rainfall_mm_per_hr,
                              "source": r.source, "quality_flag": r.quality_flag}
                             for r in reversed(rows)]}


@router.get("/soil/history")
def soil_history(zone_id: str | None = None,
                 limit: int = Query(168, ge=1, le=2000),
                 db: Session = Depends(get_db)):
    q = db.query(SoilMoistureObservation).order_by(SoilMoistureObservation.timestamp.desc())
    if zone_id:
        q = q.filter(SoilMoistureObservation.zone_id == zone_id)
    rows = q.limit(limit).all()
    return {"n": len(rows),
            "label": "Zone observations (SENSOR in-situ where posted, else MODELED proxy)",
            "observations": [{"zone_id": r.zone_id,
                              "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                              "soil_moisture": r.soil_moisture,
                              "source": r.source, "quality_flag": r.quality_flag}
                             for r in reversed(rows)]}


@router.get("/terrain/features")
def terrain_features(db: Session = Depends(get_db)):
    rows = db.query(TerrainDEM).all()
    return {"dem_source": "SRTM GL1 30m via OpenTopodata (+ STATIC seed profiles)",
            "zones": [{"zone_id": r.zone_id, "resolution_m": r.resolution_m,
                       "elevation_m": r.elevation_m, "slope_deg": r.slope_deg,
                       "aspect_deg": r.aspect_deg, "ruggedness_m": r.ruggedness_m,
                       "relief_m": r.relief_m} for r in rows]}
