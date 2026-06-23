def risk_level(tags: list[str]) -> str:
    high = {"WINDSHEAR", "TSRA", "CB", "LOW_VISIBILITY", "HEAVY_RAIN"}
    medium = {"WET_RWY", "GUST", "TAILWIND", "CROSSWIND", "FOG"}
    if len(high.intersection(tags)) >= 2 or "WINDSHEAR" in tags:
        return "HIGH"
    if high.intersection(tags) or medium.intersection(tags):
        return "MEDIUM"
    return "LOW"


def threat_for_tags(tags: set[str]) -> tuple[str, str]:
    if "WET_RWY" in tags:
        return "Wet Runway Landing Performance", "Wet runway and convective weather may reduce landing performance margin."
    if "CONVECTIVE_WEATHER" in tags or "TSRA" in tags or "CB" in tags:
        return "Convective Weather Near Final Approach", "Thunderstorm cells near final can rapidly reduce path, speed, and wind margin."
    if "UNSTABLE_APPROACH_RISK" in tags:
        return "Unstable Approach and Late Go-Around", "High workload conditions increase continuation bias below stable approach gates."
    if "GPS_INTEGRITY" in tags:
        return "RNAV and GPS Integrity", "Navigation integrity changes require a briefed backup approach and early reconfiguration."
    if "ETOPS" in tags:
        return "Long-Haul Diversion and System Margin", "Long-haul sectors need early fuel, system, and alternate decision gates."
    return "Route-Based Operational Threat", "Similar route events suggest a targeted prevention review."

