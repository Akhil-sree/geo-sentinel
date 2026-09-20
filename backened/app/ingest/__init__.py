"""Ingestion layer.

base.py     — IngestionAdapter contract (fetch→validate→normalize→store→log→retry)
runner.py   — runs all registered adapters, persists features, returns freshness
scheduler.py— periodic loop wrapper (background thread in demo; Celery in prod)

NOTE: no eager imports here — runner imports providers which import
app.ingest.base, so eager re-exports create a circular import.
Import from app.ingest.runner / app.ingest.base directly.
"""
