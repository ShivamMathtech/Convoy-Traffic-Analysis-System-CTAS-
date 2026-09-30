"""Central configuration for CTAS backend.

All tunables come from environment variables with sane defaults so the
application boots with zero configuration. Secrets live in the environment,
never in code.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- roots
BACKEND_DIR = Path(__file__).resolve().parents[2]          # .../CTAS/backend
ROOT_DIR = BACKEND_DIR.parent                              # .../CTAS

STORAGE_DIR = Path(os.getenv("CTAS_STORAGE_DIR", BACKEND_DIR / "storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
SESSION_DIR = STORAGE_DIR / "sessions"
REPORT_DIR = STORAGE_DIR / "reports"
THUMB_DIR = STORAGE_DIR / "thumbnails"
for _d in (UPLOAD_DIR, OUTPUT_DIR, SESSION_DIR, REPORT_DIR, THUMB_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ db
DATABASE_URL = os.getenv("CTAS_DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'ctas.db'}")

# ---------------------------------------------------------------- model
MODEL_PATH = Path(os.getenv("CTAS_MODEL_PATH", ROOT_DIR / "models" / "default_model.pt"))

# --------------------------------------------------------------- upload
MAX_UPLOAD_MB = int(os.getenv("CTAS_MAX_UPLOAD_MB", "1024"))
ALLOWED_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

VERSION = "1.0.0"
APP_NAME = "Convoy & Traffic Analysis System"

# ------------------------------------------------------------- defaults
DEFAULT_SETTINGS: dict = {
    "model": {
        "model_path": str(MODEL_PATH),
        "device": "cpu",            # cpu | cuda | mps
        "imgsz": 640,               # 320/416/512/640/768/960
        "conf": 0.35,
        "iou": 0.45,
    },
    "tracker": {
        "name": "bytetrack",        # bytetrack | botsort
        "max_age": 30,              # frames a track survives without match
        "min_hits": 3,              # detections before a track is confirmed
        "iou_threshold": 0.3,
        "low_conf_threshold": 0.1,  # ByteTrack second-stage association
    },
    "video": {
        "mode": "realtime",         # realtime | accurate | fast
        "frame_interval": 1,        # process every Nth frame (fast mode)
        "max_width": 1280,
    },
    "calibration": {
        "units": "pixels",          # pixels | meters
        "image_points": [],         # [[u,v]x4]
        "world_points": [],         # [[X,Y]x4]
    },
    "groups": {
        "dmax": 35.0,               # meters when calibrated, else pixels
        "hmax_deg": 15.0,
        "tmin_sec": 2.0,
        "min_vehicles": 2,
        "enabled": True,
    },
    "events": {
        "stopped_speed_kmh": 2.0,
        "stopped_seconds": 3.0,
        "spacing_warn_m": 5.0,
        "congestion_density": 25,   # vehicles in frame
        "congestion_seconds": 10.0,
        "enabled": {
            "vehicle_entered": True,
            "vehicle_exited": True,
            "lane_change": True,
            "group_formation": True,
            "stopped_vehicle": True,
            "spacing_threshold": True,
            "congestion": True,
            "stream": True,
        },
    },
    "storage": {
        "output_dir": str(OUTPUT_DIR),
        "auto_cleanup_days": 30,
    },
    "ui": {
        "show_trajectories": True,
        "trajectory_seconds": 5.0,
        "show_labels": True,
        "show_confidence": True,
        "chart_refresh_ms": 1000,
    },
}
