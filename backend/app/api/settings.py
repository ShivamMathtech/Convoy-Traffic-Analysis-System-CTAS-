"""Settings + system performance API."""
from __future__ import annotations

import shutil

import psutil
from fastapi import APIRouter
from pydantic import BaseModel

from app import config
from app.services import settings_store
from app.vision.detector import get_detector_status

router = APIRouter()


class SettingsPatch(BaseModel):
    patch: dict


@router.get("")
def get_settings():
    return settings_store.load_settings()


@router.put("")
def update_settings(body: SettingsPatch):
    return {"ok": True, "settings": settings_store.save_settings(body.patch)}


@router.get("/performance")
def performance():
    vm = psutil.virtual_memory()
    du = shutil.disk_usage(config.STORAGE_DIR)
    gpu = {"available": False}
    try:
        import torch
        if torch.cuda.is_available():
            gpu = {"available": True,
                   "name": torch.cuda.get_device_name(0),
                   "vram_used_mb": round(torch.cuda.memory_allocated() / 1e6, 1),
                   "vram_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 1e6, 1)}
    except ImportError:
        pass
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / 1e9, 2),
        "disk_free_gb": round(du.free / 1e9, 2),
        "gpu": gpu,
        "detector": get_detector_status(),
    }


@router.get("/model")
def model_info():
    st = get_detector_status()
    return {
        "path": st["path"],
        "loaded": st["loaded"],
        "expected_path": str(config.MODEL_PATH),
        "hint": ("Place yolov8n.pt (renamed to default_model.pt) in CTAS/models/ "
                 "and install ultralytics to enable real detection." if not st["loaded"]
                 else "Model ready."),
    }
