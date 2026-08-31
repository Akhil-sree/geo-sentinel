"""Phone-to-zone directory.

DEMO: two mock opted-in recipients per zone, numbers masked downstream.
REAL DEPLOYMENT REQUIRES: an authorized, opted-in phone-to-zone directory
(agreed with the state SDMA) — this mock must never ship to production.
"""
import random

_MOCK = {}


def _build(names: list[str]) -> dict:
    d = {}
    for zone in names:
        d[zone] = [
            {"name": f"{zone.split('-')[1].title()} Resident A",
             "phone": f"+9198{random.randint(10000000, 99999999)}", "lang": "en"},
            {"name": f"{zone.split('-')[1].title()} Resident B",
             "phone": f"+9199{random.randint(10000000, 99999999)}", "lang": "hi"},
        ]
    return d


def get_directory() -> dict[str, list[dict]]:
    global _MOCK
    if not _MOCK:
        from app.providers.imd import ZONES
        _MOCK = {z: [{**r, "phone": f"+9198{abs(hash(r['name'])) % 100000000:08d}"}
                     for r in _recips(z)] for z in ZONES}
    return _MOCK


def _recips(zone: str) -> list[dict]:
    base = zone.split("-", 1)[1].title()
    return [{"name": f"{base} Recipient 1", "lang": "en"},
            {"name": f"{base} Recipient 2", "lang": "hi"}]
