"""Cadence wrapper.

DEMO: ingestion runs on-demand (risk router calls run_ingestion when the
scrubber moves). This scheduler exists for production/long-running demo:
a daemon thread re-ingests every INGEST_INTERVAL_MIN minutes.

PRODUCTION: replace thread with Celery beat + dedicated workers so a slow
provider never blocks the API process. The runner contract stays identical.
"""
import os
import threading
import time
import logging

from app.ingest.runner import run_ingestion
from app.database import SessionLocal

log = logging.getLogger("ingest.scheduler")
INTERVAL_MIN = float(os.getenv("INGEST_INTERVAL_MIN", "30"))
_started = False
_lock = threading.Lock()


def _loop():
    while True:
        db = SessionLocal()
        try:
            summary = run_ingestion(db)
            log.info("ingestion run: %s", summary)
        except Exception:
            log.exception("ingestion run failed — will retry next interval")
        finally:
            db.close()
        time.sleep(INTERVAL_MIN * 60)


def start_scheduler() -> None:
    """Idempotent — called from app lifespan when SCHEDULER_ENABLED=true."""
    global _started
    with _lock:
        if _started or os.getenv("SCHEDULER_ENABLED", "false").lower() != "true":
            return
        t = threading.Thread(target=_loop, name="ingest-scheduler", daemon=True)
        t.start()
        _started = True
        log.info("ingestion scheduler started (every %s min)", INTERVAL_MIN)
