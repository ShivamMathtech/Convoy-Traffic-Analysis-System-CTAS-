"""Annotation renderer: boxes, track IDs, labels, trajectories."""
from __future__ import annotations

import cv2
import numpy as np

from app.vision.detector import CLASS_COLORS


def draw_tracks(frame, tracks, show_trajectories: bool = True,
                trajectory_seconds: float = 5.0, show_labels: bool = True,
                show_confidence: bool = True, now: float = 0.0):
    out = frame
    for tr in tracks:
        x1, y1, x2, y2 = [int(v) for v in tr.bbox]
        color = CLASS_COLORS.get(tr.class_name, CLASS_COLORS["other"])
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        if show_trajectories and tr.history:
            pts = [(int(x), int(y)) for x, y, t in tr.history
                   if now - t <= trajectory_seconds]
            for i in range(1, len(pts)):
                cv2.line(out, pts[i - 1], pts[i], color, 2)
        if show_labels:
            label = f"ID {tr.id} {tr.class_name}"
            if show_confidence:
                label += f" {tr.confidence:.2f}"
            if tr.speed is not None:
                unit = getattr(tr, "speed_unit", "")
                label += f" {tr.speed:.1f}{unit}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
            cv2.putText(out, label, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 1, cv2.LINE_AA)
    return out


def draw_lanes(frame, lanes) -> None:
    for lane in lanes:
        pts = np.asarray(lane.polygon, dtype=np.int32)
        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
        if lane.polygon:
            x, y = int(lane.polygon[0][0]) + 6, int(lane.polygon[0][1]) + 20
            cv2.putText(frame, lane.name, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)


def draw_banner(frame, text: str) -> None:
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.rectangle(frame, (10, 10), (20 + tw, 24 + th), (0, 0, 0), -1)
    cv2.putText(frame, text, (15, 18 + th),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2, cv2.LINE_AA)
