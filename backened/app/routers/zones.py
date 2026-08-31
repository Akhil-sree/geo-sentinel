from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ZoneOut
from app.models_db import Zone, LandslideEvent

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneOut])
def list_zones(db: Session = Depends(get_db)):
    return [ZoneOut(id=z.id, name=z.name, district=z.district, lat=z.lat, lng=z.lng,
                    slope=z.slope, elevation=z.elevation, population=z.population,
                    sar_acquisition_date=z.sar_acquisition_date,
                    sar_change_score=z.sar_change_score)
            for z in db.query(Zone).all()]


@router.get("/landslides")
def list_landslides(db: Session = Depends(get_db)):
    return [{"zone_id": e.zone_id, "event_date": e.event_date, "type": e.type,
             "trigger": e.trigger, "source": e.source}
            for e in db.query(LandslideEvent).all()]
