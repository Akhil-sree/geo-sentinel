"""
Citizen report API.

Supports:
    - Creating offline citizen reports
    - Uploading report photographs
    - Listing recent reports
    - Explicit offline synchronization

Important:
    Citizen reports are NOT automatically treated as ground truth.
    They require validation before being added to a training inventory.
"""

import datetime as dt
import os
import secrets

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from ..auth import _client_ip, rate_limit
from ..config import settings
from ..database import get_db
from ..models_db import AuditLog, CitizenReport
from ..schemas import ReportIn

router = APIRouter()


# =============================================================
# FILE UPLOAD CONFIGURATION
# =============================================================

ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}

MAX_SIZE = 8 * 1024 * 1024  # 8 MB images
MAX_VIDEO = 25 * 1024 * 1024  # 25 MB video

# Magic bytes: reject executables masquerading as media
MAGIC = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG"],
    "image/webp": [b"RIFF"],
    "video/mp4": [b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00 ftyp"],
    "video/webm": [b"\x1a\x45\xdf\xa3"],
}


def _check_magic(head: bytes, mime: str) -> bool:
    return any(head.startswith(m) or m in head[:32] for m in MAGIC.get(mime, []))


def _safe_name(mime: str) -> str:
    """
    Generate a safe random filename.

    Client-provided filenames are never trusted.
    """

    ext = ALLOWED.get(mime)

    if not ext:
        raise HTTPException(
            status_code=415,
            detail=(
                "Only JPEG/PNG/WEBP images are allowed — "
                "executables are rejected."
            ),
        )

    return f"{secrets.token_hex(12)}{ext}"


# =============================================================
# CREATE CITIZEN REPORT
# =============================================================

@router.post(
    "/reports",
    status_code=201,
)
def create_report(
    r: ReportIn,
    db: Session = Depends(get_db),
):
    """
    Create a citizen landslide report.

    Designed to support offline-first synchronization:
    the client-generated report ID provides idempotency.
    """

    # ---------------------------------------------------------
    # Validate GPS coordinates
    # ---------------------------------------------------------

    if not (
        -90 <= r.latitude <= 90
        and -180 <= r.longitude <= 180
    ):
        raise HTTPException(
            status_code=422,
            detail="Invalid GPS coordinates",
        )

    # ---------------------------------------------------------
    # Idempotent offline-sync deduplication
    # ---------------------------------------------------------

    existing = db.get(CitizenReport, r.id) if r.id else None

    if existing:
        return {
            "id": r.id,
            "status": existing.status,
            "deduplicated": True,
        }

    # ---------------------------------------------------------
    # Parse client timestamp
    # ---------------------------------------------------------
    if r.client_timestamp:
        try:
            client_timestamp = dt.datetime.fromisoformat(
                r.client_timestamp
            )
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail="Invalid client_timestamp. Use ISO-8601 format.",
            ) from e
    else:
        client_timestamp = dt.datetime.now(dt.UTC)

    # ---------------------------------------------------------
    # Create report
    # ---------------------------------------------------------

    import secrets as _secrets
    report_id = r.id or _secrets.token_hex(16)

    rep = CitizenReport(
        id=report_id,
        latitude=r.latitude,
        longitude=r.longitude,
        accuracy=r.accuracy,
        description=r.description,
        landslide_type=r.landslide_type,
        severity_observed=r.severity_observed,
        client_timestamp=client_timestamp,
        synced_at=dt.datetime.now(dt.UTC),
        status="PENDING",
    )

    db.add(rep)

    db.add(
        AuditLog(
            action="REPORT_CREATED",
            detail=f"citizen_report={report_id}",
        )
    )

    db.commit()

    return {
        "id": report_id,
        "status": "PENDING",
        "note": (
            "Crowdsourced reports require validation/moderation "
            "before entering the training inventory. "
            "They are never automatically treated as ground truth."
        ),
    }


# =============================================================
# UPLOAD MEDIA
# =============================================================

@router.post(
    "/reports/{report_id}/media",
)
def upload_media(
    report_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Upload a photograph associated with a citizen report.
    Rate-limited (abuse-prone binary endpoint).
    """
    rate_limit(_client_ip(request),
               limit=20)

    # ---------------------------------------------------------
    # Find report
    # ---------------------------------------------------------

    rep = db.get(CitizenReport, report_id)

    if not rep:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    # ---------------------------------------------------------
    # Validate MIME type
    # ---------------------------------------------------------

    if file.content_type not in ALLOWED:
        raise HTTPException(
            status_code=415,
            detail="Invalid MIME type. Only JPEG/PNG/WEBP/MP4/WEBM allowed.",
        )

    # ---------------------------------------------------------
    # Read with size limit
    # ---------------------------------------------------------

    data = file.file.read(MAX_VIDEO + 1)
    limit = MAX_VIDEO if file.content_type.startswith("video/") else MAX_SIZE

    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (>{limit//1024//1024}MB)",
        )

    if not _check_magic(data[:32], file.content_type):
        raise HTTPException(status_code=422, detail="File header does not match declared type")

    # ---------------------------------------------------------
    # Generate safe filename
    # ---------------------------------------------------------

    name = _safe_name(file.content_type)

    media_dir = settings.media_dir

    os.makedirs(
        media_dir,
        exist_ok=True,
    )

    path = os.path.join(
        media_dir,
        name,
    )

    # ---------------------------------------------------------
    # Duplicate detection (content hash — offline re-uploads dedup)
    # ---------------------------------------------------------

    import hashlib as _hl

    from app.models_db import MediaHash
    digest = _hl.sha256(data).hexdigest()
    dupe = db.query(MediaHash).filter(MediaHash.sha256 == digest).first()
    if dupe:
        raise HTTPException(status_code=409, detail={
            "error": "duplicate media", "existing_report": dupe.report_id,
            "sha256": digest})

    # ---------------------------------------------------------
    # Store file
    # ---------------------------------------------------------

    with open(path, "wb") as f:
        f.write(data)

    # Demo:
    #     Local filesystem storage.
    #
    # Production:
    #     Use object storage such as S3 and return
    #     a signed URL.

    rep.photo_url = f"/media/{name}"
    db.add(MediaHash(report_id=report_id, sha256=digest))

    db.commit()

    return {
        "photo_url": rep.photo_url,
        "mime_type": file.content_type,
        "file_size": len(data),
    }


# =============================================================
# LIST REPORTS
# =============================================================

@router.get(
    "/reports",
)
def list_reports(
    db: Session = Depends(get_db),
):
    """
    Return the most recent 100 citizen reports.
    """

    reports = (
        db.query(CitizenReport)
        .order_by(CitizenReport.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": r.id,
            "lat": r.latitude,
            "lng": r.longitude,
            "status": r.status,
            "type": r.landslide_type,
            "severity": r.severity_observed,
            "description": r.description,
            "photo_url": r.photo_url,
            "client_timestamp": (
                r.client_timestamp.isoformat()
                if r.client_timestamp
                else None
            ),
        }
        for r in reports
    ]


# =============================================================
# REPORT GEO-INTELLIGENCE (assistance for reviewers, NOT truth)
# =============================================================

def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    import math
    r = 6371.0
    d1, d2 = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = (math.sin(d1 / 2) ** 2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(d2 / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


@router.get("/reports/{report_id}/geo-match")
def report_geo_match(
    report_id: str,
    db: Session = Depends(get_db),
):
    """Match a report to the nearest zone + nearby roads + that zone's
    latest risk context. Reviewer assistance only — a near-high-risk-zone
    report is still unverified until a human moderates it."""
    from ..models_db import RiskScore, RoadSegment, Zone
    rep = db.get(CitizenReport, report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    zones = db.query(Zone).all()
    if not zones:
        return {"report_id": report_id, "match": None}
    nearest = min(zones, key=lambda z: _haversine_km(
        rep.latitude, rep.longitude, z.latitude, z.longitude))
    dist = _haversine_km(rep.latitude, rep.longitude,
                         nearest.latitude, nearest.longitude)
    roads = [r for r in db.query(RoadSegment).all()
             if r.from_zone == nearest.id or r.to_zone == nearest.id]
    latest = (db.query(RiskScore).filter(RiskScore.zone_id == nearest.id)
              .order_by(RiskScore.timestamp.desc()).first())
    # PostGIS when available (ST_DWithin), haversine fallback on sqlite —
    # same shape either way; backend reported in the response.
    from app.geo.postgis import roads_within_km
    prox = roads_within_km(db, rep.latitude, rep.longitude, 30.0)
    near = [r for r in prox["roads"]
            if r["road"] in {rr.name for rr in roads}][:3]
    spatial_backend = prox["spatial_backend"]
    return {"report_id": report_id,
            "match": {"zone_id": nearest.id, "zone_name": nearest.name,
                      "distance_km": round(dist, 2),
                      "zone_risk": latest.risk_score if latest else None,
                      "zone_severity": latest.severity if latest else None,
                      "nearby_roads": near,
                      "spatial_backend": spatial_backend},
            "note": "Geospatial assistance for reviewers — not verification"}


# =============================================================
# OFFLINE SYNCHRONIZATION
# =============================================================

@router.post(
    "/reports/{report_id}/sync",
)
def sync_report(
    report_id: str,
    db: Session = Depends(get_db),
):
    """
    Explicitly mark an existing report as synchronized.

    This is useful for an offline-first mobile client that
    maintains a local upload queue.
    """

    rep = db.get(
        CitizenReport,
        report_id,
    )

    if not rep:
        raise HTTPException(
            status_code=404,
            detail=(
                "Report not found — "
                "device should retry using its offline queue."
            ),
        )

    rep.synced_at = dt.datetime.now(dt.UTC)

    db.commit()

    return {
        "id": report_id,
        "synced": True,
    }