"""Clearly-marked synthetic demo source.

Produces a deterministic top-down traffic scene (moving rectangles) so the
full pipeline — detection adapter, tracking, analytics, events — can be
exercised without a model or camera. The UI always labels this
'DEMO / SYNTHETIC DATA' and it is never confused with real AI results.
"""
from __future__ import annotations

import math
import time

import cv2
import numpy as np

from app.streaming.video_reader import SourceInfo, VideoSource
from app.vision.detector import Detection


class DemoSource(VideoSource):
    kind = "demo"

    def __init__(self, width: int = 960, height: int = 540, n_vehicles: int = 14):
        self._info = SourceInfo(kind="demo", location="synthetic",
                                width=width, height=height, fps=25.0,
                                total_frames=0, is_live=True)
        self.n = n_vehicles
        self._t0 = time.time()
        self._frame_no = 0
        rng = np.random.default_rng(7)
        self._cars = []
        for i in range(n_vehicles):
            lane = i % 3
            self._cars.append({
                "x": float(rng.uniform(0, width)),
                "y": 120.0 + lane * 110.0 + float(rng.uniform(-15, 15)),
                "v": float(rng.uniform(120, 260)) * (1 if i % 2 == 0 else -1),
                "w": 46.0, "h": 26.0,
                "cls": str(rng.choice(["car", "car", "car", "truck", "bus", "motorcycle"])),
            })

    def open(self) -> SourceInfo:
        self._t0 = time.time()
        self._frame_no = 0
        return self._info

    def read(self):
        w, h = self._info.width, self._info.height
        frame = np.full((h, w, 3), (18, 26, 40), dtype=np.uint8)
        # road
        cv2.rectangle(frame, (0, 90), (w, 450), (38, 44, 58), -1)
        for y in (200, 310):
            for x in range(0, w, 60):
                cv2.rectangle(frame, (x, y - 3), (x + 34, y + 3), (150, 150, 150), -1)
        dt = 1.0 / self._info.fps
        self._detections: list[Detection] = []
        for c in self._cars:
            c["x"] += c["v"] * dt
            if c["x"] > w + 60:
                c["x"] = -60
            if c["x"] < -60:
                c["x"] = w + 60
            x1, y1 = c["x"] - c["w"] / 2, c["y"] - c["h"] / 2
            x2, y2 = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
            color = {"car": (60, 180, 255), "truck": (60, 60, 230),
                     "bus": (200, 120, 40), "motorcycle": (200, 60, 200)}[c["cls"]]
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, -1)
            self._detections.append(Detection(
                class_id=2, class_name=c["cls"], confidence=0.99,
                bbox=[x1, y1, x2, y2]))
        self._frame_no += 1
        return True, frame, time.time() - self._t0

    @property
    def info(self):
        return self._info
