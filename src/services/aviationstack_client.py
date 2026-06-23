import httpx

from ..config import settings

LOCAL_ROUTES = {
    "KE053": {"departure_iata": "ICN", "arrival_iata": "HNL", "aircraft_type": "B787-10"},
    "KE53": {"departure_iata": "ICN", "arrival_iata": "HNL", "aircraft_type": "B787-10"},
    "KE054": {"departure_iata": "HNL", "arrival_iata": "ICN", "aircraft_type": "B787-10"},
    "KE54": {"departure_iata": "HNL", "arrival_iata": "ICN", "aircraft_type": "B787-10"},
    "KE629": {"departure_iata": "ICN", "arrival_iata": "DPS", "aircraft_type": "A350-900", "scheduled_arrival": "2026-06-22T15:00:00+00:00"},
    "KE630": {"departure_iata": "DPS", "arrival_iata": "ICN", "aircraft_type": "A350-900", "scheduled_arrival": "2026-06-22T23:00:00+00:00"},
    "KE017": {"departure_iata": "ICN", "arrival_iata": "LAX", "aircraft_type": "B777-300ER", "scheduled_arrival": "2026-06-22T18:00:00+00:00"},
    "KE018": {"departure_iata": "LAX", "arrival_iata": "ICN", "aircraft_type": "B777-300ER", "scheduled_arrival": "2026-06-22T21:00:00+00:00"},
    "KE705": {"departure_iata": "ICN", "arrival_iata": "NRT", "aircraft_type": "A330-300", "scheduled_arrival": "2026-06-22T05:00:00+00:00"},
    "KE706": {"departure_iata": "NRT", "arrival_iata": "ICN", "aircraft_type": "A330-300", "scheduled_arrival": "2026-06-22T10:00:00+00:00"},
}


def flight_query_candidates(flight_number: str) -> list[str]:
    if len(flight_number) >= 4 and flight_number[2:].isdigit():
        return list(dict.fromkeys([flight_number, f"{flight_number[:2]}{int(flight_number[2:])}"]))
    return [flight_number]


def local_route_for(flight_number: str) -> dict | None:
    for query in flight_query_candidates(flight_number):
        route = LOCAL_ROUTES.get(query)
        if route:
            return route.copy()
    return None


def flight_from_api_item(flight_number: str, item: dict) -> dict:
    return {
        "flight_number": flight_number,
        "airline_iata": (item.get("airline") or {}).get("iata"),
        "flight_iata": (item.get("flight") or {}).get("iata"),
        "departure_iata": (item.get("departure") or {}).get("iata"),
        "arrival_iata": (item.get("arrival") or {}).get("iata"),
        "scheduled_departure": (item.get("departure") or {}).get("scheduled"),
        "scheduled_arrival": (item.get("arrival") or {}).get("scheduled"),
        "estimated_departure": (item.get("departure") or {}).get("estimated"),
        "estimated_arrival": (item.get("arrival") or {}).get("estimated"),
        "aircraft_type": (item.get("aircraft") or {}).get("iata"),
        "raw": item,
    }


async def aviationstack_lookup(flight_number: str) -> dict | None:
    if not settings.aviationstack_api_key:
        return None
    async with httpx.AsyncClient(timeout=8) as client:
        for query in flight_query_candidates(flight_number):
            params = {"access_key": settings.aviationstack_api_key, "flight_iata": query}
            response = await client.get("http://api.aviationstack.com/v1/flights", params=params)
            response.raise_for_status()
            data = response.json().get("data") or []
            if data:
                return flight_from_api_item(flight_number, data[0])
    return None


async def get_flight(flight_number: str) -> tuple[dict, str | None]:
    flight_number = flight_number.upper().strip()
    local = local_route_for(flight_number)
    fallback_message = None if local else "Flight API unavailable; using local route database."
    api_flight = None
    try:
        api_flight = await aviationstack_lookup(flight_number)
    except Exception:
        fallback_message = None if local else "Flight API unavailable; using local route database."

    if local:
        raw = {"source": "internal_route_database", **local}
        if api_flight:
            raw = api_flight.get("raw", raw)
            local["aircraft_type"] = api_flight.get("aircraft_type") or local.get("aircraft_type")
            for key in ["scheduled_departure", "scheduled_arrival", "estimated_departure", "estimated_arrival"]:
                local[key] = api_flight.get(key)
        local.update({"flight_number": flight_number, "airline_iata": flight_number[:2], "flight_iata": (api_flight or {}).get("flight_iata") or flight_number, "raw": raw})
        return local, None

    if api_flight:
        return api_flight, None

    local = LOCAL_ROUTES["KE629"].copy()
    raw = {"source": "default_demo_route", **local}
    local.update({"flight_number": flight_number, "airline_iata": flight_number[:2], "flight_iata": flight_number, "raw": raw})
    return local, fallback_message
