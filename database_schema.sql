CREATE TABLE IF NOT EXISTS flight_queries (
  id INTEGER PRIMARY KEY,
  flight_number TEXT NOT NULL,
  airline_iata TEXT,
  flight_iata TEXT,
  departure_iata TEXT,
  arrival_iata TEXT,
  departure_icao TEXT,
  arrival_icao TEXT,
  scheduled_departure TEXT,
  scheduled_arrival TEXT,
  estimated_departure TEXT,
  estimated_arrival TEXT,
  aircraft_type TEXT,
  raw_response_json TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weather_reports (
  id INTEGER PRIMARY KEY,
  airport_icao TEXT NOT NULL,
  report_type TEXT NOT NULL,
  report_time TEXT,
  raw_text TEXT,
  parsed_json TEXT,
  risk_tags TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  source_name TEXT,
  source_url TEXT,
  event_date TEXT,
  published_date TEXT,
  operation_type TEXT,
  airport_iata TEXT,
  airport_icao TEXT,
  runway TEXT,
  approach_type TEXT,
  flight_phase TEXT,
  aircraft_type TEXT,
  aircraft_category TEXT,
  operator TEXT,
  weather_summary TEXT,
  metar_text TEXT,
  visibility TEXT,
  wind TEXT,
  runway_condition TEXT,
  event_type TEXT,
  severity INTEGER,
  core_event TEXT,
  lesson_keyword TEXT,
  summary TEXT,
  contributing_factors TEXT,
  operational_lessons TEXT,
  pilot_briefing_sentence TEXT,
  confidence_score REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_tags (
  id INTEGER PRIMARY KEY,
  event_id TEXT NOT NULL,
  tag_type TEXT,
  tag_value TEXT,
  FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS ops_intel_runs (
  id INTEGER PRIMARY KEY,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP,
  status TEXT DEFAULT 'running',
  items_checked INTEGER DEFAULT 0,
  items_saved INTEGER DEFAULT 0,
  error TEXT
);

CREATE TABLE IF NOT EXISTS ops_intel_items (
  id INTEGER PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL UNIQUE,
  title TEXT,
  operation_type TEXT DEFAULT 'Part 121 / Part 135',
  category TEXT,
  severity TEXT DEFAULT 'Low',
  summary TEXT,
  operational_lesson TEXT,
  a350_b787_applicability TEXT,
  recommended_action TEXT,
  tags TEXT,
  last_status INTEGER,
  last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
