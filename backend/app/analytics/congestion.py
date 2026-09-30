"""Congestion detection: sustained high vehicle density in frame."""
from __future__ import annotations


class CongestionDetector:
    def __init__(self, density_threshold: int = 25, sustain_seconds: float = 10.0):
        self.density_threshold = density_threshold
        self.sustain_seconds = sustain_seconds
        self._since: float | None = None
        self._fired = False

    def update(self, vehicle_count: int, timestamp: float) -> bool:
        """Return True exactly once when congestion newly triggers."""
        if vehicle_count >= self.density_threshold:
            if self._since is None:
                self._since = timestamp
            if not self._fired and timestamp - self._since >= self.sustain_seconds:
                self._fired = True
                return True
        else:
            self._since = None
            self._fired = False
        return False

    def reset(self) -> None:
        self._since = None
        self._fired = False
