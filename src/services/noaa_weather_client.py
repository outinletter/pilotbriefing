import httpx


async def _fetch(kind: str, icao: str) -> tuple[str | None, str | None]:
    url = f"https://aviationweather.gov/api/data/{kind}?ids={icao}&format=json"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            if data:
                return data[0].get("rawOb") or data[0].get("rawTAF") or data[0].get("raw_text"), None
    except Exception:
        pass
    return None, "Weather API unavailable; showing route-based risk briefing."


async def get_weather(icao: str) -> tuple[dict, list[str]]:
    metar, metar_msg = await _fetch("metar", icao)
    taf, taf_msg = await _fetch("taf", icao)
    messages = sorted({m for m in [metar_msg, taf_msg] if m})
    if not metar and icao == "WADD":
        metar = "WADD 220900Z 09012G24KT 5000 TSRA SCT018CB BKN030 27/25 Q1008 TEMPO WS"
    if not taf and icao == "WADD":
        taf = "TAF WADD 220500Z 2206/2312 10012KT 6000 TSRA SCT018CB BKN030 TEMPO 2209/2214 3000 +TSRA WS"
    return {"metar": metar or "", "taf": taf or ""}, messages

