# Architecture

## Overview

CTAS is a two-tier application:

```
┌─────────────────────────┐         HTTP/WS          ┌─────────────────────────┐
│  Frontend (React+TS)    │ ◄──────────────────────► │  Backend (FastAPI)      │
│  Vite :5173             │                          │  uvicorn :8000          │
│  - Dashboard, Live,     │   REST /api/*            │  - routers              │
│    Map2D, 3D, Analytics │   WS /ws/session/{id}    │  - analysis pipeline    │
│    Events, Sessions,    │   MJPEG /api/analysis/   │  - detector + tracker   │
│    Reports, Settings    │     …/stream             │  - SQLite storage       │
└─────────────────────────┘                          └─────────────────────────┘
```

## Backend layout (`backend/app/`)

| Package     | Contents                                                     |
|-------------|--------------------------------------------------------------|
| `api/`      | Routers: `videos`, `streams`, `analysis`, `sessions`, `reports`, `settings` |
| `vision/`   | `detector`, `tracker`, `pipeline`, `preprocessing`, `geometry`, `calibration`, `speed`, `lane_detection`, `group_analysis`, `trajectory`, `visualization` |
| `streaming/`| `video_reader` (file/image/webcam/RTSP/HTTP), `frame_buffer`, `websocket`, `demo` |
| `analytics/`| `statistics`, `spacing`, `congestion`, `events`, `aggregation` |
| `services/` | `session_manager`, `settings_store`                          |
| `reports/`  | `generator` (PDF via ReportLab, CSV, JSON)                   |
| `models/`   | SQLAlchemy tables: Session, Detection, Track, TrackPoint, Event, Calibration, AnalyticsSnapshot |
| `schemas/`  | Pydantic DTOs                                                |

## Request flow (analysis)

1. `POST /api/videos/upload` → file saved to `storage/uploads`, session row created (state PENDING).
2. `POST /api/analysis/start` → `SessionManager` spawns an `AnalysisPipeline` thread.
3. Pipeline: `VideoReader → Detector → Tracker → Geometry/Calibration → Speed →
   Lane assign → Group analysis → Event rules → Visualization/CSV/DB`.
4. Frames are broadcast to WebSocket subscribers at ~15 fps; annotated frames via MJPEG.
5. `POST /api/analysis/stop` → pipeline finalizes: annotated video, CSVs, JSON,
   PDF report, DB commit; session state COMPLETE.

## Concurrency

- One `AnalysisPipeline` thread per session; the FastAPI event loop stays free.
- `StreamingHub` fans out frames to WebSocket clients via a queue; slow clients
  are dropped, not blocking.
- SQLite is used via a thread-local session scope; DB writes are small and batched.

## Configuration

`backend/app/config.py` reads environment variables (see `.env.example`).
Runtime settings (model, tracker, events, UI) live in
`storage/settings.json` and are edited from the Settings page (`PUT /api/settings`).

## Accuracy rules (enforced in code)

- Speed/distance/congestion metrics are reported in **meters/km/h only after a
  homography calibration is applied**; otherwise pixel units labelled `px`, `px/s`.
- GPS fields are always reported `UNAVAILABLE` (no GPS input in this release).
- Without weights the detector returns `MODEL NOT AVAILABLE`; downstream
  modules receive empty detection lists rather than hallucinated ones.
- Depth/Z is fixed to 0 in the 3D view — never fabricated.

## Security boundaries

The repository contains no face recognition, person re-identification,
biometrics, weapon/targeting/engagement/fire-control logic. Vehicle classes
come from the standard COCO vehicle subset.
