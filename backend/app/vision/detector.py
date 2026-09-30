"""Vehicle detector abstraction.

Real detection is done by :class:`YOLODetector` (Ultralytics YOLO-compatible).
If the library or the weights file is missing the backend keeps running and
reports MODEL NOT AVAILABLE honestly — it never fabricates detections.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from app import config

log = logging.getLogger("ctas.detector")

# COCO ids -> CTAS vehicle classes
VEHICLE_CLASS_MAP = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
CLASS_COLORS = {  # BGR for OpenCV drawing
    "car": (60, 180, 255),
    "truck": (60, 60, 230),
    "bus": (200, 120, 40),
    "van": (40, 200, 160),
    "motorcycle": (200, 60, 200),
    "bicycle": (60, 220, 120),
    "other": (160, 160, 160),
}


class ModelNotAvailable(RuntimeError):
    """Raised when no usable detection model is present."""


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


@dataclass
class DetectorBase:
    model_path: Path = field(default_factory=lambda: config.MODEL_PATH)
    device: str = "cpu"
    imgsz: int = 640
    conf: float = 0.35
    iou: float = 0.45
    loaded: bool = False
    last_latency_ms: float = 0.0

    def load(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def predict(self, frame: np.ndarray) -> list[Detection]:  # pragma: no cover
        raise NotImplementedError

    def warmup(self, shape=(640, 640, 3)) -> None:
        try:
            self.predict(np.zeros(shape, dtype=np.uint8))
        except Exception as exc:  # noqa: BLE001
            log.warning("detector warmup failed: %s", exc)


class NullDetector(DetectorBase):
    """Fallback used when no model is available: returns zero detections."""

    def load(self) -> None:
        self.loaded = False
        log.warning("No detection model available — detector disabled (MODEL NOT AVAILABLE).")

    def predict(self, frame: np.ndarray) -> list[Detection]:
        return []


class YOLODetector(DetectorBase):
    """Ultralytics YOLO-compatible detector adapter."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._model = None

    def load(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:
            raise ModelNotAvailable(
                "ultralytics is not installed. Install it with "
                "`pip install ultralytics` (requires PyTorch) or place a model "
                "at models/default_model.pt and install the dependency."
            ) from exc
        if not self.model_path.exists():
            raise ModelNotAvailable(
                f"Model file not found: {self.model_path}. "
                "Download yolov8n.pt into models/ and rename it to default_model.pt, "
                "or set CTAS_MODEL_PATH."
            )
        device = self.device
        if device == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    log.warning("CUDA requested but not available — falling back to CPU.")
                    device = "cpu"
            except ImportError:
                device = "cpu"
        if device == "mps":
            try:
                import torch
                if not torch.backends.mps.is_available():
                    device = "cpu"
            except ImportError:
                device = "cpu"
        self.device = device
        log.info("Loading YOLO model from %s on %s", self.model_path, device)
        self._model = YOLO(str(self.model_path))
        self.loaded = True

    def predict(self, frame: np.ndarray) -> list[Detection]:
        if not self.loaded or self._model is None:
            return []
        t0 = time.perf_counter()
        results = self._model.predict(
            frame, imgsz=self.imgsz, conf=self.conf, iou=self.iou,
            device=self.device, verbose=False,
        )
        out: list[Detection] = []
        for r in results:
            boxes = getattr(r, "boxes", None)
            if boxes is None:
                continue
            for b in boxes:
                cid = int(b.cls[0])
                if cid not in VEHICLE_CLASS_MAP:
                    continue
                xyxy = b.xyxy[0].tolist()
                out.append(Detection(
                    class_id=cid,
                    class_name=VEHICLE_CLASS_MAP[cid],
                    confidence=float(b.conf[0]),
                    bbox=[float(v) for v in xyxy],
                ))
        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
        return out


_detector: Optional[DetectorBase] = None


def get_detector(settings: dict | None = None) -> DetectorBase:
    """Return the shared detector, (re)built from settings when they change."""
    global _detector
    m = (settings or {}).get("model", {})
    key = (str(m.get("model_path", config.MODEL_PATH)), m.get("device", "cpu"),
           int(m.get("imgsz", 640)), float(m.get("conf", 0.35)), float(m.get("iou", 0.45)))
    current_key = getattr(_detector, "_cfg_key", None)
    if _detector is None or current_key != key:
        det: DetectorBase = YOLODetector(
            model_path=Path(m.get("model_path", config.MODEL_PATH)),
            device=m.get("device", "cpu"),
            imgsz=int(m.get("imgsz", 640)),
            conf=float(m.get("conf", 0.35)),
            iou=float(m.get("iou", 0.45)),
        )
        try:
            det.load()
        except ModelNotAvailable as exc:
            log.warning("%s", exc)
            det = NullDetector()
            det.load()
        det._cfg_key = key  # type: ignore[attr-defined]
        _detector = det
    return _detector


def get_detector_status() -> dict:
    d = _detector
    gpu = False
    try:
        import torch
        gpu = torch.cuda.is_available()
    except ImportError:
        pass
    return {
        "loaded": bool(d and d.loaded),
        "path": str(getattr(d, "model_path", config.MODEL_PATH)),
        "gpu_available": gpu,
        "latency_ms": round(getattr(d, "last_latency_ms", 0.0) or 0.0, 1),
    }
