# API Reference

Base URL: `http://localhost:8000`. All REST routes are under `/api/`.
Interactive docs: `/docs`.

## Videos

| Method | Route                        | Description                                  |
|--------|------------------------------|----------------------------------------------|
| POST   | `/api/videos/upload`         | multipart `file` → `{id, filename, ...}`     |
| GET    | `/api/videos`                | list uploaded videos                         |
| DELETE | `/api/videos/{id}`           | delete upload                                |

## Streams (source probing)

| Method | Route                        | Description                                  |
|--------|------------------------------|----------------------------------------------|
| POST   | `/api/streams/test`          | `{kind: "rtsp"\|"http"\|"webcam", url?, index?}` → reachability |
| POST   | `/api/streams/start`         | start live source analysis                   |
| GET    | `/api/streams/cameras`       | enumerate local cameras                      |

## Analysis

| Method | Route                                | Description                              |
|--------|--------------------------------------|------------------------------------------|
| POST   | `/api/analysis/start`                | `{session_id}` or `{source}` → start      |
| POST   | `/api/analysis/{id}/pause`           | pause                                    |
| POST   | `/api/analysis/{id}/resume`          | resume                                   |
| POST   | `/api/analysis/{id}/stop`            | stop + finalize outputs                  |
| GET    | `/api/analysis/{id}/status`          | state, fps, progress, counts             |
| GET    | `/api/analysis/{id}/stream`          | MJPEG annotated video                    |
| GET    | `/api/analysis/{id}/vehicles`        | current live vehicles                    |
| GET    | `/api/analysis/{id}/events`          | session events                           |
| GET    | `/api/analysis/{id}/analytics`       | aggregated analytics series              |
| GET    | `/api/analysis/{id}/snapshot`        | latest annotated frame (JPEG)            |
| POST   | `/api/analysis/{id}/calibration`     | set 4+ image↔world correspondences       |
| POST   | `/api/analysis/{id}/lanes`           | set lane polygons                        |

## Sessions

| Method | Route                        | Description                                  |
|--------|------------------------------|----------------------------------------------|
| GET    | `/api/sessions`              | session history                              |
| GET    | `/api/sessions/{id}`         | detail                                       |
| DELETE | `/api/sessions/{id}`         | delete session + outputs                     |
| GET    | `/api/sessions/{id}/events`  | events                                       |
| GET    | `/api/sessions/{id}/tracks`  | tracks + trajectories                        |
| GET    | `/api/sessions/{id}/analytics`| stored analytics                            |
| GET    | `/api/sessions/{id}/replay`  | replay feed parameters                       |

## Reports

| Method | Route                                | Description                      |
|--------|--------------------------------------|----------------------------------|
| POST   | `/api/reports/{id}/generate`         | build report bundle              |
| GET    | `/api/reports/{id}/download?format=` | `pdf\|json\|video\|tracks\|detections\|events\|analytics` |

## Settings

| Method | Route                | Description                              |
|--------|----------------------|------------------------------------------|
| GET    | `/api/settings`      | full settings object                     |
| PUT    | `/api/settings`      | replace settings                         |
| GET    | `/api/settings/performance` | cpu/ram/disk/gpu/detector status |

## WebSocket

`ws://localhost:8000/ws/session/{session_id}`

Messages from server:

```json
{"type": "frame", "frame": 123, "timestamp": 4.1, "annotated_jpeg_b64": "..."}
{"type": "vehicles", "vehicles": [{"track_id": 3, "class_name": "car", ...}]}
{"type": "event", "event": {"event_type": "stopped_vehicle", ...}}
{"type": "analytics", "analytics": {"vehicle_count_over_time": [...], ...}}
{"type": "status", "status": {"state": "RUNNING", ...}}
```

Client → server: `{"type": "ping"}`.

## Session lifecycle

`PENDING → RUNNING ⇄ PAUSED → COMPLETE` (or `FAILED`).
