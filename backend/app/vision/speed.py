"""Speed estimation with configurable smoothing (EMA / moving average)."""
from __future__ import annotations

from collections import defaultdict, deque


class SpeedEstimator:
    """Per-track speed from consecutive world/pixel positions.

    v = d / dt, converted to km/h when calibrated (world units = meters).
    Smoothing: exponential moving average  v_s(t) = a*v(t) + (1-a)*v_s(t-1).
    """

    def __init__(self, alpha: float = 0.4, window: int = 5):
        self.alpha = alpha
        self._ema: dict[int, float] = {}
        self._hist: dict[int, deque] = defaultdict(lambda: deque(maxlen=window))
        self._last: dict[int, tuple[float, float, float]] = {}  # track -> (x, y, t)

    def update(self, track_id: int, x: float, y: float, t: float,
               calibrated: bool) -> tuple[float | None, float | None, str]:
        """Return (raw_speed, smoothed_speed, unit). Speeds are None when
        there is no previous observation."""
        prev = self._last.get(track_id)
        self._last[track_id] = (x, y, t)
        if prev is None:
            return None, None, ("km/h" if calibrated else "px/s")
        px, py, pt = prev
        dt = t - pt
        if dt <= 1e-6:
            return None, self._ema.get(track_id), ("km/h" if calibrated else "px/s")
        d = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
        raw = d / dt
        unit = "km/h" if calibrated else "px/s"
        if calibrated:
            raw = raw * 3.6  # m/s -> km/h
        hist = self._hist[track_id]
        hist.append(raw)
        ema_prev = self._ema.get(track_id, raw)
        ema = self.alpha * raw + (1 - self.alpha) * ema_prev
        self._ema[track_id] = ema
        return raw, ema, unit

    def moving_average(self, track_id: int) -> float | None:
        hist = self._hist.get(track_id)
        if not hist:
            return None
        return sum(hist) / len(hist)

    def forget(self, track_id: int) -> None:
        self._ema.pop(track_id, None)
        self._hist.pop(track_id, None)
        self._last.pop(track_id, None)
