from fastapi.testclient import TestClient

from src.main import app


def test_ke629_briefing_demo():
    client = TestClient(app)
    response = client.get("/api/briefing/KE629")
    assert response.status_code == 200
    data = response.json()
    assert data["flight_context"]["route"] == "ICN-DPS"
    assert data["flight_context"]["arrival_icao"] == "WADD"
    assert data["top_threats"]
    assert len(data["top_threats"]) <= 5
    assert data["top_threats"][0]["events"]
    event = data["top_threats"][0]["events"][0]
    assert event["category"]
    assert event["severity"] in {"Low", "Medium", "High", "Critical"}
    assert event["a350_b787_applicability"]
    assert event["recommended_action"]
