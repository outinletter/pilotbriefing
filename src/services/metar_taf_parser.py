import re
from datetime import datetime, timezone


def parse_weather_tags(metar: str = "", taf: str = "") -> list[str]:
    text = f"{metar} {taf}".upper()
    tags = set()
    checks = {
        "TSRA": r"\bTSRA\b|\+TSRA",
        "CB": r"\bCB\b|CB",
        "GUST": r"G\d{2}KT",
        "WINDSHEAR": r"\bWS\b|WINDSHEAR",
        "FOG": r"\bFG\b|FOG",
        "HEAVY_RAIN": r"\+RA|\+TSRA",
        "THUNDERSTORM": r"\bTS\b|TSRA",
    }
    for tag, pattern in checks.items():
        if re.search(pattern, text):
            tags.add(tag)
    vis = [token for token in text.split() if re.fullmatch(r"\d{4}", token)]
    if any(int(v) < 5000 for v in vis):
        tags.add("LOW_VISIBILITY")
    if any(tag in tags for tag in ["TSRA", "CB", "THUNDERSTORM"]):
        tags.add("CONVECTIVE_WEATHER")
    if any(tag in tags for tag in ["GUST", "WINDSHEAR", "LOW_VISIBILITY", "CONVECTIVE_WEATHER"]):
        tags.add("UNSTABLE_APPROACH_RISK")
    if "RA" in text or "TSRA" in text:
        tags.add("WET_RWY")
    return sorted(tags)


def parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def taf_window_matches(token: str, arrival: datetime) -> bool:
    match = re.fullmatch(r"(\d{2})(\d{2})/(\d{2})(\d{2})", token)
    if not match:
        return False
    start_day, start_hour, end_day, end_hour = map(int, match.groups())
    arrival_day = arrival.day
    arrival_hour = arrival.hour
    start_value = start_day * 24 + start_hour
    end_value = end_day * 24 + end_hour
    arrival_value = arrival_day * 24 + arrival_hour
    if end_value < start_value:
        end_value += 31 * 24
        if arrival_value < start_value:
            arrival_value += 31 * 24
    return start_value <= arrival_value <= end_value


def select_arrival_taf_segment(taf: str, arrival_time: str | None) -> str:
    arrival = parse_iso_utc(arrival_time)
    if not taf or not arrival:
        return taf
    tokens = taf.split()
    selected = []
    active = False
    for token in tokens:
        if token.startswith("FM") and re.fullmatch(r"FM\d{6}", token):
            day = int(token[2:4])
            hour = int(token[4:6])
            active = day == arrival.day and hour <= arrival.hour
            selected = [token] if active else selected
            continue
        if token in {"TEMPO", "BECMG", "PROB30", "PROB40"}:
            active = False
            selected = []
            continue
        if re.fullmatch(r"\d{4}/\d{4}", token):
            active = taf_window_matches(token, arrival)
            selected = [token] if active else selected
            continue
        if active:
            selected.append(token)
    return " ".join(selected) if selected else taf
