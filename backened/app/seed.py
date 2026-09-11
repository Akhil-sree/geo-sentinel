"""
Seeds the Meghalaya demo dataset.

Creates:
    - 8 demo zones
    - Demo recipients
    - Historical landslide inventory
    - Audit log

If no trained RF artifact exists, trains a real scikit-learn
Random Forest model from the seeded zone feature set.

All demo recipients and synthetic data are clearly labeled.
"""

import datetime as dt
import os


ZONES = [
    {
        "id": "Z1",
        "name": "Sohra (Cherrapunji)",
        "district": "East Khasi Hills",
        "lat": 25.30,
        "lng": 91.70,
        "slope": 38,
        "elevation": 1484,
        "ruggedness": 0.85,
        "road_proximity": 0.72,
        "drainage_proximity": 0.80,
        "settlement_density": 0.62,
        "population": 11800,
        "sar_change_score": 0.21,
        "label": 2,
    },
    {
        "id": "Z2",
        "name": "Mawsynram",
        "district": "East Khasi Hills",
        "lat": 25.30,
        "lng": 91.58,
        "slope": 34,
        "elevation": 1380,
        "ruggedness": 0.78,
        "road_proximity": 0.60,
        "drainage_proximity": 0.72,
        "settlement_density": 0.30,
        "population": 4000,
        "sar_change_score": 0.15,
        "label": 2,
    },
    {
        "id": "Z3",
        "name": "Shillong North Slopes",
        "district": "East Khasi Hills",
        "lat": 25.62,
        "lng": 91.90,
        "slope": 24,
        "elevation": 1496,
        "ruggedness": 0.55,
        "road_proximity": 0.85,
        "drainage_proximity": 0.55,
        "settlement_density": 0.90,
        "population": 145000,
        "sar_change_score": 0.30,
        "label": 2,
    },
    {
        "id": "Z4",
        "name": "Nongstoin Ridge",
        "district": "West Khasi Hills",
        "lat": 25.52,
        "lng": 91.27,
        "slope": 29,
        "elevation": 1409,
        "ruggedness": 0.70,
        "road_proximity": 0.50,
        "drainage_proximity": 0.65,
        "settlement_density": 0.40,
        "population": 8200,
        "sar_change_score": 0.11,
        "label": 1,
    },
    {
        "id": "Z5",
        "name": "Tura Hills",
        "district": "West Garo Hills",
        "lat": 25.51,
        "lng": 90.20,
        "slope": 31,
        "elevation": 640,
        "ruggedness": 0.76,
        "road_proximity": 0.68,
        "drainage_proximity": 0.58,
        "settlement_density": 0.72,
        "population": 74000,
        "sar_change_score": 0.25,
        "label": 2,
    },
    {
        "id": "Z6",
        "name": "Williamnagar Valley",
        "district": "East Garo Hills",
        "lat": 25.60,
        "lng": 90.46,
        "slope": 18,
        "elevation": 240,
        "ruggedness": 0.42,
        "road_proximity": 0.62,
        "drainage_proximity": 0.85,
        "settlement_density": 0.55,
        "population": 18000,
        "sar_change_score": 0.08,
        "label": 0,
    },
    {
        "id": "Z7",
        "name": "Jowai Plateau Edge",
        "district": "West Jaintia Hills",
        "lat": 25.45,
        "lng": 92.20,
        "slope": 27,
        "elevation": 1220,
        "ruggedness": 0.66,
        "road_proximity": 0.58,
        "drainage_proximity": 0.68,
        "settlement_density": 0.45,
        "population": 15000,
        "sar_change_score": 0.18,
        "label": 1,
    },
    {
        "id": "Z8",
        "name": "Baghmara Foothills",
        "district": "South Garo Hills",
        "lat": 25.39,
        "lng": 90.63,
        "slope": 22,
        "elevation": 310,
        "ruggedness": 0.50,
        "road_proximity": 0.40,
        "drainage_proximity": 0.60,
        "settlement_density": 0.35,
        "population": 5100,
        "sar_change_score": 0.06,
        "label": 0,
    },
]


EVENTS = [
    ("Z1", "2024-07-10", "Debris flow"),
    ("Z1", "2023-06-15", "Slide"),
    ("Z2", "2024-06-30", "Slide"),
    ("Z3", "2022-09-12", "Rockfall"),
    ("Z3", "2023-08-02", "Slide"),
    ("Z4", "2024-07-19", "Debris flow"),
    ("Z5", "2023-05-20", "Slide"),
    ("Z5", "2024-06-18", "Debris flow"),
    ("Z7", "2023-07-28", "Debris flow"),
    ("Z8", "2022-06-14", "Creep"),
]


ROAD_SEGMENTS = [
    ("Z1", "Z3", "Shillong-Sohra Road", "district", 52, "OPEN", None, 25.31, 91.80),
    ("Z1", "Z2", "Sohra-Mawsynram Link", "village", 18, "BLOCKED", "landslide", 25.30, 91.64),
    ("Z3", "Z7", "Shillong-Jowai Highway", "national", 64, "OPEN", None, 25.53, 92.05),
    ("Z4", "Z3", "Nongstoin-Shillong Road", "state", 85, "DAMAGED", "slope_failure", 25.57, 91.58),
    ("Z5", "Z8", "Tura-Baghmara Road", "state", 72, "UNDER_REPAIR", "flood", 25.45, 90.42),
    ("Z5", "Z6", "Tura-Williamnagar NH", "national", 95, "OPEN", None, 25.55, 90.33),
    ("Z7", "Z1", "Jowai-Sohra Alternative", "district", 48, "BLOCKED", "landslide", 25.38, 91.95),
    ("Z6", "Z8", "Williamnagar-Baghmara", "district", 38, "OPEN", None, 25.50, 90.55),
]

EMERGENCY_TASKS = [
    ("Z1", "road_clear", "Clear Sohra-Mawsynram Link", "Landslide blocking main access road to Mawsynram village", "CRITICAL", "IN_PROGRESS", "NDRF Team Alpha", "4 hours"),
    ("Z2", "evacuation", "Evacuate Mawsynram Low-Lying Areas", "Rising water levels threatening 3 hamlets near drainage basin", "CRITICAL", "PENDING", "SDRF Team B", "2 hours"),
    ("Z4", "road_clear", "Repair Nongstoin-Shillong Road Section", "Slope failure at km 42 blocking state highway", "HIGH", "IN_PROGRESS", "PWD Road Division", "12 hours"),
    ("Z5", "patrol", "Patrol Tura Hills Vulnerable Slopes", "Monitor cracking pattern reported by village council", "HIGH", "PENDING", "GEO Team Tura", "6 hours"),
    ("Z7", "supply", "Emergency Supply Drop to Jowai Plateau", "Village isolated due to road blockage — food and medicine needed", "HIGH", "PENDING", "District Admin Jaintia", "8 hours"),
    ("Z3", "shelter_setup", "Open Shillong North Relief Camp", "Pre-emptive shelter activation for degraded slope zone residents", "MEDIUM", "COMPLETED", "DDMA Shillong", "—"),
    ("Z8", "patrol", "Monitor Baghmara Foothill Drainage", "Check drainage capacity after overnight rainfall", "LOW", "PENDING", "Block Office Baghmara", "3 hours"),
    ("Z6", "supply", "Restock Williamnagar Medical Supplies", "Ensure health center is stocked before forecasted heavy rain", "LOW", "COMPLETED", "District Health Office", "—"),
]

RECIPIENTS = [
    (
        "+91-98xxx-DEMO1",
        "en",
        "Z1",
        "Block Officer — Sohra",
    ),
    (
        "+91-98xxx-DEMO2",
        "hi",
        "Z1",
        "Village Council — Laitryng",
    ),
    (
        "+91-98xxx-DEMO3",
        "en",
        "Z3",
        "DDMA Duty Officer",
    ),
    (
        "+91-98xxx-DEMO4",
        "en",
        "Z5",
        "Tura Control Room",
    ),
]


def seed(db):
    """
    Seed the database and train the RF model if necessary.
    """

    from .models_db import (
        Zone,
        LandslideEvent,
        Recipient,
        AuditLog,
        RoadSegment,
        EmergencyTask,
    )

    from .ml.rf_model import (
        train,
        MODEL_DIR,
        VERSION,
    )

    # ---------------------------------------------------------
    # Seed database
    # ---------------------------------------------------------

    if db.query(Zone).count() == 0:

        # -----------------------------------------------------
        # Zones
        # -----------------------------------------------------

        for zone_data in ZONES:

            zone = {
                key: value
                for key, value in zone_data.items()
                if key not in ("label", "lat", "lng")
            }
            zone["latitude"] = zone_data["lat"]
            zone["longitude"] = zone_data["lng"]

            db.add(
                Zone(**zone)
            )

        # -----------------------------------------------------
        # Historical landslide events
        # -----------------------------------------------------

        for zone_id, event_date, event_type in EVENTS:

            db.add(
                LandslideEvent(
                    zone_id=zone_id,
                    event_date=dt.datetime.fromisoformat(
                        event_date
                    ),
                    landslide_type=event_type,
                    source="SI/NRSC_DEMO inventory",
                )
            )

        # -----------------------------------------------------
        # Demo recipients
        # -----------------------------------------------------

        for phone, language, zone_id, name in RECIPIENTS:

            db.add(
                Recipient(
                    phone_number=phone,
                    preferred_language=language,
                    zone_id=zone_id,
                    name=name,
                    active=True,
                )
            )

        # -----------------------------------------------------
        # Road segments
        # -----------------------------------------------------

        for from_z, to_z, name, rtype, length, status, reason, lat, lng in ROAD_SEGMENTS:

            db.add(
                RoadSegment(
                    from_zone=from_z,
                    to_zone=to_z,
                    name=name,
                    road_type=rtype,
                    length_km=length,
                    status=status,
                    blockage_reason=reason,
                    latitude=lat,
                    longitude=lng,
                )
            )

        # -----------------------------------------------------
        # Emergency tasks
        # -----------------------------------------------------

        for zone_id, ttype, title, desc, priority, status, team, eta in EMERGENCY_TASKS:

            db.add(
                EmergencyTask(
                    zone_id=zone_id,
                    task_type=ttype,
                    title=title,
                    description=desc,
                    priority=priority,
                    status=status,
                    assigned_team=team,
                    estimated_time=eta,
                )
            )

        # -----------------------------------------------------
        # Audit log
        # -----------------------------------------------------

        db.add(
            AuditLog(
                action="SEED_DEMO",
                detail=(
                    "Meghalaya demo dataset — "
                    "synthetic demonstration data; "
                    "demo recipients."
                ),
            )
        )

        db.commit()

    # ---------------------------------------------------------
    # Train RF model if artifact doesn't exist
    # ---------------------------------------------------------

    model_path = os.path.join(
        MODEL_DIR,
        VERSION,
        "model.joblib",
    )

    if not os.path.exists(model_path):

        zones = (
            db.query(Zone)
            .all()
        )

        zone_labels = {
            item["id"]: item["label"]
            for item in ZONES
        }

        labels = [
            zone_labels[zone.id]
            for zone in zones
        ]

        train(
            zones,
            labels,
            version=VERSION,
        )