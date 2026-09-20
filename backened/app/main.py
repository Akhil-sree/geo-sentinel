"""FastAPI entry point. On first boot: create tables → seed DB → train RF
(skipped if a versioned artifact already exists)."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.models_db import *  # noqa: F401,F403 — ensure all tables registered
from app.seed import seed
from app.api import risk, reports, alerts, admin, dashboard, routes, vision, status
from app.api import gs as gs_api
from app.api import sensors as sensors_api
from app.api import satellite as satellite_api
from app.api import datasets as datasets_api
from app.api import roads_gis as roads_gis_api
from app.api import rescue as rescue_api
from app.config import MEDIA_DIR
import app.config as _cfg
from app.observability import setup_json_logging

setup_json_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging as _log
    from app.database import DB_BACKEND, RESOLVED_DATABASE_URL
    _log.getLogger("geo-sentinel").warning(
        "database backend=%s url=%s "
        "(sqlite=demo/local, postgresql=production)",
        DB_BACKEND, RESOLVED_DATABASE_URL)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
        from app.ml.rf_model import MODEL_DIR, VERSION
        import os
        if not os.path.exists(os.path.join(MODEL_DIR, VERSION, "model.joblib")):
            from app.ml.train_rf import main
            main()
    finally:
        db.close()
    # Initialize rate limit store (Redis if configured, else in-memory)
    from app.auth import init_rate_limit_store
    init_rate_limit_store()
    yield

app = FastAPI(title="GEO-SENTINEL", version="0.1.0",
              description="AI landslide early warning — zone-level advisory, decision support only.",
              lifespan=lifespan)

def _cors_origins() -> list[str]:
    """Environment-based CORS. Development/demo may use `*`; production
    MUST set CORS_ORIGINS explicitly — fail closed (no origins) otherwise."""
    if _cfg.CORS_ORIGINS == "*":
        if _cfg.ENVIRONMENT == "production":
            import logging as _log
            _log.getLogger("geo-sentinel").error(
                "CORS_ORIGINS=* is forbidden in production — "
                "serving with no allowed origins; set CORS_ORIGINS")
            return []
        return ["*"]
    return [o.strip() for o in _cfg.CORS_ORIGINS.split(",") if o.strip()]


app.add_middleware(CORSMiddleware,
                   allow_origins=_cors_origins(),
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request, call_next):
    """Baseline hardening headers (Phase 16). CORS stays demo-open (`*`)
    unless CORS_ORIGINS is set — documented, not hidden."""
    import logging as _log
    import time as _t
    import uuid as _u
    rid = request.headers.get("X-Request-ID", _u.uuid4().hex[:12])
    t0 = _t.perf_counter()
    resp = await call_next(request)
    latency_ms = round((_t.perf_counter() - t0) * 1000, 1)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    resp.headers["X-Request-ID"] = rid  # Phase 33: traceable requests
    resp.headers["X-Process-Time-ms"] = f"{latency_ms:.1f}"
    try:
        from app.observability import record_request
        record_request(request.url.path, resp.status_code, latency_ms)
        _log.getLogger("geo-sentinel").info(
            "%s %s -> %s (%sms)",
            request.method, request.url.path, resp.status_code, latency_ms,
            extra={"request_id": rid, "method": request.method,
                   "path": request.url.path, "status": resp.status_code,
                   "latency_ms": latency_ms})
    except Exception as e:
        _log.getLogger("geo-sentinel").debug("Observability recording failed: %s", e)
    return resp


app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

app.include_router(status.router, prefix="/api")

app.include_router(risk.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(vision.router, prefix="/api")
app.include_router(sensors_api.router, prefix="/api")
app.include_router(satellite_api.router, prefix="/api")
app.include_router(datasets_api.router, prefix="/api")
app.include_router(gs_api.router, prefix="/api")
app.include_router(roads_gis_api.router, prefix="/api")
app.include_router(rescue_api.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
