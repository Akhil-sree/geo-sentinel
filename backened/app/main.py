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
from app.api import risk, reports, alerts, admin
from app.config import MEDIA_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    yield

app = FastAPI(title="GEO-SENTINEL", version="0.1.0",
              description="AI landslide early warning — zone-level advisory, decision support only.",
              lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

app.include_router(risk.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
