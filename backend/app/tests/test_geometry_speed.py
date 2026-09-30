"""Geometry / calibration / speed / lane / spacing / group tests."""
import math

from app.vision.calibration import Calibration
from app.vision.geometry import apply_homography, compute_homography
from app.vision.group_analysis import GroupAnalyzer
from app.vision.lane_detection import LaneAnalyzer
from app.vision.speed import SpeedEstimator
from app.analytics.spacing import spacing_stats


def test_homography_identity_square():
    H = compute_homography([[0, 0], [10, 0], [10, 10], [0, 10]],
                           [[0, 0], [10, 0], [10, 10], [0, 10]])
    x, y = apply_homography(H, 4, 7)
    assert abs(x - 4) < 1e-3 and abs(y - 7) < 1e-3


def test_homography_scale():
    H = compute_homography([[0, 0], [100, 0], [100, 100], [0, 100]],
                           [[0, 0], [10, 0], [10, 10], [0, 10]])
    x, y = apply_homography(H, 50, 50)
    assert abs(x - 5) < 1e-3 and abs(y - 5) < 1e-3


def test_calibration_not_calibrated_by_default():
    c = Calibration()
    assert not c.is_calibrated
    assert c.to_world(10, 10) is None


def test_speed_ema_and_kmh():
    se = SpeedEstimator(alpha=0.5)
    raw, smooth, unit = se.update(1, 0, 0, 0.0, calibrated=True)
    assert raw is None and unit == "km/h"
    raw, smooth, unit = se.update(1, 10, 0, 1.0, calibrated=True)  # 10 m in 1 s
    assert abs(raw - 36.0) < 1e-6  # 10 m/s = 36 km/h
    assert abs(smooth - 36.0) < 1e-6  # first EMA = raw


def test_speed_pixel_units_when_uncalibrated():
    se = SpeedEstimator()
    se.update(1, 0, 0, 0.0, calibrated=False)
    raw, smooth, unit = se.update(1, 30, 0, 1.0, calibrated=False)
    assert unit == "px/s" and abs(raw - 30.0) < 1e-6


def test_lane_assignment_and_change():
    la = LaneAnalyzer()
    la.set_lanes([
        {"id": "1", "name": "Lane 1", "polygon": [[0, 0], [50, 0], [50, 100], [0, 100]]},
        {"id": "2", "name": "Lane 2", "polygon": [[50, 0], [100, 0], [100, 100], [50, 100]]},
    ])
    lane, changed = la.lane_of_track(1, 25, 50)
    assert lane == "Lane 1" and not changed
    lane, changed = la.lane_of_track(1, 75, 50)
    assert lane == "Lane 2" and changed


class _T:
    def __init__(self, tid, x, y, heading, speed=None):
        self.id = tid
        self.centroid = (x, y)
        self.world_xy = None
        self.heading = heading
        self.speed = speed


def test_group_forms_with_proximity_and_heading():
    ga = GroupAnalyzer(dmax=60.0, hmax_deg=15.0, tmin_sec=0.5, min_vehicles=2)
    tracks = [_T(1, 100, 100, 0.0, 50.0), _T(2, 130, 105, 2.0, 52.0),
              _T(3, 500, 500, 90.0, 50.0)]
    assert ga.update(tracks, 0.0, calibrated=False) == []  # persistence not met
    groups = ga.update(tracks, 1.0, calibrated=False)
    assert len(groups) == 1
    assert sorted(groups[0].member_ids) == [1, 2]
    assert groups[0].unit == "px"


def test_spacing_stats():
    tracks = [_T(1, 0, 0, 0.0), _T(2, 10, 0, 0.0), _T(3, 30, 0, 0.0)]
    sp = spacing_stats(tracks, calibrated=True)
    assert sp["min"] == 10.0 and sp["max"] == 20.0
    assert abs(sp["mean"] - 15.0) < 1e-9 and sp["unit"] == "m"
