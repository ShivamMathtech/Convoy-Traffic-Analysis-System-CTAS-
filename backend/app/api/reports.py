"""Report generation & download API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import config
from app.reports.generator import generate_json_summary, generate_pdf

router = APIRouter()


@router.post("/{session_id}")
def build_report(session_id: str):
    out_dir = config.OUTPUT_DIR / session_id
    if not out_dir.exists():
        raise HTTPException(404, "Session outputs not found — run analysis first")
    try:
        pdf = generate_pdf(session_id, out_dir)
        js = generate_json_summary(session_id, out_dir)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Report generation failed: {exc}")
    return {"ok": True,
            "pdf": f"/storage/outputs/{session_id}/report.pdf",
            "json": f"/storage/outputs/{session_id}/report.json",
            "files": [f.name for f in out_dir.iterdir()]}


@router.get("/{session_id}/download")
def download_report(session_id: str, fmt: str = "pdf"):
    out_dir = config.OUTPUT_DIR / session_id
    mapping = {"pdf": "report.pdf", "json": "report.json",
               "detections": "detections.csv", "tracks": "tracks.csv",
               "trajectories": "trajectories.csv", "events": "events.csv",
               "analytics": "analytics.csv", "video": "annotated_video.mp4"}
    name = mapping.get(fmt)
    if not name:
        raise HTTPException(400, f"Unknown format '{fmt}'")
    path = out_dir / name
    if not path.exists():
        raise HTTPException(404, f"{name} not found — generate the report first")
    return FileResponse(str(path), filename=f"{session_id}_{name}")
