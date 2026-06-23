from src.database import Base, SessionLocal, engine
from src.seed import seed
from src.services.similarity_engine import ranked_events


def test_dps_events_rank_for_ke629_context():
    Base.metadata.create_all(bind=engine)
    seed()
    db = SessionLocal()
    try:
        context = {"arrival_icao": "WADD", "destination_runway": "RWY09"}
        rows = ranked_events(db, context, ["TSRA", "CB", "WET_RWY", "LOW_VISIBILITY"])
        assert rows[0][0].airport_icao == "WADD"
        assert rows[0][1] >= 80
    finally:
        db.close()

