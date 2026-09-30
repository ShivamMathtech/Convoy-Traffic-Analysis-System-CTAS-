"""SQLAlchemy table definitions (see spec section 30)."""
from __future__ import annotations

import datetime as _dt

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now():
    return _dt.datetime.utcnow()


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    source_type: Mapped[str] = mapped_column(String(32), default="video")
    source_path: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=_now)
    ended_at: Mapped[_dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="idle")
    fps: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    total_frames: Mapped[int] = mapped_column(Integer, default=0)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)


class Detection(Base):
    __tablename__ = "detections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    frame_number: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[float] = mapped_column(Float)
    track_id: Mapped[int] = mapped_column(Integer, default=-1)
    class_name: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    x2: Mapped[float] = mapped_column(Float)
    y2: Mapped[float] = mapped_column(Float)


class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)
    class_name: Mapped[str] = mapped_column(String(32))
    first_seen: Mapped[float] = mapped_column(Float)
    last_seen: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float, default=0)
    avg_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    lane: Mapped[str | None] = mapped_column(String(32), nullable=True)


class TrackPoint(Base):
    __tablename__ = "track_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True)
    frame_number: Mapped[int] = mapped_column(Integer, default=0)
    pixel_x: Mapped[float] = mapped_column(Float)
    pixel_y: Mapped[float] = mapped_column(Float)
    world_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    world_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    lane: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default="INFO")
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Calibration(Base):
    __tablename__ = "calibrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    image_points: Mapped[list] = mapped_column(JSON)
    world_points: Mapped[list] = mapped_column(JSON)
    homography: Mapped[list] = mapped_column(JSON)


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    timestamp: Mapped[float] = mapped_column(Float, index=True)
    vehicle_count: Mapped[int] = mapped_column(Integer, default=0)
    class_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    average_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_spacing: Mapped[float | None] = mapped_column(Float, nullable=True)
    group_count: Mapped[int] = mapped_column(Integer, default=0)
