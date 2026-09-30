"""Multi-object tracker abstraction.

Implements two configurable tracking adapters on a shared IoU-association
core:

* :class:`ByteTrackAdapter` — two-stage association (high-confidence
  detections first, then low-confidence ones), lost-track buffer.
* :class:`BoTSORTAdapter` — same core plus a constant-velocity motion
  prediction step before association.

Both maintain per-track: id, class, confidence, bbox, centroid, trajectory
history, first/last seen, velocity, heading, lane and group membership.
Tracks are confirmed after ``min_hits`` matches and expire after ``max_age``
frames without a match. These are faithful lightweight adapters of the
published algorithms' association logic, tuned for CPU use.
"""
from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger("ctas.tracker")


def _iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def _centroid(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


@dataclass
class TrackState:
    id: int
    class_name: str
    confidence: float
    bbox: list[float]
    centroid: tuple[float, float]
    hits: int = 1
    age: int = 1
    time_since_update: int = 0
    confirmed: bool = False
    first_seen: float = 0.0
    last_seen: float = 0.0
    velocity: tuple[float, float] = (0.0, 0.0)   # px/s in image plane
    heading: float | None = None                 # degrees, 0 = +x
    lane: str | None = None
    group_id: int | None = None
    speed: float | None = None                   # smoothed, unit depends on calibration
    history: deque = field(default_factory=lambda: deque(maxlen=600))

    def to_dict(self) -> dict:
        return {
            "track_id": self.id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": [round(float(v), 1) for v in self.bbox],
            "centroid": [round(float(self.centroid[0]), 1), round(float(self.centroid[1]), 1)],
            "speed": None if self.speed is None else round(float(self.speed), 2),
            "heading": None if self.heading is None else round(float(self.heading), 1),
            "lane": self.lane,
            "group_id": self.group_id,
            "age": self.age,
        }


class TrackerBase:
    def __init__(self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self._next_id = 1
        self.tracks: list[TrackState] = []

    # ------------------------------------------------------------ core
    def _associate(self, tracks: list[TrackState], detections: list,
                   iou_thr: float) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        """Greedy IoU matching. Returns (matches, unmatched_track_idx, unmatched_det_idx)."""
        if not tracks or not detections:
            return [], list(range(len(tracks))), list(range(len(detections)))
        iou_mat = np.zeros((len(tracks), len(detections)))
        for i, t in enumerate(tracks):
            for j, d in enumerate(detections):
                iou_mat[i, j] = _iou(t.bbox, d.bbox)
        matches: list[tuple[int, int]] = []
        used_t, used_d = set(), set()
        # greedy: repeatedly take the best remaining pair above threshold
        flat = [ (iou_mat[i, j], i, j) for i in range(len(tracks)) for j in range(len(detections)) ]
        flat.sort(reverse=True)
        for score, i, j in flat:
            if score < iou_thr or i in used_t or j in used_d:
                continue
            matches.append((i, j))
            used_t.add(i); used_d.add(j)
        unmatched_t = [i for i in range(len(tracks)) if i not in used_t]
        unmatched_d = [j for j in range(len(detections)) if j not in used_d]
        return matches, unmatched_t, unmatched_d

    def _new_track(self, det, timestamp: float) -> TrackState:
        c = _centroid(det.bbox)
        tr = TrackState(
            id=self._next_id, class_name=det.class_name, confidence=det.confidence,
            bbox=list(det.bbox), centroid=c, first_seen=timestamp, last_seen=timestamp,
            confirmed=(1 >= self.min_hits),
        )
        tr.history.append((c[0], c[1], timestamp))
        self._next_id += 1
        return tr

    def _update_track(self, tr: TrackState, det, timestamp: float, dt: float) -> None:
        new_c = _centroid(det.bbox)
        if dt > 1e-6 and tr.history:
            vx = (new_c[0] - tr.centroid[0]) / dt
            vy = (new_c[1] - tr.centroid[1]) / dt
            tr.velocity = (vx, vy)
            if abs(vx) + abs(vy) > 1e-3:
                tr.heading = math.degrees(math.atan2(vy, vx))
        tr.bbox = list(det.bbox)
        tr.centroid = new_c
        tr.confidence = det.confidence
        tr.class_name = det.class_name
        tr.hits += 1
        tr.age += 1
        tr.time_since_update = 0
        tr.last_seen = timestamp
        tr.history.append((new_c[0], new_c[1], timestamp))
        if tr.hits >= self.min_hits:
            tr.confirmed = True

    def update(self, detections: list, timestamp: float) -> list[TrackState]:
        raise NotImplementedError

    def active_tracks(self) -> list[TrackState]:
        return [t for t in self.tracks if t.confirmed and t.time_since_update == 0]

    def reset(self) -> None:
        self.tracks = []
        self._next_id = 1


class ByteTrackAdapter(TrackerBase):
    """Two-stage association: high-confidence detections first, then
    low-confidence detections are matched against remaining tracks
    (recovers occluded vehicles)."""

    def __init__(self, low_conf_threshold: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.low_conf_threshold = low_conf_threshold

    def update(self, detections: list, timestamp: float) -> list[TrackState]:
        split = max(0.2, self.low_conf_threshold + 0.2)
        high = [d for d in detections if d.confidence >= split]
        low = [d for d in detections if self.low_conf_threshold <= d.confidence < split]

        matches, unmatched_t, unmatched_d = self._associate(self.tracks, high, self.iou_threshold)
        for ti, di in matches:
            tr = self.tracks[ti]
            _dt = timestamp - tr.last_seen if tr.last_seen else 1 / 30
            self._update_track(tr, high[di], timestamp, max(_dt, 1e-3))

        # second stage: match leftover tracks with low-confidence detections
        remaining = [self.tracks[i] for i in unmatched_t]
        matches2, _, unmatched_d2 = self._associate(remaining, low, self.iou_threshold * 0.7)
        matched_low = set()
        for ti, di in matches2:
            tr = remaining[ti]
            _dt = timestamp - tr.last_seen if tr.last_seen else 1 / 30
            self._update_track(tr, low[di], timestamp, max(_dt, 1e-3))
            matched_low.add(unmatched_t[ti])

        # age unmatched tracks, spawn new ones from unmatched high-conf detections
        for i, tr in enumerate(self.tracks):
            if all(ti != i for ti, _ in matches) and i not in matched_low:
                tr.time_since_update += 1
                tr.age += 1
        for j in unmatched_d:
            self.tracks.append(self._new_track(high[j], timestamp))
        # note: unmatched low-conf detections do NOT spawn tracks (ByteTrack rule)

        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]
        return self.active_tracks()


class BoTSORTAdapter(TrackerBase):
    """IoU association with a constant-velocity motion prediction step."""

    def _predict(self, tr: TrackState, dt: float) -> list[float]:
        vx, vy = tr.velocity
        dx, dy = vx * dt, vy * dt
        x1, y1, x2, y2 = tr.bbox
        return [x1 + dx, y1 + dy, x2 + dx, y2 + dy]

    def update(self, detections: list, timestamp: float) -> list[TrackState]:
        # predict step
        for tr in self.tracks:
            dt = max(timestamp - tr.last_seen, 1e-3)
            tr.bbox = self._predict(tr, min(dt, 0.5))
            tr.centroid = _centroid(tr.bbox)
        matches, unmatched_t, unmatched_d = self._associate(self.tracks, detections, self.iou_threshold)
        matched = set()
        for ti, di in matches:
            tr = self.tracks[ti]
            _dt = max(timestamp - tr.last_seen, 1e-3)
            self._update_track(tr, detections[di], timestamp, _dt)
            matched.add(ti)
        for i, tr in enumerate(self.tracks):
            if i not in matched:
                tr.time_since_update += 1
                tr.age += 1
        for j in unmatched_d:
            self.tracks.append(self._new_track(detections[j], timestamp))
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]
        return self.active_tracks()


def create_tracker(settings: dict) -> TrackerBase:
    t = (settings or {}).get("tracker", {})
    name = str(t.get("name", "bytetrack")).lower()
    kwargs = dict(
        max_age=int(t.get("max_age", 30)),
        min_hits=int(t.get("min_hits", 3)),
        iou_threshold=float(t.get("iou_threshold", 0.3)),
    )
    if name == "botsort":
        return BoTSORTAdapter(**kwargs)
    return ByteTrackAdapter(low_conf_threshold=float(t.get("low_conf_threshold", 0.1)), **kwargs)
