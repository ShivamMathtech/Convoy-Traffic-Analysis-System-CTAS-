"""Perspective geometry: homography between image pixels and the road plane.

s * [X, Y, 1]^T = H * [u, v, 1]^T
"""
from __future__ import annotations

import numpy as np


def compute_homography(image_points: list[list[float]],
                       world_points: list[list[float]]) -> np.ndarray:
    """Compute 3x3 homography mapping image (u,v) -> world (X,Y).

    Requires exactly 4 point pairs (uses getPerspectiveTransform) or more
    (uses findHomography with RANSAC).
    """
    import cv2
    src = np.asarray(image_points, dtype=np.float32)
    dst = np.asarray(world_points, dtype=np.float32)
    if src.shape != (4, 2) or dst.shape != (4, 2):
        if len(src) < 4:
            raise ValueError("Need at least 4 point correspondences.")
        H, _ = cv2.findHomography(src, dst, cv2.RANSAC)
        if H is None:
            raise ValueError("Could not compute homography from the given points.")
        return H
    return cv2.getPerspectiveTransform(src, dst)


def apply_homography(H: np.ndarray, u: float, v: float) -> tuple[float, float]:
    p = H @ np.array([u, v, 1.0], dtype=float)
    if abs(p[2]) < 1e-9:
        raise ValueError("Degenerate homography (w ~ 0).")
    return float(p[0] / p[2]), float(p[1] / p[2])


def pixel_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def angle_between(h1: float, h2: float) -> float:
    """Smallest absolute heading difference in degrees."""
    d = abs(h1 - h2) % 360.0
    return d if d <= 180 else 360.0 - d
