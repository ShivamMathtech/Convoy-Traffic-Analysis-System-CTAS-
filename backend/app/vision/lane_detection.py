"""Lane analysis: operator-drawn polygons (primary) + optional auto estimation.

Lane assignment is point-in-polygon on the track centroid. A lane change
event fires when a confirmed track moves between two valid lane regions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger("ctas.lanes")


@dataclass
class Lane:
    id: str
    name: str
    polygon: list[list[float]]  # [[x,y], ...] in image pixels


class LaneAnalyzer:
    def __init__(self):
        self.lanes: list[Lane] = []
        self._last_lane: dict[int, str | None] = {}

    # ------------------------------------------------------------- setup
    def set_lanes(self, lanes: list[dict]) -> None:
        self.lanes = [Lane(id=str(l.get("id", i + 1)),
                           name=str(l.get("name", f"Lane {i + 1}")),
                           polygon=[[float(x), float(y)] for x, y in l["polygon"]])
                      for i, l in enumerate(lanes)]
        log.info("Configured %d lanes", len(self.lanes))

    def estimate_lanes(self, width: int, height: int, n: int = 3) -> list[Lane]:
        """Naive vertical-stripe estimation used only when the operator has
        not drawn lanes. Clearly an approximation."""
        lanes = []
        for i in range(n):
            x0, x1 = width * i / n, width * (i + 1) / n
            lanes.append(Lane(id=str(i + 1), name=f"Lane {i + 1}",
                              polygon=[[x0, 0], [x1, 0], [x1, height], [x0, height]]))
        self.lanes = lanes
        return lanes

    # ------------------------------------------------------------ assign
    @staticmethod
    def _inside(polygon: list[list[float]], x: float, y: float) -> bool:
        import cv2
        return cv2.pointPolygonTest(np.asarray(polygon, dtype=np.float32), (x, y), False) >= 0

    def assign(self, x: float, y: float) -> str | None:
        for lane in self.lanes:
            if self._inside(lane.polygon, x, y):
                return lane.name
        return None

    def lane_of_track(self, track_id: int, x: float, y: float) -> tuple[str | None, bool]:
        """Return (lane_name, changed_since_last_frame)."""
        lane = self.assign(x, y)
        prev = self._last_lane.get(track_id)
        changed = prev is not None and lane is not None and prev != lane
        self._last_lane[track_id] = lane
        return lane, changed

    def occupancy(self, lane_name: str, centroids: list[tuple[float, float]]) -> int:
        return sum(1 for x, y in centroids if self.assign(x, y) == lane_name)

    def forget(self, track_id: int) -> None:
        self._last_lane.pop(track_id, None)
