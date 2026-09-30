"""Inter-vehicle spacing: sort vehicles along road direction, then measure
consecutive gaps. Uses world coords when calibrated, pixels otherwise."""
from __future__ import annotations

import math
import statistics as _stats

from app.vision.geometry import pixel_distance


def _positions(tracks: list, calibrated: bool) -> list[tuple[float, float]]:
    pts = []
    for t in tracks:
        p = getattr(t, "world_xy", None) if calibrated else None
        pts.append(p if p is not None else t.centroid)
    return pts


def spacing_stats(tracks: list, calibrated: bool) -> dict:
    pts = _positions(tracks, calibrated)
    if len(pts) < 2:
        return {"count": len(pts), "min": None, "max": None, "mean": None,
                "median": None, "stdev": None, "unit": "m" if calibrated else "px"}
    headings = [t.heading for t in tracks if t.heading is not None]
    ang = math.radians(sum(headings) / len(headings)) if headings else 0.0
    dx, dy = math.cos(ang), math.sin(ang)
    order = sorted(pts, key=lambda p: p[0] * dx + p[1] * dy)
    gaps = [pixel_distance(order[i], order[i + 1]) for i in range(len(order) - 1)]
    return {
        "count": len(pts),
        "min": min(gaps),
        "max": max(gaps),
        "mean": sum(gaps) / len(gaps),
        "median": _stats.median(gaps),
        "stdev": _stats.pstdev(gaps) if len(gaps) > 1 else 0.0,
        "unit": "m" if calibrated else "px",
    }
