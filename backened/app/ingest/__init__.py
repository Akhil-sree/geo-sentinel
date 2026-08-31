"""Ingestion layer.

base.py     — IngestionAdapter contract (fetch→validate→normalize→store→log→retry)
runner.py   — runs all registered adapters, persists features, returns freshness
scheduler.py— periodic loop wrapper (background thread in demo; Celery in prod)
"""
from app.ingest.base import IngestionAdapter, MAX_RETRIES, BACKOFF_S
from app.ingest.runner import run_ingestion, get_freshness_snapshot

__all__ = ["IngestionAdapter", "MAX_RETRIES", "BACKOFF_S",
           "run_ingestion", "get_freshness_snapshot"]
