"""Event engine + database tests."""
from app.analytics.events import EventEngine
from app.database import SessionLocal, init_db
from app.models.tables import Event as EventRow
from app.models.tables import Session as SessionRow


def test_entered_exited_events():
    eng = EventEngine({"events": {"enabled": {}}})
    evs = eng.entered_exited({1, 2}, 1.0)
    assert {e.event_type for e in evs} == {"Vehicle Entered"}
    evs = eng.entered_exited({2, 3}, 2.0)
    types = {e.event_type for e in evs}
    assert "Vehicle Entered" in types and "Vehicle Exited" in types


def test_stopped_vehicle_fires_after_threshold():
    eng = EventEngine({"events": {"enabled": {}, "stopped_speed_kmh": 2.0, "stopped_seconds": 3.0}})
    assert eng.stopped_vehicle(1, 0.0, 0.5, True) is None
    assert eng.stopped_vehicle(1, 2.9, 0.5, True) is None
    ev = eng.stopped_vehicle(1, 3.1, 0.5, True)
    assert ev is not None and ev.event_type == "Stopped Vehicle"


def test_disabled_rule_emits_nothing():
    eng = EventEngine({"events": {"enabled": {"lane_change": False}}})
    assert eng.lane_change(1, "Lane 1", "Lane 2", 1.0) is None


def test_db_session_and_event_crud():
    init_db()
    db = SessionLocal()
    try:
        db.query(EventRow).filter_by(session_id="test_ses").delete()
        db.query(SessionRow).filter_by(id="test_ses").delete()
        db.add(SessionRow(id="test_ses", name="t", source_type="video",
                          source_path="/tmp/x.mp4", status="complete"))
        db.add(EventRow(session_id="test_ses", timestamp=1.5,
                        event_type="Vehicle Entered", severity="INFO",
                        track_id=7, description="hello"))
        db.commit()
        evs = db.query(EventRow).filter_by(session_id="test_ses").all()
        assert len(evs) == 1 and evs[0].track_id == 7
    finally:
        db.query(EventRow).filter_by(session_id="test_ses").delete()
        db.query(SessionRow).filter_by(id="test_ses").delete()
        db.commit()
        db.close()
