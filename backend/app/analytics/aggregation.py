"""Per-second analytics aggregation feeding charts and snapshots."""
from __future__ import annotations

from collections import defaultdict

from app.analytics import spacing as spacing_mod
from app.analytics import statistics as stats_mod


class AnalyticsAggregator:
    def __init__(self):
        self.series: dict[str, list] = defaultdict(list)  # key -> [(t, value)]
        self.class_series: dict[str, list] = defaultdict(list)
        self._last_bucket: float | None = None
        self._entered_total = 0

    def update(self, timestamp: float, tracks: list, calibrated: bool,
               groups: list, entered_now: int) -> dict:
        bucket = int(timestamp)
        self._entered_total += entered_now
        snapshot = None
        if self._last_bucket is None or bucket != self._last_bucket:
            self._last_bucket = bucket
            counts = stats_mod.class_counts(tracks)
            sp = spacing_mod.spacing_stats(tracks, calibrated)
            snapshot = {
                "t": float(bucket),
                "vehicle_count": len(tracks),
                "class_counts": counts,
                "average_speed": stats_mod.average_speed(tracks),
                "average_spacing": sp["mean"],
                "spacing_unit": sp["unit"],
                "group_count": len(groups),
            }
            self.series["vehicle_count"].append((float(bucket), len(tracks)))
            self.series["average_speed"].append((float(bucket), snapshot["average_speed"]))
            self.series["average_spacing"].append((float(bucket), snapshot["average_spacing"]))
            self.series["group_count"].append((float(bucket), len(groups)))
            for cls, n in counts.items():
                self.class_series[cls].append((float(bucket), n))
        return snapshot or {}

    def chart_payload(self) -> dict:
        def ser(key):
            return [{"t": t, "v": v} for t, v in self.series[key]]
        return {
            "vehicle_count_over_time": ser("vehicle_count"),
            "average_speed_over_time": ser("average_speed"),
            "spacing_over_time": ser("spacing_over_time") if "spacing_over_time" in self.series else
                                 [{"t": t, "v": v} for t, v in self.series["average_spacing"]],
            "group_count_over_time": ser("group_count"),
            "class_counts_over_time": {
                cls: [{"t": t, "v": v} for t, v in pts]
                for cls, pts in self.class_series.items()
            },
            "total_entered": self._entered_total,
        }

    def reset(self) -> None:
        self.series.clear()
        self.class_series.clear()
        self._last_bucket = None
        self._entered_total = 0
