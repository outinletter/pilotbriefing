from typing import Any

from pydantic import BaseModel


class FlightContext(BaseModel):
    flight_number: str
    route: str
    aircraft: str | None = None
    departure_icao: str
    arrival_icao: str
    destination_runway: str | None = None
    weather: str
    risk_level: str
    messages: list[str] = []
    metar: str | None = None
    taf: str | None = None


class BriefingEvent(BaseModel):
    id: str
    similarity: int
    one_line: str
    detail_title: str
    summary: str
    contributing_factors: list[str]
    operational_lessons: list[str]
    pilot_briefing_sentence: str


class TopThreat(BaseModel):
    title: str
    description: str
    events: list[BriefingEvent]


class BriefingResponse(BaseModel):
    flight_context: FlightContext
    top_threats: list[TopThreat]

