import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import SessionLocal
from src.models import Event, EventTag, OpsIntelItem
from src.services.airport_mapper import load_airports
from src.services.aviationstack_client import LOCAL_ROUTES
from src.services.noaa_weather_client import get_weather

OUT = ROOT / "docs" / "data"


def write_json(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def event_tags(db, event_id: str) -> list[str]:
    return [row.tag_value for row in db.query(EventTag).filter(EventTag.event_id == event_id).all()]


def route_payload() -> dict:
    airports = load_airports()
    routes = {}
    for flight, route in LOCAL_ROUTES.items():
        dep = route.get("departure_iata", "")
        arr = route.get("arrival_iata", "")
        routes[flight] = {
            **route,
            "departure_icao": airports.get(dep, dep),
            "arrival_icao": airports.get(arr, arr),
        }
    return {"generated_at": datetime.utcnow().isoformat() + "Z", "routes": routes, "airports": airports}


def events_payload(db) -> dict:
    rows = db.query(Event).all()
    events = []
    for row in rows:
        events.append({
            "id": row.id,
            "event_date": row.event_date,
            "published_date": row.published_date,
            "source_name": row.source_name,
            "source_url": row.source_url,
            "operation_type": row.operation_type,
            "airport_iata": row.airport_iata,
            "airport_icao": row.airport_icao,
            "runway": row.runway,
            "approach_type": row.approach_type,
            "flight_phase": row.flight_phase,
            "aircraft_type": row.aircraft_type,
            "aircraft_category": row.aircraft_category,
            "operator": row.operator,
            "weather_summary": row.weather_summary,
            "event_type": row.event_type,
            "severity": row.severity,
            "core_event": row.core_event,
            "lesson_keyword": row.lesson_keyword,
            "summary": row.summary,
            "contributing_factors": json.loads(row.contributing_factors or "[]"),
            "operational_lessons": json.loads(row.operational_lessons or "[]"),
            "pilot_briefing_sentence": row.pilot_briefing_sentence,
            "tags": event_tags(db, row.id),
        })
    return {"generated_at": datetime.utcnow().isoformat() + "Z", "events": events}


def ops_payload(db) -> dict:
    rows = db.query(OpsIntelItem).order_by(OpsIntelItem.updated_at.desc()).all()
    items = []
    for row in rows:
        items.append({
            "source_name": row.source_name,
            "source_url": row.source_url,
            "title": row.title,
            "operation_type": row.operation_type,
            "category": row.category,
            "severity": row.severity,
            "summary": row.summary,
            "operational_lesson": row.operational_lesson,
            "recommended_action": row.recommended_action,
            "tags": json.loads(row.tags or "[]"),
            "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
        })
    return {"generated_at": datetime.utcnow().isoformat() + "Z", "count": len(items), "items": items}


async def weather_payload(stations: list[str]) -> dict:
    payload = {"generated_at": datetime.utcnow().isoformat() + "Z", "stations": {}}
    for station in sorted(set(stations)):
        weather, messages = await get_weather(station)
        payload["stations"][station] = {
            "metar": weather.get("metar", ""),
            "taf": weather.get("taf", ""),
            "messages": messages,
        }
    return payload


async def main() -> None:
    db = SessionLocal()
    try:
        routes = route_payload()
        events = events_payload(db)
        ops = ops_payload(db)
        stations = ["RKSI", *[route["arrival_icao"] for route in routes["routes"].values()]]
        weather = await weather_payload(stations)
        write_json("routes.json", routes)
        write_json("events.json", events)
        write_json("ops_intel.json", ops)
        write_json("weather.json", weather)
        write_json("status.json", {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "events": len(events["events"]),
            "ops_intel_items": ops["count"],
            "weather_stations": len(weather["stations"]),
        })
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
