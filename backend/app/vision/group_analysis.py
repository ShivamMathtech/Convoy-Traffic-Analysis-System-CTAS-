"""Convoy / group analysis for fleet & logistics research.

Group membership requires spatial proximity AND similar heading AND temporal
persistence. Metric thresholds apply when calibrated, otherwise configurable
pixel thresholds are used (and the UI labels them as such).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from app.vision.geometry import angle_between, pixel_distance

log = logging.getLogger("ctas.groups")


@dataclass
class Group:
    id: int
    member_ids: list[int]
    avg_speed: float | None
    avg_spacing: float | None
    direction_deg: float | None
    duration_s: float
    unit: str = "px"


class GroupAnalyzer:
    def __init__(self, dmax: float = 35.0, hmax_deg: float = 15.0,
                 tmin_sec: float = 2.0, min_vehicles: int = 2,
                 enabled: bool = True):
        self.dmax = dmax
        self.hmax_deg = hmax_deg
        self.tmin_sec = tmin_sec
        self.min_vehicles = min_vehicles
        self.enabled = enabled
        self._pair_since: dict[tuple[int, int], float] = {}
        self._group_since: dict[frozenset, float] = {}
        self._next_id = 1
        self._known: dict[frozenset, int] = {}

    def _pos(self, tr, calibrated) -> tuple[float, float] | None:
        return getattr(tr, "world_xy", None) if calibrated else tr.centroid

    def update(self, tracks: list, timestamp: float, calibrated: bool) -> list[Group]:
        """tracks: TrackState list with optional .world_xy set by pipeline."""
        if not self.enabled:
            return []
        unit = "m" if calibrated else "px"
        dmax = self.dmax if calibrated else self.dmax  # pixel thresholds configured by operator

        # candidate pairs
        pairs: set[tuple[int, int]] = set()
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                a, b = tracks[i], tracks[j]
                pa, pb = self._pos(a, calibrated), self._pos(b, calibrated)
                if pa is None or pb is None:
                    continue
                if pixel_distance(pa, pb) > dmax:
                    continue
                if a.heading is None or b.heading is None:
                    continue
                if angle_between(a.heading, b.heading) > self.hmax_deg:
                    continue
                pairs.add((min(a.id, b.id), max(a.id, b.id)))

        now_pairs = set()
        for p in pairs:
            self._pair_since.setdefault(p, timestamp)
            if timestamp - self._pair_since[p] >= self.tmin_sec:
                now_pairs.add(p)
        # drop stale pairs
        for p in list(self._pair_since):
            if p not in pairs:
                del self._pair_since[p]

        # connected components over persistent pairs
        parent: dict[int, int] = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for a, b in now_pairs:
            union(a, b)
        comps: dict[int, set[int]] = {}
        for a, b in now_pairs:
            r = find(a)
            comps.setdefault(r, set()).update((a, b))
        by_id = {t.id: t for t in tracks}
        groups: list[Group] = []
        for members in comps.values():
            if len(members) < self.min_vehicles:
                continue
            key = frozenset(members)
            self._group_since.setdefault(key, timestamp)
            gid = self._known.setdefault(key, self._next_id)
            if gid == self._next_id:
                self._next_id += 1
            mlist = sorted(members)
            speeds = [by_id[i].speed for i in mlist
                      if i in by_id and by_id[i].speed is not None]
            headings = [by_id[i].heading for i in mlist
                        if i in by_id and by_id[i].heading is not None]
            # avg spacing: sort along mean heading, consecutive distances
            pts = [self._pos(by_id[i], calibrated) for i in mlist if i in by_id]
            pts = [p for p in pts if p is not None]
            avg_spacing = None
            if len(pts) >= 2:
                ang = math.radians(sum(headings) / len(headings)) if headings else 0.0
                dx, dy = math.cos(ang), math.sin(ang)
                order = sorted(pts, key=lambda p: p[0] * dx + p[1] * dy)
                dists = [pixel_distance(order[k], order[k + 1]) for k in range(len(order) - 1)]
                avg_spacing = sum(dists) / len(dists)
            groups.append(Group(
                id=gid, member_ids=mlist,
                avg_speed=sum(speeds) / len(speeds) if speeds else None,
                avg_spacing=avg_spacing,
                direction_deg=(sum(headings) / len(headings)) if headings else None,
                duration_s=timestamp - self._group_since[key],
                unit=unit,
            ))
        # forget dissolved groups
        for key in list(self._group_since):
            if all(key != frozenset(g.member_ids) for g in groups):
                self._group_since.pop(key, None)
        return groups

    def reset(self) -> None:
        self._pair_since.clear()
        self._group_since.clear()
        self._known.clear()
        self._next_id = 1
