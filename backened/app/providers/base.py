"""
Provider adapter contract.

Every external source implements:
    fetch()
    validate()
    normalize()
    transform()
    store()

Failures never crash the system.
They degrade gracefully and are logged as FAILED/STALE.
"""

import time
import logging

import httpx

from ..database import SessionLocal
from ..models_db import IngestionRun


log = logging.getLogger("ingestion")


class BaseProvider:
    """
    Base adapter for external data providers.
    """

    name = "base"

    def fetch(self):
        raise NotImplementedError

    def validate(self, raw):
        raise NotImplementedError

    def normalize(self, raw):
        raise NotImplementedError

    def transform(self, records):
        return records

    def store(self, records, db):
        raise NotImplementedError

    def run(
        self,
        retries: int = 3,
        backoff: float = 2.0,
    ):
        """
        Execute the provider ingestion pipeline.

        Pipeline:
            fetch
              ↓
            validate
              ↓
            normalize
              ↓
            transform
              ↓
            store
              ↓
            log

        Failed attempts are retried using exponential backoff.
        """

        db = SessionLocal()

        try:

            for attempt in range(retries):

                try:
                    # -------------------------------------------------
                    # 1. Fetch
                    # -------------------------------------------------

                    raw = self.fetch()

                    # -------------------------------------------------
                    # 2. Validate
                    # -------------------------------------------------

                    if not self.validate(raw):
                        raise ValueError(
                            "Provider validation failed"
                        )

                    # -------------------------------------------------
                    # 3. Normalize
                    # -------------------------------------------------

                    records = self.normalize(raw)

                    # -------------------------------------------------
                    # 4. Transform
                    # -------------------------------------------------

                    records = self.transform(records)

                    # -------------------------------------------------
                    # 5. Store
                    # -------------------------------------------------

                    self.store(
                        records,
                        db,
                    )

                    # -------------------------------------------------
                    # 6. Log successful ingestion
                    # -------------------------------------------------

                    db.add(
                        IngestionRun(
                            source=self.name,
                            status="OK",
                            detail=f"{len(records)} records",
                        )
                    )

                    db.commit()

                    log.info(
                        "%s ingestion successful: %d records",
                        self.name,
                        len(records),
                    )

                    return True

                except Exception as e:

                    # Roll back any failed DB transaction
                    # before retrying.
                    db.rollback()

                    wait = backoff ** attempt

                    log.warning(
                        "%s attempt %d/%d failed: %s "
                        "— retry in %.1fs",
                        self.name,
                        attempt + 1,
                        retries,
                        e,
                        wait,
                    )

                    # Don't sleep after the final attempt
                    if attempt < retries - 1:
                        time.sleep(wait)

            # ---------------------------------------------------------
            # All retries exhausted
            # ---------------------------------------------------------

            detail = (
                "All retries exhausted — "
                "using last known good data, "
                "marked STALE"
            )

            db.add(
                IngestionRun(
                    source=self.name,
                    status="STALE",
                    detail=detail,
                )
            )

            db.commit()

            log.error(
                "%s ingestion failed after %d attempts. "
                "Using last known good data.",
                self.name,
                retries,
            )

            return False

        except Exception as e:

            # Protect the whole ingestion system from an
            # unexpected database/logging failure.
            db.rollback()

            log.exception(
                "%s ingestion pipeline failed unexpectedly: %s",
                self.name,
                e,
            )

            return False

        finally:
            db.close()


class HTTPMixin:
    """
    Shared HTTP client for real external providers.

    Provides:
        _get(url)

    with timeout and HTTP status checking.
    """

    @staticmethod
    def _get(
        url,
        headers=None,
        timeout=15,
    ):
        """
        Perform an HTTP GET request.

        Raises httpx.HTTPStatusError if the server
        returns a non-success HTTP status.
        """

        with httpx.Client(
            timeout=timeout
        ) as client:

            response = client.get(
                url,
                headers=headers or {},
            )

            response.raise_for_status()

            return response