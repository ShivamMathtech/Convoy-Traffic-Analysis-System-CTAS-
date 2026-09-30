"""Pydantic request/response schemas for the REST API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["upload", "video", "image", "image_dir", "webcam", "usb", "rtsp", "http", "demo"]


class AnalysisStartRequest(BaseModel):
    source_type: SourceType
    location: str = ""                      # path / device index / URL
    name: str = ""
    settings_override: dict[str, Any] = Field(default_factory=dict)


class CalibrationRequest(BaseModel):
    session_id: str = ""
    image_points: list[list[float]] = Field(min_length=4, max_length=4)
    world_points: list[list[float]] = Field(min_length=4, max_length=4)
    units: Literal["pixels", "meters"] = "meters"


class LaneRequest(BaseModel):
    session_id: str = ""
    lanes: list[dict[str, Any]]             # [{id, name, polygon:[[x,y]...]}]


class StreamTestRequest(BaseModel):
    url: str
    kind: Literal["rtsp", "http"] = "rtsp"


class VehicleOut(BaseModel):
    track_id: int
    class_name: str
    confidence: float
    bbox: list[float]
    centroid: list[float]
    speed: float | None = None
    speed_unit: str = "px/s"
    heading: float | None = None
    lane: str | None = None
    group_id: int | None = None


class EventOut(BaseModel):
    timestamp: float
    event_type: str
    severity: str
    track_id: int | None = None
    description: str = ""


class StatusOut(BaseModel):
    session_id: str
    state: str
    frame: int = 0
    total_frames: int = 0
    fps: float = 0
    inference_fps: float = 0
    latency_ms: float = 0
    progress: float = 0
    source: str = ""
    model_loaded: bool = False
    error: str | None = None
