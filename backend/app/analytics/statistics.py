"""Live statistics computed from the current tracking state."""
from __future__ import annotations

from collections import Counter


def class_counts(tracks: list) -> dict[str, int]:
    return dict(Counter(t.class_name for t in tracks))


def unique_session_count(all_track_ids: set[int]) -> int:
    return len(all_track_ids)


def average_speed(tracks: list) -> float | None:
    speeds = [t.speed for t in tracks if t.speed is not None]
    return sum(speeds) / len(speeds) if speeds else None


def track_durations(tracks: list) -> dict[int, float]:
    return {t.id: t.last_seen - t.first_seen for t in tracks}


def flow_rate(entered: int, elapsed_s: float) -> float:
    """Vehicles per hour entering the scene."""
    if elapsed_s <= 0:
        return 0.0
    return entered / elapsed_s * 3600.0
