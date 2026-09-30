"""Perspective calibration store.

The operator picks 4 image reference points and the corresponding ground
coordinates; we solve the homography H once and reuse it for distance,
spacing and speed. Without calibration every metric is honestly reported
in pixels and the UI labels units as pixels.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from app.vision.geometry import apply_homography, compute_homography

log = logging.getLogger("ctas.calibration")


@dataclass
class Calibration:
    image_points: list[list[float]] = field(default_factory=list)
    world_points: list[list[float]] = field(default_factory=list)
    units: str = "pixels"                       # pixels | meters
    H: np.ndarray | None = None

    @property
    def is_calibrated(self) -> bool:
        return self.H is not None and self.units == "meters"

    def set_points(self, image_points, world_points, units: str = "meters") -> None:
        self.H = compute_homography(image_points, world_points)
        self.image_points = [list(map(float, p)) for p in image_points]
        self.world_points = [list(map(float, p)) for p in world_points]
        self.units = units
        log.info("Calibration set: units=%s", units)

    def to_world(self, u: float, v: float) -> tuple[float, float] | None:
        if not self.is_calibrated or self.H is None:
            return None
        try:
            return apply_homography(self.H, u, v)
        except ValueError:
            return None

    def clear(self) -> None:
        self.H = None
        self.image_points = []
        self.world_points = []
        self.units = "pixels"

    def as_dict(self) -> dict:
        return {
            "image_points": self.image_points,
            "world_points": self.world_points,
            "units": self.units,
            "homography": None if self.H is None else self.H.tolist(),
            "is_calibrated": self.is_calibrated,
        }
