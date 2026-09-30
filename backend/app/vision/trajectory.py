"""Trajectory history store: per-track deque of (x, y, t)."""
from __future__ import annotations

from collections import defaultdict, deque


class TrajectoryStore:
    def __init__(self, maxlen: int = 600):
        self._store: dict[int, deque] = defaultdict(lambda: deque(maxlen=maxlen))

    def push(self, track_id: int, x: float, y: float, t: float) -> None:
        self._store[track_id].append((x, y, t))

    def get(self, track_id: int, seconds: float | None = None,
            now: float | None = None) -> list[tuple[float, float, float]]:
        pts = list(self._store.get(track_id, []))
        if seconds is not None and now is not None:
            pts = [p for p in pts if now - p[2] <= seconds]
        return pts

    def drop(self, track_id: int) -> None:
        self._store.pop(track_id, None)

    def clear(self) -> None:
        self._store.clear()
