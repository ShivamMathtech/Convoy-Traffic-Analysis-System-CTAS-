"""Stream test & camera enumeration API."""
from __future__ import annotations

import cv2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.dto import StreamTestRequest
from app.streaming.video_reader import enumerate_cameras
from app.utils.helpers import mask_url_secret

router = APIRouter()


@router.post("/test")
def test_stream(req: StreamTestRequest):
    cap = cv2.VideoCapture(req.url, cv2.CAP_FFMPEG if req.kind == "rtsp" else cv2.CAP_ANY)
    opened = cap.isOpened()
    info = {}
    if opened:
        ok, frame = cap.read()
        info = {
            "opened": True,
            "got_frame": bool(ok and frame is not None),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
        }
    cap.release()
    if not opened:
        raise HTTPException(400, f"Could not connect to {req.kind.upper()} stream: "
                                 f"{mask_url_secret(req.url)}")
    return {"reachable": True, "url": mask_url_secret(req.url), **info}


@router.get("/cameras")
def list_cameras():
    return {"cameras": enumerate_cameras()}


class SnapshotBody(BaseModel):
    session_id: str


@router.post("/snapshot-test")
def snapshot_probe(body: SnapshotBody):
    from app.services.session_manager import manager
    p = manager.get_pipeline(body.session_id)
    if not p:
        raise HTTPException(404, "Session not found")
    jpg = p.latest_jpeg()
    return {"has_frame": jpg is not None, "bytes": len(jpg) if jpg else 0}
