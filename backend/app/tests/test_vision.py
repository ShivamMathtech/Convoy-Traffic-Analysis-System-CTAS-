"""Vision tests: synthetic video write/read, detector adapter honesty,
frame buffer bounds."""
import numpy as np

from app.streaming.frame_buffer import FrameBuffer
from app.streaming.video_reader import FileVideoSource
from app.vision.detector import NullDetector, YOLODetector, ModelNotAvailable


def test_synthetic_video_roundtrip(tmp_path):
    import cv2
    p = tmp_path / "syn.mp4"
    w = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    for i in range(12):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        cv2.rectangle(frame, (10 + i * 5, 40), (50 + i * 5, 80), (255, 255, 255), -1)
        w.write(frame)
    w.release()

    src = FileVideoSource(p)
    info = src.open()
    assert info.total_frames == 12
    assert info.width == 160 and info.height == 120
    n = 0
    while True:
        ok, frame, ts = src.read()
        if not ok:
            break
        n += 1
        assert frame.shape == (120, 160, 3)
    assert n == 12
    src.release()


def test_null_detector_returns_zero_detections():
    det = NullDetector()
    det.load()
    assert det.loaded is False
    assert det.predict(np.zeros((64, 64, 3), dtype=np.uint8)) == []


def test_yolo_detector_missing_model_raises_honestly(tmp_path):
    det = YOLODetector(model_path=tmp_path / "nope.pt")
    try:
        det.load()
    except ModelNotAvailable as exc:
        assert "not found" in str(exc).lower() or "not installed" in str(exc).lower()
    else:
        # ultralytics installed AND model resolved — must still not crash
        assert det.predict(np.zeros((64, 64, 3), dtype=np.uint8)) == []


def test_frame_buffer_bounded():
    buf = FrameBuffer(maxsize=3)
    for i in range(10):
        buf.put_latest(i)
    assert buf.qsize() == 3
    # latest-frame semantics: the newest items survive
    got = [buf.get(timeout=0.1) for _ in range(3)]
    assert got[-1] == 9
