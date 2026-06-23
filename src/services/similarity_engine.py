import json


def event_tags(db, event_id: str) -> set[str]:
    from ..models import EventTag

    return {row.tag_value for row in db.query(EventTag).filter(EventTag.event_id == event_id).all()}


def score_event(event, context: dict, tags: list[str], db) -> int:
    score = 0
    tag_set = set(tags)
    e_tags = event_tags(db, event.id)
    if event.airport_icao == context["arrival_icao"]:
        score += 25
    if event.runway and event.runway == context.get("destination_runway"):
        score += 15
    if tag_set and e_tags:
        score += min(25, round(25 * len(tag_set.intersection(e_tags)) / max(1, len(tag_set))))
    if event.approach_type in {"VISUAL", "RNAV", "ILS"}:
        score += 10
    if event.aircraft_category == "JET":
        score += 10
    if event.flight_phase in {"APPROACH", "LANDING"}:
        score += 10
    if e_tags.intersection({"UNSTABLE_APPROACH_RISK", "CONVECTIVE_WEATHER", "WET_RWY"}):
        score += 5
    return min(score, 100)


def ranked_events(db, context: dict, tags: list[str]):
    from ..models import Event

    rows = db.query(Event).all()
    scored = []
    for event in rows:
        same_airport = event.airport_icao == context["arrival_icao"]
        route_event = event.flight_phase in {"CRUISE", "PREFLIGHT"} and event.aircraft_category == "JET"
        if not same_airport and not route_event:
            continue
        score = score_event(event, context, tags, db)
        if same_airport or score >= 35:
            scored.append((event, score))
    return sorted(
        scored,
        key=lambda item: (
            item[1],
            item[0].severity or 0,
            item[0].airport_icao == context["arrival_icao"],
            item[0].runway == context.get("destination_runway"),
        ),
        reverse=True,
    )


def json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []
