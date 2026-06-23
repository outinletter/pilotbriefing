from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from .database import Base


class FlightQuery(Base):
    __tablename__ = "flight_queries"
    id = Column(Integer, primary_key=True)
    flight_number = Column(String, nullable=False)
    airline_iata = Column(String)
    flight_iata = Column(String)
    departure_iata = Column(String)
    arrival_iata = Column(String)
    departure_icao = Column(String)
    arrival_icao = Column(String)
    scheduled_departure = Column(String)
    scheduled_arrival = Column(String)
    estimated_departure = Column(String)
    estimated_arrival = Column(String)
    aircraft_type = Column(String)
    raw_response_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class WeatherReport(Base):
    __tablename__ = "weather_reports"
    id = Column(Integer, primary_key=True)
    airport_icao = Column(String, nullable=False)
    report_type = Column(String, nullable=False)
    report_time = Column(String)
    raw_text = Column(Text)
    parsed_json = Column(Text)
    risk_tags = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True)
    source_name = Column(String)
    source_url = Column(String)
    event_date = Column(String)
    published_date = Column(String)
    operation_type = Column(String)
    airport_iata = Column(String)
    airport_icao = Column(String)
    runway = Column(String)
    approach_type = Column(String)
    flight_phase = Column(String)
    aircraft_type = Column(String)
    aircraft_category = Column(String)
    operator = Column(String)
    weather_summary = Column(String)
    metar_text = Column(Text)
    visibility = Column(String)
    wind = Column(String)
    runway_condition = Column(String)
    event_type = Column(String)
    severity = Column(Integer, default=1)
    core_event = Column(String)
    lesson_keyword = Column(String)
    summary = Column(Text)
    contributing_factors = Column(Text)
    operational_lessons = Column(Text)
    pilot_briefing_sentence = Column(Text)
    confidence_score = Column(Float, default=0.8)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EventTag(Base):
    __tablename__ = "event_tags"
    id = Column(Integer, primary_key=True)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    tag_type = Column(String)
    tag_value = Column(String)


class OpsIntelRun(Base):
    __tablename__ = "ops_intel_runs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String, default="running")
    items_checked = Column(Integer, default=0)
    items_saved = Column(Integer, default=0)
    error = Column(Text)


class OpsIntelItem(Base):
    __tablename__ = "ops_intel_items"
    id = Column(Integer, primary_key=True)
    source_name = Column(String, nullable=False)
    source_url = Column(String, nullable=False, unique=True)
    title = Column(String)
    operation_type = Column(String, default="Part 121 / Part 135")
    category = Column(String)
    severity = Column(String, default="Low")
    summary = Column(Text)
    operational_lesson = Column(Text)
    a350_b787_applicability = Column(Text)
    recommended_action = Column(Text)
    tags = Column(Text)
    last_status = Column(Integer)
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
