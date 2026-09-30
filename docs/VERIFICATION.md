# Verification Record — CTAS build (2026-09-30)

How each item was checked. Anything not runnable in this environment is marked
honestly instead of being claimed.

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Frontend build (`tsc -b && vite build`) | ✅ PASS | `dist/` built in ~10s, 0 errors |
| 2 | Backend imports & startup (`uvicorn app.main:app`) | ✅ PASS | `/api/health` → 200 `{"status":"healthy"}` |
| 3 | Unit tests | ✅ PASS | `pytest app/tests` — **27/27 passed** |
| 4 | Database (SQLite init + session/track/event rows) | ✅ PASS | e2e: sessions listed, tracks & events persisted, no duplicate event rows (db=199 = csv=199) |
| 5 | Video reader (file upload → frames) | ✅ PASS | `sample_traffic.mp4` uploaded, 375/375 frames processed |
| 6 | Detector honesty (no model installed) | ✅ PASS | health `model_loaded: false`; dashboard shows MODEL NOT AVAILABLE; demo source still exercises pipeline |
| 7 | Tracker (persistent IDs, trajectories) | ✅ PASS | live `/vehicles` returned tracked IDs; `trajectories.csv` + `tracks.csv` populated |
| 8 | WebSocket (`/api/analysis/ws/{id}`) | ✅ PASS | received `status` + `event` messages live (fixed worker-thread loop bug during verification) |
| 9 | MJPEG stream | ✅ PASS | `/api/analysis/{id}/stream` streamed JPEG frames |
| 10 | Analytics (counts, speed, spacing, groups) | ✅ PASS | `/sessions/{id}/analytics` returned all series; charts render from same payload |
| 11 | Events (rules fire from real state) | ✅ PASS | 199 events for demo session (entered/exited, groups, lifecycle); severity filter works |
| 12 | Report generation (PDF/JSON/CSV/video) | ✅ PASS | `report.pdf` (valid %PDF), `report.json`, CSV downloads all 200 |
| 13 | Natural EOF (file completes, no self-join crash) | ✅ PASS | video session reached COMPLETE on its own (fixed `stop()` self-join during verification) |
| 14 | Annotated video output | ✅ PASS | `annotated_video.mp4` written at processed resolution |
| 15 | Demo watermark | ✅ PASS | frames carry `DEMO / SYNTHETIC DATA` banner |
| 16 | Calibration units honesty | ✅ PASS | uncalibrated → `px/s`, `px`; metric labels appear only after homography set |
| 17 | `start_windows.bat` / `start_linux.sh` | ⚠️ PARTIAL | `bash -n` syntax ok; Windows .bat reviewed, not executed here (no Windows host) |
| 18 | Dockerfiles / `docker-compose.yml` | ⚠️ PARTIAL | reviewed (correct ports, volumes, healthcheck, nginx proxy); `docker` not available in this VM, so images were not built here |
| 19 | Webcam / RTSP / HTTP live sources | ⚠️ PARTIAL | code paths + `/streams/test` exercised against an unreachable RTSP (clean rejection); no real camera/stream in this VM — results on user hardware will be honest pass/fail |
| 20 | Real YOLO detection | ⏭️ NOT INSTALLED | `ultralytics` intentionally optional; pipeline verified with detector adapter + synthetic detections; install per README §9 for real video |

Bugs found and fixed during verification:
- `AnalysisPipeline.stop()` joined the calling thread on natural EOF → skipped self-join.
- Event CSV was closed before the final lifecycle event → reordered (event → flush → close).
- `detections.csv` / `trajectories.csv` had headers only → per-frame rows now written.
- `VideoWriter` used raw source dims while frames were resized → writer now sized from processed dims.
- Events persisted twice (live callback + finalize) → keyed dedup in finalize.
- WebSocket broadcasts from worker threads silently dropped → main loop captured in lifespan, `run_coroutine_threadsafe`.
- Integration script drove the real API and caught a frontend/backend request-shape mismatch in the start call.
