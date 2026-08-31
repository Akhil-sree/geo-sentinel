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
    UploadFile,
)

from sqlalchemy.orm import Session

from ..database import get_db
from ..models_db import CitizenReport, AuditLog
from ..schemas import ReportIn
from ..config import settings


router = APIRouter()


# =============================================================
# FILE UPLOAD CONFIGURATION
# =============================================================

ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_SIZE = 8 * 1024 * 1024  # 8 MB


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
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Invalid client_timestamp. Use ISO-8601 format.",
            )
    else:
        client_timestamp = dt.datetime.utcnow()

    # ---------------------------------------------------------
    # Create report
    # ---------------------------------------------------------

    import secrets as _secrets
    report_id = r.id or _secrets.token_hex(16)

    rep = CitizenReport(
        id=report_id,
        latitude=r.latitude,
        longitude=r.longitude,
        accuracy=float(r.accuracy) if r.accuracy else None,
        description=r.description,
        landslide_type=r.landslide_type,
        severity_observed=r.severity_observed,
        client_timestamp=client_timestamp,
        synced_at=dt.datetime.utcnow(),
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
):
    """
    Upload a photograph associated with a citizen report.
    """

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
            detail="Invalid MIME type. Only JPEG/PNG/WEBP allowed.",
        )

    # ---------------------------------------------------------
    # Read with size limit
    # ---------------------------------------------------------

    data = file.file.read(MAX_SIZE + 1)

    if len(data) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large (>8MB)",
        )

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

    rep.synced_at = dt.datetime.utcnow()

    db.commit()

    return {
        "id": report_id,
        "synced": True,
    }