"""Rule-based event engine. Every event is generated from backend state —
no fake events. Rules can be enabled/disabled and thresholds tuned via
Settings; the engine consults the settings snapshot it was built with.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("ctas.events")


@dataclass
class Event:
    timestamp: float
    event_type: str
    severity: str = "INFO"          # INFO | LOW | MEDIUM | HIGH
    track_id: int | None = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": round(self.timestamp, 2),
            "event_type": self.event_type,
            "severity": self.severity,
            "track_id": self.track_id,
            "description": self.description,
        }


class EventEngine:
    def __init__(self, settings: dict | None = None):
        ev = (settings or {}).get("events", {})
        self.enabled: dict = ev.get("enabled", {})
        self.stopped_speed = float(ev.get("stopped_speed_kmh", 2.0))
        self.stopped_seconds = float(ev.get("stopped_seconds", 3.0))
        self.spacing_warn = float(ev.get("spacing_warn_m", 5.0))
        self._known_ids: set[int] = set()
        self._stopped_since: dict[int, float] = {}
        self._spacing_warned: set[int] = set()
        self.events: list[Event] = []

    # ------------------------------------------------------------- util
    def _on(self, rule: str) -> bool:
        return bool(self.enabled.get(rule, True))

    def emit(self, event: Event) -> Event:
        self.events.append(event)
        log.info("EVENT %s [%s] %s", event.event_type, event.severity, event.description)
        return event

    # ------------------------------------------------------------- rules
    def entered_exited(self, active_ids: set[int], timestamp: float) -> list[Event]:
        out = []
        for tid in sorted(active_ids - self._known_ids):
            if self._on("vehicle_entered"):
                out.append(self.emit(Event(timestamp, "Vehicle Entered", "INFO", tid,
                                            f"Vehicle ID {tid} entered the scene")))
        for tid in sorted(self._known_ids - active_ids):
            if self._on("vehicle_exited"):
                out.append(self.emit(Event(timestamp, "Vehicle Exited", "INFO", tid,
                                            f"Vehicle ID {tid} left the scene")))
        self._known_ids = set(active_ids)
        return out

    def lane_change(self, track_id: int, from_lane: str, to_lane: str, timestamp: float) -> Event | None:
        if not self._on("lane_change"):
            return None
        return self.emit(Event(timestamp, "Lane Change", "LOW", track_id,
                               f"Vehicle ID {track_id} changed lane {from_lane} → {to_lane}"))

    def group_formed(self, group_id: int, size: int, timestamp: float) -> Event | None:
        if not self._on("group_formation"):
            return None
        return self.emit(Event(timestamp, "Group Formation Detected", "MEDIUM", None,
                               f"Convoy group {group_id} formed with {size} vehicles"))

    def group_left(self, track_id: int, group_id: int, timestamp: float) -> Event | None:
        return self.emit(Event(timestamp, "Vehicle Left Group", "LOW", track_id,
                               f"Vehicle ID {track_id} left group {group_id}"))

    def stopped_vehicle(self, track_id: int, timestamp: float,
                        speed: float | None, calibrated: bool) -> Event | None:
        if not self._on("stopped_vehicle"):
            return None
        slow = False
        if speed is not None:
            slow = (speed < self.stopped_speed) if calibrated else (speed < 2.0)
        if slow:
            self._stopped_since.setdefault(track_id, timestamp)
            if timestamp - self._stopped_since[track_id] >= self.stopped_seconds:
                del self._stopped_since[track_id]
                unit = "km/h" if calibrated else "px/s"
                return self.emit(Event(timestamp, "Stopped Vehicle", "MEDIUM", track_id,
                                       f"Vehicle ID {track_id} stationary "
                                       f"({speed:.1f} {unit}) for {self.stopped_seconds:.0f}s"))
        else:
            self._stopped_since.pop(track_id, None)
        return None

    def spacing_threshold(self, track_id: int, gap: float, timestamp: float,
                          calibrated: bool) -> Event | None:
        if not self._on("spacing_threshold") or not calibrated:
            return None
        if gap < self.spacing_warn and track_id not in self._spacing_warned:
            self._spacing_warned.add(track_id)
            return self.emit(Event(timestamp, "Spacing Threshold Triggered", "HIGH", track_id,
                                   f"Vehicle ID {track_id} gap {gap:.1f} m below {self.spacing_warn:.1f} m"))
        if gap >= self.spacing_warn:
            self._spacing_warned.discard(track_id)
        return None

    def congestion(self, timestamp: float, count: int) -> Event | None:
        if not self._on("congestion"):
            return None
        return self.emit(Event(timestamp, "Congestion Detected", "HIGH", None,
                               f"High density: {count} vehicles in frame"))

    def stream_interrupted(self, timestamp: float, detail: str = "") -> Event | None:
        if not self._on("stream"):
            return None
        return self.emit(Event(timestamp, "Stream Interrupted", "HIGH", None,
                               f"Stream interrupted{(': ' + detail) if detail else ''} — reconnecting"))

    def camera_reconnected(self, timestamp: float) -> Event | None:
        if not self._on("stream"):
            return None
        return self.emit(Event(timestamp, "Camera Reconnected", "MEDIUM", None,
                               "Stream reconnected successfully"))

    def lifecycle(self, kind: str, timestamp: float, detail: str = "") -> Event:
        mapping = {"started": ("Analysis Started", "INFO"),
                   "stopped": ("Analysis Stopped", "INFO"),
                   "paused": ("Analysis Paused", "LOW")}
        etype, sev = mapping.get(kind, (kind, "INFO"))
        return self.emit(Event(timestamp, etype, sev, None, detail))

    def recent(self, n: int = 100) -> list[Event]:
        return self.events[-n:]
