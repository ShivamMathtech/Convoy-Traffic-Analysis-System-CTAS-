"""Video source abstraction.

Covers file videos, image sequences / single images, local cameras, RTSP and
HTTP/MJPEG streams. Live sources reconnect with bounded exponential backoff
and surface StreamInterrupted / CameraReconnected events instead of dying.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app.utils.helpers import mask_url_secret

log = logging.getLogger("ctas.source")


@dataclass
class SourceInfo:
    kind: str
    location: str
    width: int = 0
    height: int = 0
    fps: float = 30.0
    total_frames: int = 0
    is_live: bool = False


class VideoSource:
    kind = "base"

    def open(self) -> SourceInfo:
        raise NotImplementedError

    def read(self) -> tuple[bool, np.ndarray | None, float]:
        """Return (ok, frame_bgr, timestamp_seconds)."""
        raise NotImplementedError

    def release(self) -> None:
        pass

    @property
    def info(self) -> SourceInfo:
        raise NotImplementedError


class FileVideoSource(VideoSource):
    kind = "video"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.cap: cv2.VideoCapture | None = None
        self._info = SourceInfo(kind="video", location=str(self.path))
        self._t0 = time.time()

    def open(self) -> SourceInfo:
        if not self.path.exists():
            raise FileNotFoundError(f"Video file not found: {self.path}")
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video (unsupported or corrupted): {self.path}")
        self._info.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._info.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._info.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
        self._info.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._t0 = time.time()
        log.info("Opened video %s (%dx%d @ %.1f fps, %d frames)",
                 self.path.name, self._info.width, self._info.height,
                 self._info.fps, self._info.total_frames)
        return self._info

    def read(self):
        assert self.cap is not None
        ok, frame = self.cap.read()
        if not ok:
            return False, None, 0.0
        pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        ts = pos / max(self._info.fps, 1e-6)
        return True, frame, ts

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    @property
    def info(self):
        return self._info


class ImageFileSource(FileVideoSource):
    kind = "image"

    def open(self) -> SourceInfo:
        img = cv2.imread(str(self.path))
        if img is None:
            raise RuntimeError(f"Could not read image: {self.path}")
        h, w = img.shape[:2]
        self._frame = img
        self._done = False
        self._info.width, self._info.height = w, h
        self._info.fps, self._info.total_frames = 1.0, 1
        return self._info

    def read(self):
        if self._done:
            return False, None, 0.0
        self._done = True
        return True, self._frame, 0.0


class ImageDirSource(VideoSource):
    kind = "image_dir"
    EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self._files: list[Path] = []
        self._idx = 0
        self._info = SourceInfo(kind="image_dir", location=str(self.directory))

    def open(self) -> SourceInfo:
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.directory}")
        self._files = sorted(p for p in self.directory.iterdir()
                             if p.suffix.lower() in self.EXTS)
        if not self._files:
            raise RuntimeError(f"No images found in {self.directory}")
        img = cv2.imread(str(self._files[0]))
        h, w = img.shape[:2]
        self._info.width, self._info.height = w, h
        self._info.fps, self._info.total_frames = 5.0, len(self._files)
        self._idx = 0
        return self._info

    def read(self):
        if self._idx >= len(self._files):
            return False, None, 0.0
        img = cv2.imread(str(self._files[self._idx]))
        ts = self._idx / max(self._info.fps, 1e-6)
        self._idx += 1
        return (img is not None), img, ts

    @property
    def info(self):
        return self._info


class _LiveSource(VideoSource):
    """Shared reconnect/backoff logic for camera & network streams."""

    def __init__(self, location: str, kind: str, is_live: bool = True):
        self.location = location
        self.kind = kind
        self.cap: cv2.VideoCapture | None = None
        self._info = SourceInfo(kind=kind, location=mask_url_secret(location), is_live=is_live)
        self._t0 = time.time()
        self.interrupted = False

    def _connect(self) -> bool:
        raise NotImplementedError

    def open(self) -> SourceInfo:
        if not self._connect():
            raise RuntimeError(f"Could not open {self.kind} source: {mask_url_secret(self.location)}")
        self._t0 = time.time()
        return self._info

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            self.interrupted = True
            if not self._reconnect():
                return False, None, time.time() - self._t0
            self.interrupted = False
        ok, frame = self.cap.read()
        if not ok or frame is None:
            self.interrupted = True
            log.warning("%s stream interrupted, reconnecting…", self.kind)
            if not self._reconnect():
                return False, None, time.time() - self._t0
            ok, frame = self.cap.read()
            if not ok or frame is None:
                return False, None, time.time() - self._t0
        return True, frame, time.time() - self._t0

    def _reconnect(self) -> bool:
        delay = 1.0
        for attempt in range(5):  # bounded exponential backoff: 1,2,4,8,16s
            log.info("Reconnect attempt %d for %s in %.0fs", attempt + 1, self.kind, delay)
            time.sleep(delay)
            try:
                if self.cap is not None:
                    self.cap.release()
                if self._connect():
                    log.info("%s reconnected", self.kind)
                    return True
            except Exception as exc:  # noqa: BLE001
                log.warning("Reconnect failed: %s", exc)
            delay = min(delay * 2, 16.0)
        return False

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    @property
    def info(self):
        return self._info


class CameraSource(_LiveSource):
    kind = "webcam"

    def __init__(self, index: int = 0):
        super().__init__(str(index), kind="webcam")

    def _connect(self) -> bool:
        self.cap = cv2.VideoCapture(int(self.location))
        if not self.cap.isOpened():
            return False
        self._info.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        self._info.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
        self._info.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
        return True


class RTSPStreamSource(_LiveSource):
    kind = "rtsp"

    def __init__(self, url: str):
        super().__init__(url, kind="rtsp")

    def _connect(self) -> bool:
        self.cap = cv2.VideoCapture(self.location, cv2.CAP_FFMPEG)
        ok = self.cap.isOpened()
        if ok:
            self._info.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            self._info.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            self._info.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 25.0)
        return ok


class HTTPStreamSource(_LiveSource):
    kind = "http"

    def __init__(self, url: str):
        super().__init__(url, kind="http")

    def _connect(self) -> bool:
        self.cap = cv2.VideoCapture(self.location)
        ok = self.cap.isOpened()
        if ok:
            self._info.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            self._info.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            self._info.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 25.0)
        return ok


def enumerate_cameras(max_index: int = 6) -> list[dict]:
    """Probe camera indices; returns the ones that actually open."""
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            found.append({"index": i, "label": f"Camera {i} ({w}x{h})", "width": w, "height": h})
        cap.release()
    return found


def create_source(source_type: str, location: str) -> VideoSource:
    st = source_type.lower()
    if st in ("upload", "video"):
        return FileVideoSource(location)
    if st == "image":
        return ImageFileSource(location)
    if st == "image_dir":
        return ImageDirSource(location)
    if st in ("webcam", "usb"):
        return CameraSource(int(location or 0))
    if st == "rtsp":
        return RTSPStreamSource(location)
    if st == "http":
        return HTTPStreamSource(location)
    if st == "demo":
        from app.streaming.demo import DemoSource  # local import, optional
        return DemoSource()
    raise ValueError(f"Unknown source type: {source_type}")
