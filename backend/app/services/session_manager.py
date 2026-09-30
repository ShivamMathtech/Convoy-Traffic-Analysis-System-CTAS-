"""Session manager: owns pipeline lifecycles, DB rows, output dirs and
WebSocket fan-out for every analysis session."""
from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import threading
from pathlib import Path

from app import config
from app.database import SessionLocal
from app.models.tables import Calibration as CalibrationRow
from app.models.tables import Event as EventRow
from app.models.tables import Session as SessionRow
from app.models.tables import Track as TrackRow
from app.streaming.video_reader import create_source
from app.streaming.websocket import manager_ws
from app.utils.helpers import new_id
from app.vision.pipeline import AnalysisPipeline

log = logging.getLogger("ctas.sessions")


def _event_key(ev: dict) -> tuple:
    """Identity of an event row — used to avoid double-persisting."""
    return (round(float(ev.get("timestamp", 0) or 0), 3),
            str(ev.get("event_type", "")),
            ev.get("track_id"),
            str(ev.get("description", ""))[:160])


class SessionManager:
    def __init__(self):
        self._pipelines: dict[str, AnalysisPipeline] = {}
        self._lock = threading.Lock()
        self._persisted_event_keys: dict[str, set] = {}
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = None

    # ------------------------------------------------------------ CRUD
    def active_count(self) -> int:
        return len(self._pipelines)

    def get_pipeline(self, session_id: str) -> AnalysisPipeline | None:
        return self._pipelines.get(session_id)

    # ------------------------------------------------------------ start
    def start_analysis(self, source_type: str, location: str, name: str,
                       settings: dict) -> str:
        session_id = new_id("ses")
        out_dir = config.OUTPUT_DIR / session_id
        out_dir.mkdir(parents=True, exist_ok=True)

        db = SessionLocal()
        try:
            db.add(SessionRow(id=session_id, name=name or session_id,
                              source_type=source_type, source_path=location,
                              status="loading", settings=settings))
            db.commit()
        finally:
            db.close()

        source = create_source(source_type, location)

        def on_event(ev: dict):
            ev["session_id"] = session_id
            self._persist_event(session_id, ev)
            self._broadcast(session_id, {"type": "event", "event": ev})

        def on_status(st: dict):
            self._broadcast(session_id, {"type": "status", "status": st})

        pipe = AnalysisPipeline(session_id, source, settings, out_dir,
                                on_event=on_event, on_status=on_status)
        with self._lock:
            self._pipelines[session_id] = pipe
        try:
            pipe.start()
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to start session %s", session_id)
            pipe.error = str(exc)
            try:
                pipe._set_state("ERROR")
            except Exception:  # noqa: BLE001
                pipe.state = "ERROR"
            self._mark_status(session_id, "error")
            raise
        self._mark_status(session_id, "running",
                          fps=pipe.info.fps, width=pipe.info.width,
                          height=pipe.info.height, total_frames=pipe.info.total_frames)
        self._broadcast(session_id, {"type": "status", "status": pipe.status_dict()})
        return session_id

    def pause(self, session_id: str):
        p = self._require(session_id)
        p.pause()
        self._mark_status(session_id, "paused")

    def resume(self, session_id: str):
        p = self._require(session_id)
        p.resume()
        self._mark_status(session_id, "running")

    def stop(self, session_id: str) -> dict:
        p = self._require(session_id)
        p.stop()
        self._finalize_session(session_id, p)
        with self._lock:
            self._pipelines.pop(session_id, None)
        return p.status_dict()

    def status(self, session_id: str) -> dict:
        p = self._pipelines.get(session_id)
        if p:
            return p.status_dict()
        db = SessionLocal()
        try:
            row = db.get(SessionRow, session_id)
            if not row:
                raise KeyError(session_id)
            return {"session_id": session_id, "state": row.status.upper(),
                    "frame": 0, "total_frames": row.total_frames,
                    "source": row.source_path, "model_loaded": False}
        finally:
            db.close()

    def set_calibration(self, session_id: str, image_points, world_points, units) -> dict:
        p = self._require(session_id)
        p.calibration.set_points(image_points, world_points, units)
        p.settings.setdefault("calibration", {}).update(
            {"image_points": image_points, "world_points": world_points, "units": units})
        db = SessionLocal()
        try:
            db.add(CalibrationRow(session_id=session_id, image_points=image_points,
                                  world_points=world_points,
                                  homography=p.calibration.H.tolist()))
            db.commit()
        finally:
            db.close()
        return p.calibration.as_dict()

    def set_lanes(self, session_id: str, lanes: list[dict]) -> dict:
        p = self._require(session_id)
        p.lanes.set_lanes(lanes)
        p.settings["lanes"] = lanes
        return {"lanes": lanes}

    # ------------------------------------------------------------ internals
    def _require(self, session_id: str) -> AnalysisPipeline:
        p = self._pipelines.get(session_id)
        if not p:
            raise KeyError(session_id)
        return p

    def set_loop(self, loop) -> None:
        """Called from the FastAPI lifespan — the loop worker threads use
        to broadcast WebSocket messages."""
        self._loop = loop

    def _broadcast(self, session_id: str, message: dict):
        loop = self._loop
        if loop is None or not loop.is_running():
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                return
            if not loop.is_running():
                return
        try:
            asyncio.run_coroutine_threadsafe(manager_ws.broadcast(session_id, message), loop)
        except RuntimeError:
            pass

    def _mark_status(self, session_id: str, status: str, **kw):
        db = SessionLocal()
        try:
            row = db.get(SessionRow, session_id)
            if row:
                row.status = status
                for k, v in kw.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                if status in ("complete", "error", "stopped"):
                    row.ended_at = _dt.datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def _persist_event(self, session_id: str, ev: dict):
        db = SessionLocal()
        try:
            db.add(EventRow(session_id=session_id, timestamp=float(ev.get("timestamp", 0)),
                            event_type=ev.get("event_type", ""),
                            severity=ev.get("severity", "INFO"),
                            track_id=ev.get("track_id"),
                            description=ev.get("description", "")))
            db.commit()
            self._persisted_event_keys.setdefault(session_id, set()).add(_event_key(ev))
        except Exception:  # noqa: BLE001
            db.rollback()
        finally:
            db.close()

    def _finalize_session(self, session_id: str, pipe: AnalysisPipeline):
        """Persist per-track summary rows and mark the session complete."""
        db = SessionLocal()
        try:
            for tr in pipe.tracker.tracks:
                if not tr.confirmed:
                    continue
                db.add(TrackRow(session_id=session_id, track_id=tr.id,
                                class_name=tr.class_name,
                                first_seen=tr.first_seen, last_seen=tr.last_seen,
                                duration=tr.last_seen - tr.first_seen,
                                avg_speed=tr.speed, lane=tr.lane))
            # leftover buffered events (safety net) — skip any already persisted
            # via the live on_event callback so rows are not duplicated
            seen = self._persisted_event_keys.get(session_id, set())
            for ev in pipe.events.events:
                key = _event_key(ev.to_dict())  # same rounding as the live path
                if key in seen:
                    continue
                seen.add(key)
                db.add(EventRow(session_id=session_id, timestamp=ev.timestamp,
                                event_type=ev.event_type, severity=ev.severity,
                                track_id=ev.track_id, description=ev.description))
            self._persisted_event_keys.pop(session_id, None)
            row = db.get(SessionRow, session_id)
            if row:
                row.status = "complete"
                row.ended_at = _dt.datetime.utcnow()
            db.commit()
        except Exception:  # noqa: BLE001
            log.exception("finalize failed")
            db.rollback()
        finally:
            db.close()

    # ------------------------------------------------------------ replay data
    def session_payload(self, session_id: str) -> dict:
        """Full replay payload: session.json + events + tracks from DB/outputs."""
        out = config.OUTPUT_DIR / session_id / "session.json"
        payload: dict = {}
        if out.exists():
            payload = json.loads(out.read_text(encoding="utf-8"))
        db = SessionLocal()
        try:
            row = db.get(SessionRow, session_id)
            if row:
                payload.setdefault("meta", {
                    "id": row.id, "name": row.name, "source_type": row.source_type,
                    "source_path": row.source_path,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "status": row.status, "fps": row.fps,
                    "width": row.width, "height": row.height,
                })
            payload["events"] = [
                {"timestamp": e.timestamp, "event_type": e.event_type,
                 "severity": e.severity, "track_id": e.track_id,
                 "description": e.description}
                for e in db.query(EventRow).filter_by(session_id=session_id)
                        .order_by(EventRow.timestamp).limit(2000).all()
            ]
            payload["tracks"] = [
                {"track_id": t.track_id, "class_name": t.class_name,
                 "first_seen": t.first_seen, "last_seen": t.last_seen,
                 "duration": t.duration, "avg_speed": t.avg_speed, "lane": t.lane}
                for t in db.query(TrackRow).filter_by(session_id=session_id).all()
            ]
        finally:
            db.close()
        return payload


manager = SessionManager()
