"""CTAS backend — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import analysis, reports, sessions, settings, streams, videos
from app.database import init_db

LOG_DIR = Path(config.BACKEND_DIR) / "logs"
LOG_DIR.mkdir(exist_ok=True)
_handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=5_000_000, backupCount=3)
logging.basicConfig(level=logging.INFO, handlers=[_handler, logging.StreamHandler()],
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ctas")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.services.session_manager import manager
    init_db()
    manager.set_loop(asyncio.get_running_loop())
    log.info("CTAS backend starting (version %s)", config.VERSION)
    yield
    log.info("CTAS backend shutting down")


app = FastAPI(title=config.APP_NAME, version=config.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # dev default; tighten via reverse proxy in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/api/health")
def health():
    from app.services.session_manager import manager
    from app.vision.detector import get_detector_status
    det = get_detector_status()
    return {
        "status": "healthy",
        "database": True,
        "model_loaded": det["loaded"],
        "model_path": det["path"],
        "gpu_available": det["gpu_available"],
        "active_sessions": manager.active_count(),
        "version": config.VERSION,
    }


# Serve generated outputs (annotated videos, reports) for download/preview.
app.mount("/storage", StaticFiles(directory=str(config.STORAGE_DIR)), name="storage")
