# app/ingest/base.py
"""Ingestion adapter contract.

Every source adapter must implement: fetch → validate → normalize →
transform → store → log → retry. Retries use exponential backoff;
after MAX_RETRIES the source is marked STALE (visible in /admin/data),
never silently dropped or filled with synthetic values.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time

MAX_RETRIES = 3
BACKOFF_S = [2, 8, 30]


class IngestionAdapter(ABC):
    source_name: str

    @abstractmethod
    def fetch(self) -> list[dict]: ...
    """Raw records from provider. Must return [] on clean empty, raise on error."""

    def run(self, db) -> dict:
        attempt = 0
        while True:
            try:
                raw = self.fetch()
                records = [self.normalize(r) for r in self.validate(raw)]
                self.store(db, records)
                status = "OK" if records else "EMPTY"
                self.log(db, status, f"{len(records)} records")
                return {"source": self.source_name, "status": status}
            except Exception as e:
                if attempt >= MAX_RETRIES:
                    self.log(db, "STALE", f"failed after {MAX_RETRIES} retries: {e}")
                    return {"source": self.source_name, "status": "STALE", "detail": str(e)}
                time.sleep(BACKOFF_S[attempt])
                attempt += 1

    def validate(self, raw: list[dict]) -> list[dict]:
        """Subclasses override: drop rows failing range/null checks."""
        return raw

    def normalize(self, r: dict) -> dict:
        """Subclasses override: provider field names → canonical schema."""
        return r

    def store(self, db, records: list[dict]) -> None: ...

    def log(self, db, status: str, detail: str) -> None:
        from app.models_db import IngestionLog
        db.add(IngestionLog(source=self.source_name, status=status, detail=detail,
                            at=datetime.now(timezone.utc)))
        db.commit()
