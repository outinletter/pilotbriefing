from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Event

router = APIRouter()


@router.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    return [{"id": e.id, "airport_icao": e.airport_icao, "event_type": e.event_type} for e in db.query(Event).all()]

