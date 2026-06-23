import json

from ..config import BASE_DIR


def load_airports() -> dict[str, str]:
    with open(BASE_DIR / "sample_airports.json", encoding="utf-8") as f:
        return json.load(f)


def iata_to_icao(iata: str | None) -> str:
    if not iata:
        return ""
    return load_airports().get(iata.upper(), iata.upper())

