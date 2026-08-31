"""
Sentinel-1 SAR adapter.

SAR is PERIODIC (revisit approximately 6–12 days),
never continuous.

Acquisition metadata is preserved.

Missing SAR is NEVER treated as zero change.
The last acquisition remains explicitly flagged
with its acquisition date.
"""

import datetime as dt

from .base import BaseProvider


class MockSARProvider(BaseProvider):
    """
    Synthetic Sentinel-1 SAR provider.

    Produces a SAR change score together with
    acquisition metadata.
    """

    name = "SENTINEL1_MOCK"

    def __init__(
        self,
        zone_id: str,
        change_score: float,
    ):
        self.zone_id = zone_id
        self.change_score = float(change_score)

    def fetch(self):
        """
        Return mock Sentinel-1 acquisition metadata.
        """

        return {
            "orbit": "ASCENDING",
            "pol": "VV+VH",
        }

    def validate(self, raw):
        """
        Validate SAR acquisition metadata.
        """

        return (
            isinstance(raw, dict)
            and "orbit" in raw
            and "pol" in raw
        )

    def normalize(self, raw):
        """
        Convert SAR data into the common model schema.

        Important:
        Missing SAR is NOT represented as zero change.
        """

        acquisition_date = dt.datetime(
            2026,
            7,
            8,
        )

        previous_acquisition_date = dt.datetime(
            2026,
            6,
            30,
        )

        return {
            "sar_change_score": self.change_score,

            "sar_acquisition_date": (
                acquisition_date
                .date()
                .isoformat()
            ),

            "sar_previous_acquisition_date": (
                previous_acquisition_date
                .date()
                .isoformat()
            ),

            "polarization": raw["pol"],

            "orbit": raw["orbit"],

            "preprocessing": [
                "calibration",
                "speckle_filter",
                "terrain_correction",
                "co-registration",
            ],

            "quality_flag": (
                "DEMO_DATA — periodic acquisition, "
                "not live"
            ),
        }

    def transform(self, records):
        """
        Apply final transformations before storage.
        """

        records["sar_change_score"] = float(
            records["sar_change_score"]
        )

        return records

    def store(self, records, db):
        """
        Store SAR information on the corresponding Zone.
        """

        from ..models_db import Zone

        zone = db.get(
            Zone,
            self.zone_id,
        )

        if zone is None:
            raise ValueError(
                f"Zone '{self.zone_id}' "
                "does not exist."
            )

        for key, value in records.items():
            setattr(
                zone,
                key,
                value,
            )

        db.commit()