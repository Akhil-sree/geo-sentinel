"""Standalone RF training entry point."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models_db import Zone
from app.ml.rf_model import train, MODEL_DIR, VERSION
from app.seed import ZONES

def main():
    db = SessionLocal()
    zones = db.query(Zone).all()
    if not zones:
        raise RuntimeError("no zones — run seed() first (app startup does this)")
    labels = [next(z["label"] for z in ZONES if z["id"] == zz.id) for zz in zones]
    meta = train(zones, labels, version=VERSION)
    db.close()
    print("trained →", os.path.join(MODEL_DIR, VERSION), "| cv_accuracy =", meta["cv_accuracy"])
    return meta

if __name__ == "__main__":
    main()
