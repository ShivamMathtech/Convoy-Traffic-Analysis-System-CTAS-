"""Video upload / listing API with strict file validation."""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
from fastapi import APIRouter, File, HTTPException, UploadFile

from app import config
from app.utils.helpers import safe_filename

log = logging.getLogger("ctas.api.videos")
router = APIRouter()


def _probe(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"ok": False}
    meta = {
        "ok": True,
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": round(float(cap.get(cv2.CAP_PROP_FPS) or 0), 2),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
    }
    cap.release()
    if meta["frames"]:
        meta["duration_s"] = round(meta["frames"] / max(meta["fps"], 1e-6), 1)
    return meta


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in config.ALLOWED_VIDEO_EXTS and ext not in config.ALLOWED_IMAGE_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. "
                                 f"Allowed: {sorted(config.ALLOWED_VIDEO_EXTS | config.ALLOWED_IMAGE_EXTS)}")
    internal = safe_filename(file.filename or "upload")
    dest = config.UPLOAD_DIR / internal
    size = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > config.MAX_UPLOAD_MB * 1024 * 1024:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {config.MAX_UPLOAD_MB} MB limit")
            f.write(chunk)
    meta = _probe(dest)
    if ext in config.ALLOWED_VIDEO_EXTS and not meta.get("ok"):
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded video could not be decoded (unsupported or corrupted)")
    log.info("Uploaded %s -> %s (%d bytes)", file.filename, internal, size)
    return {"id": internal, "filename": file.filename, "stored_as": internal,
            "size_bytes": size, "path": str(dest), **meta}


@router.get("")
def list_videos():
    items = []
    for p in sorted(config.UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if p.suffix.lower() in config.ALLOWED_VIDEO_EXTS | config.ALLOWED_IMAGE_EXTS:
            items.append({"id": p.name, "filename": p.name,
                          "size_bytes": p.stat().st_size,
                          "path": str(p), **_probe(p)})
    return {"videos": items}


@router.get("/{video_id}")
def video_info(video_id: str):
    p = config.UPLOAD_DIR / Path(video_id).name  # prevent traversal
    if not p.exists():
        raise HTTPException(404, "Video not found")
    return {"id": p.name, "path": str(p), **_probe(p)}
