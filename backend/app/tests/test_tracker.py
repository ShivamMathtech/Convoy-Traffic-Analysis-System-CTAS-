"""Tracker tests: ID persistence, confirmation, expiry, ByteTrack two-stage."""
from app.vision.detector import Detection
from app.vision.tracker import BoTSORTAdapter, ByteTrackAdapter


def _det(x, conf=0.9, cls="car"):
    return Detection(class_id=2, class_name=cls, confidence=conf,
                     bbox=[x, 100.0, x + 40.0, 140.0])


def test_track_persists_across_frames():
    tr = ByteTrackAdapter(max_age=5, min_hits=2)
    t1 = tr.update([_det(10)], timestamp=0.0)
    assert t1 == []  # not confirmed yet (min_hits=2)
    t2 = tr.update([_det(14)], timestamp=0.1)
    assert len(t2) == 1
    first_id = t2[0].id
    t3 = tr.update([_det(18)], timestamp=0.2)
    assert t3[0].id == first_id  # ID persisted


def test_track_expires_after_max_age():
    tr = ByteTrackAdapter(max_age=2, min_hits=1)
    tr.update([_det(10)], timestamp=0.0)
    tr.update([], timestamp=0.1)
    tr.update([], timestamp=0.2)
    tr.update([], timestamp=0.3)
    assert tr.active_tracks() == []


def test_bytetrack_second_stage_recovers_low_conf():
    tr = ByteTrackAdapter(max_age=5, min_hits=1, low_conf_threshold=0.1)
    tr.update([_det(10, conf=0.9)], timestamp=0.0)
    tid = tr.active_tracks()[0].id
    # next frame: only a low-confidence detection at the same spot
    out = tr.update([_det(12, conf=0.15)], timestamp=0.1)
    assert out and out[0].id == tid


def test_botsort_predicts_motion():
    tr = BoTSORTAdapter(max_age=5, min_hits=1)
    tr.update([_det(10)], timestamp=0.0)
    tr.update([_det(30)], timestamp=0.1)   # velocity +200 px/s
    state = tr.tracks[0]
    assert state.velocity[0] > 0
    assert state.heading is not None


def test_counting_no_double_count():
    tr = ByteTrackAdapter(max_age=10, min_hits=1)
    seen = set()
    for i in range(6):
        out = tr.update([_det(10 + i * 4), _det(300 - i * 4)], timestamp=i * 0.1)
        seen.update(t.id for t in out)
    assert seen == {1, 2}  # exactly two unique vehicles
