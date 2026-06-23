import json
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FlightQuery
from ..services.airport_mapper import iata_to_icao
from ..services.aviationstack_client import get_flight
from ..services.briefing_generator import build_threats
from ..services.metar_taf_parser import parse_weather_tags, select_arrival_taf_segment
from ..services.noaa_weather_client import get_weather
from ..services.risk_tagger import risk_level

router = APIRouter()


def google_search_links(flight_number: str, route: str) -> list[dict[str, str]]:
    queries = [
        f"{flight_number} flight status",
        f"{flight_number} {route} today flight",
        f"{flight_number} arrival departure time",
    ]
    return [{"label": query, "url": f"https://www.google.com/search?q={quote_plus(query)}"} for query in queries]


@router.get("/api/briefing/{flight_number}")
async def briefing(flight_number: str, db: Session = Depends(get_db)):
    flight, flight_msg = await get_flight(flight_number)
    dep_icao = iata_to_icao(flight.get("departure_iata"))
    arr_icao = iata_to_icao(flight.get("arrival_iata"))
    weather, weather_messages = await get_weather(arr_icao)
    arrival_time = flight.get("estimated_arrival") or flight.get("scheduled_arrival")
    arrival_taf = select_arrival_taf_segment(weather.get("taf", ""), arrival_time)
    tags = parse_weather_tags(weather.get("metar", ""), arrival_taf)
    destination_runway = "RWY09" if arr_icao == "WADD" else None
    context = {
        "flight_number": flight_number.upper(),
        "route": f"{flight.get('departure_iata')}-{flight.get('arrival_iata')}",
        "aircraft": flight.get("aircraft_type") or "Unknown",
        "departure_icao": dep_icao,
        "arrival_icao": arr_icao,
        "destination_runway": destination_runway,
        "weather": "/".join(tags) or "ROUTE ONLY",
        "risk_level": risk_level(tags),
        "messages": [m for m in [flight_msg, *weather_messages] if m],
        "arrival_weather_time": arrival_time,
        "metar": weather.get("metar"),
        "taf": weather.get("taf"),
        "arrival_taf": arrival_taf,
    }
    if flight_msg:
        context["flight_search_links"] = google_search_links(context["flight_number"], context["route"])
    db.add(FlightQuery(
        flight_number=context["flight_number"],
        airline_iata=flight.get("airline_iata"),
        flight_iata=flight.get("flight_iata"),
        departure_iata=flight.get("departure_iata"),
        arrival_iata=flight.get("arrival_iata"),
        departure_icao=dep_icao,
        arrival_icao=arr_icao,
        scheduled_departure=flight.get("scheduled_departure"),
        scheduled_arrival=flight.get("scheduled_arrival"),
        estimated_departure=flight.get("estimated_departure"),
        estimated_arrival=flight.get("estimated_arrival"),
        aircraft_type=flight.get("aircraft_type"),
        raw_response_json=json.dumps(flight.get("raw", {})),
    ))
    db.commit()
    return {"flight_context": context, "top_threats": build_threats(db, context, tags)}


@router.get("/api/weather/{icao}")
async def station_weather(icao: str):
    station = icao.strip().upper()
    weather, messages = await get_weather(station)
    return {
        "station": station,
        "metar": weather.get("metar", ""),
        "taf": weather.get("taf", ""),
        "messages": messages,
    }
