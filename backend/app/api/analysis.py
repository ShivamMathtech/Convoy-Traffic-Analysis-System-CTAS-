"""Analysis control API + realtime WebSocket + MJPEG stream."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse

from app import config
from app.schemas.dto import AnalysisStartRequest, CalibrationRequest, LaneRequest
from app.services import settings_store
from app.services.session_manager import manager
from app.streaming.websocket import manager_ws

log = logging.getLogger("ctas.api.analysis")
router = APIRouter()


@router.post("/start")
def start_analysis(req: AnalysisStartRequest):
    settings = settings_store.load_settings()
    # deep-merge user overrides for this run
    from app.services.settings_store import _deep_merge
    settings = _deep_merge(settings, req.settings_override or {})
    location = req.location
    if req.source_type in ("upload", "video", "image"):
        # resolve upload id -> real path
        candidate = config.UPLOAD_DIR / location
        if candidate.exists():
            location = str(candidate)
    try:
        session_id = manager.start_analysis(req.source_type, location, req.name, settings)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc))
    return {"session_id": session_id, "status": manager.status(session_id)}


@router.post("/{session_id}/pause")
def pause(session_id: str):
    try:
        manager.pause(session_id)
    except KeyError:
        raise HTTPException(404, "Session not found")
    return {"ok": True, "status": manager.status(session_id)}


@router.post("/{session_id}/resume")
def resume(session_id: str):
    try:
        manager.resume(session_id)
    except KeyError:
        raise HTTPException(404, "Session not found")
    return {"ok": True, "status": manager.status(session_id)}


@router.post("/{session_id}/stop")
def stop(session_id: str):
    try:
        final = manager.stop(session_id)
    except KeyError:
        raise HTTPException(404, "Session not found")
    return {"ok": True, "status": final,
            "outputs": f"/storage/outputs/{session_id}/"}


@router.get("/{session_id}/status")
def status(session_id: str):
    try:
        return manager.status(session_id)
    except KeyError:
        raise HTTPException(404, "Session not found")


@router.post("/calibration")
def set_calibration(req: CalibrationRequest):
    try:
        result = manager.set_calibration(req.session_id, req.image_points,
                                         req.world_points, req.units)
    except KeyError:
        raise HTTPException(404, "Session not found (start analysis first)")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return result


@router.post("/lanes")
def set_lanes(req: LaneRequest):
    try:
        return manager.set_lanes(req.session_id, req.lanes)
    except KeyError:
        raise HTTPException(404, "Session not found (start analysis first)")


@router.get("/{session_id}/snapshot")
def snapshot(session_id: str):
    p = manager.get_pipeline(session_id)
    if not p:
        raise HTTPException(404, "Session not found")
    jpg = p.latest_jpeg()
    if not jpg:
        raise HTTPException(409, "No frame available yet")
    dest = config.REPORT_DIR / f"{session_id}_{int(time.time())}.jpg"
    dest.write_bytes(jpg)
    return {"ok": True, "path": f"/storage/reports/{dest.name}"}


@router.get("/{session_id}/stream")
def mjpeg_stream(session_id: str):
    p = manager.get_pipeline(session_id)
    if not p:
        raise HTTPException(404, "Session not found")

    def gen():
        while True:
            jpg = p.latest_jpeg()
            if jpg:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            time.sleep(1 / 25)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.websocket("/ws/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str):
    await manager_ws.connect(session_id, websocket)
    try:
        while True:
            # keepalive + allow client pings; broadcasts come from the pipeline
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager_ws.disconnect(session_id, websocket)
