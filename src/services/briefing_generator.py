from collections import OrderedDict

from .risk_tagger import threat_for_tags
from .similarity_engine import event_tags, json_list, ranked_events


def event_title(event) -> str:
    year = (event.event_date or "0000")[:4]
    return f"{year} {event.airport_iata} {event.runway} {event.approach_type} {event.aircraft_type} | {event.weather_summary} | {event.core_event} - {event.lesson_keyword}"


def one_line(event, similarity: int) -> str:
    return f"{similarity}% | {event.runway or 'ROUTE'} | {event.weather_summary} | {event.approach_type} | {event.aircraft_type} | {event.event_type} | {event.lesson_keyword}".upper()


def severity_label(value: int | None) -> str:
    if (value or 0) >= 5:
        return "Critical"
    if (value or 0) >= 4:
        return "High"
    if (value or 0) >= 3:
        return "Medium"
    return "Low"


def event_category(event, tags: set[str]) -> str:
    categories = []
    if event.flight_phase in {"APPROACH", "LANDING"} or "UNSTABLE_APPROACH_RISK" in tags:
        categories.append("Accident / Incident")
    if event.flight_phase in {"CRUISE", "PREFLIGHT"} or event.approach_type in {"ENROUTE", "DISPATCH"}:
        categories.append("Flight Operations")
    if tags.intersection({"ETOPS", "GPS_INTEGRITY"}):
        categories.append("Flight Operations")
    if event.event_type and any(term in event.event_type for term in ["MEL", "ENGINE", "GPS"]):
        categories.append("Maintenance / Technical Reliability")
    return " / ".join(dict.fromkeys(categories)) or "Flight Operations"


def a350_b787_applicability(event) -> str:
    aircraft = event.aircraft_type or ""
    if "A350" in aircraft or "B787" in aircraft or "B78" in aircraft or "long-haul" in (event.operation_type or "").lower():
        return "Directly applicable to A350/B787 long-haul operations, especially during dispatch, approach briefing, and fatigue-aware threat management."
    return "Use as a comparable jet-operations lesson when briefing A350/B787 long-haul crews."


def recommended_action(event) -> str:
    phase = event.flight_phase or ""
    if phase in {"APPROACH", "LANDING"}:
        return "Include in arrival briefing, stable-approach gates, go-around decision review, and recurrent simulator scenarios."
    if phase == "CRUISE":
        return "Review dispatch release, ETOPS alternates, fuel decision points, and enroute contingency briefing."
    if phase == "PREFLIGHT":
        return "Review MEL/CDL, dispatch release limitations, and crew threat briefing before acceptance."
    return "Use for pilot briefing, SOP review, and training department trend monitoring."


def build_threats(db, context: dict, tags: list[str]) -> list[dict]:
    groups: OrderedDict[str, dict] = OrderedDict()
    for event, similarity in ranked_events(db, context, tags)[:18]:
        tags_for_event = event_tags(db, event.id)
        title, description = threat_for_tags(tags_for_event)
        if title not in groups:
            groups[title] = {"title": title, "description": description, "events": []}
        if len(groups[title]["events"]) < 4:
            groups[title]["events"].append({
                "id": event.id,
                "similarity": similarity,
                "one_line": one_line(event, similarity),
                "detail_title": event_title(event),
                "date": event.event_date or event.published_date or "",
                "source_name": event.source_name or "",
                "source_url": event.source_url or "",
                "operation_type": event.operation_type or "",
                "aircraft_type": event.aircraft_type or "",
                "operator": event.operator or "",
                "category": event_category(event, tags_for_event),
                "severity": severity_label(event.severity),
                "summary": event.summary or "",
                "contributing_factors": json_list(event.contributing_factors),
                "operational_lessons": json_list(event.operational_lessons),
                "a350_b787_applicability": a350_b787_applicability(event),
                "recommended_action": recommended_action(event),
                "pilot_briefing_sentence": event.pilot_briefing_sentence or "",
            })
        if len(groups) >= 5 and all(len(g["events"]) for g in groups.values()):
            break
    return list(groups.values())[:5]
