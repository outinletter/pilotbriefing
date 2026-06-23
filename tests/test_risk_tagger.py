from src.services.metar_taf_parser import parse_weather_tags
from src.services.risk_tagger import risk_level


def test_convective_low_vis_is_high_risk():
    tags = parse_weather_tags("WADD 220900Z 09012G24KT 3000 TSRA SCT018CB", "")
    assert "TSRA" in tags
    assert "CB" in tags
    assert risk_level(tags) == "HIGH"

