"""Session history / replay API."""
from __future__ import annotations

import shutil

from fastapi import APIRouter, HTTPException

from app import config
from app.database import SessionLocal
from app.models.tables import Event as EventRow
from app.models.tables import Session as SessionRow
from app.models.tables import Track as TrackRow
from app.services.session_manager import manager

router = APIRouter()


def _row_to_dict(r: SessionRow) -> dict:
    return {"id": r.id, "name": r.name, "source_type": r.source_type,
            "source_path": r.source_path,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            "status": r.status, "fps": r.fps, "width": r.width, "height": r.height,
            "total_frames": r.total_frames}


@router.get("")
def list_sessions():
    db = SessionLocal()
    try:
        rows = db.query(SessionRow).order_by(SessionRow.started_at.desc()).limit(200).all()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["vehicles"] = db.query(TrackRow).filter_by(session_id=r.id).count()
            d["events"] = db.query(EventRow).filter_by(session_id=r.id).count()
            out.append(d)
        return {"sessions": out}
    finally:
        db.close()


@router.get("/{session_id}")
def get_session(session_id: str):
    db = SessionLocal()
    try:
        r = db.get(SessionRow, session_id)
        if not r:
            raise HTTPException(404, "Session not found")
        return _row_to_dict(r)
    finally:
        db.close()


@router.get("/{session_id}/replay")
def replay(session_id: str):
    """Everything the frontend needs to replay a saved session."""
    return manager.session_payload(session_id)


@router.get("/{session_id}/vehicles")
def vehicles(session_id: str, active_only: bool = True):
    p = manager.get_pipeline(session_id)
    if p:
        tracks = p.tracker.active_tracks() if active_only else p.tracker.tracks
        unit = "km/h" if p.calibration.is_calibrated else "px/s"
        return {"vehicles": [{**t.to_dict(), "speed_unit": unit} for t in tracks
                             if t.confirmed or not active_only],
                "unit": unit, "live": True}
    db = SessionLocal()
    try:
        rows = db.query(TrackRow).filter_by(session_id=session_id).all()
        return {"vehicles": [{"track_id": t.track_id, "class_name": t.class_name,
                              "first_seen": t.first_seen, "last_seen": t.last_seen,
                              "duration": t.duration, "avg_speed": t.avg_speed,
                              "lane": t.lane} for t in rows],
                "unit": "km/h", "live": False}
    finally:
        db.close()


@router.get("/{session_id}/tracks/{track_id}")
def track_detail(session_id: str, track_id: int):
    db = SessionLocal()
    try:
        t = db.query(TrackRow).filter_by(session_id=session_id, track_id=track_id).first()
        if not t:
            raise HTTPException(404, "Track not found")
        return {"track_id": t.track_id, "class_name": t.class_name,
                "first_seen": t.first_seen, "last_seen": t.last_seen,
                "duration": t.duration, "avg_speed": t.avg_speed, "lane": t.lane}
    finally:
        db.close()


@router.get("/{session_id}/events")
def events(session_id: str, limit: int = 500):
    p = manager.get_pipeline(session_id)
    if p:
        return {"events": [e.to_dict() for e in p.events.recent(limit)], "live": True}
    db = SessionLocal()
    try:
        rows = (db.query(EventRow).filter_by(session_id=session_id)
                .order_by(EventRow.timestamp).limit(limit).all())
        return {"events": [{"timestamp": e.timestamp, "event_type": e.event_type,
                            "severity": e.severity, "track_id": e.track_id,
                            "description": e.description} for e in rows], "live": False}
    finally:
        db.close()


@router.get("/{session_id}/analytics")
def analytics(session_id: str):
    p = manager.get_pipeline(session_id)
    if p:
        payload = p.agg.chart_payload()
        payload["calibrated"] = p.calibration.is_calibrated
        payload["unit"] = "m" if p.calibration.is_calibrated else "px"
        return payload
    import json
    fp = config.OUTPUT_DIR / session_id / "analytics.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    raise HTTPException(404, "No analytics for session")


@router.delete("/{session_id}")
def delete_session(session_id: str):
    p = manager.get_pipeline(session_id)
    if p:
        try:
            p.stop()
        except Exception:  # noqa: BLE001
            pass
    db = SessionLocal()
    try:
        for model in (EventRow, TrackRow):
            db.query(model).filter_by(session_id=session_id).delete()
        db.query(SessionRow).filter_by(id=session_id).delete()
        db.commit()
    finally:
        db.close()
    shutil.rmtree(config.OUTPUT_DIR / session_id, ignore_errors=True)
    return {"ok": True}
