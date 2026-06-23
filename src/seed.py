import json

from .config import BASE_DIR
from .database import Base, SessionLocal, engine
from .models import Event, EventTag


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        with open(BASE_DIR / "sample_events.json", encoding="utf-8") as f:
            events = json.load(f)
        for item in events:
            tags = item.pop("tags", [])
            existing = db.get(Event, item["id"])
            payload = item.copy()
            payload["contributing_factors"] = json.dumps(payload.get("contributing_factors", []))
            payload["operational_lessons"] = json.dumps(payload.get("operational_lessons", []))
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                db.query(EventTag).filter(EventTag.event_id == existing.id).delete()
                event_id = existing.id
            else:
                db.add(Event(**payload))
                event_id = payload["id"]
            for tag in tags:
                db.add(EventTag(event_id=event_id, tag_type="risk", tag_value=tag))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()

