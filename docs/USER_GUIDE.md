# User Guide

## 1. Launch

- **Windows:** double-click `start_windows.bat`
- **Linux/macOS:** `chmod +x start_linux.sh && ./start_linux.sh`
- **Docker:** `docker compose up --build`

Open **http://localhost:5173**. The top bar shows backend connectivity.

## 2. Select a source

Press **＋ SELECT SOURCE** (or the button on an empty dashboard):

- **Upload Video** — drag & drop MP4/AVI/MOV/MKV/WEBM (≤ 1 GB default)
- **Existing** — pick a previously uploaded file
- **Image Dir** — a folder of frames (JPG/PNG)
- **Camera** — local webcam/USB index (tested with the Test button)
- **RTSP** — paste the stream URL, test, then start
- **HTTP** — HTTP/MJPEG stream URL
- **Demo** — synthetic traffic, watermarked **DEMO / SYNTHETIC DATA**

Choosing a source creates a session and (for files) uploads it. Press
**START ANALYSIS** in the dialog.

## 3. Dashboard

- **Live Video Feed** — annotated frames with boxes, IDs, speed, lanes;
  pause/resume/stop, snapshot (S), fullscreen (F), progress bar for files.
- **2D Localization** — top-view map with per-vehicle markers and headings.
- **3D Localization** — perspective view (drag to rotate). Z is 0 for all
  vehicles — monocular video has no true depth; it is not fabricated.
- **Vehicle Summary** — live per-class counts, speed unit.
- **Analytics** — count over time, speed distribution, spacing, class donut.
- **Events & Alerts** — real-time rule firings with severity colours.

Keyboard: **Space** pause/resume, **S** snapshot, **F** fullscreen.

## 4. Live View

Vehicle list (click any row for the detail drawer: class, confidence, speed,
heading, lane, group, bbox), plus **Perspective Calibration**:

1. Pause the video on a clear frame.
2. Choose 4 fixed ground points you know (lane markings, poles) and enter
   their image pixel coords (u,v) and real-world coords (X,Y meters).
3. **Apply Calibration** — speed switches from `px/s` to `km/h`, spacing to
   meters, and metric event rules (overspeed, close spacing) activate.

**Lane Polygons** — JSON list of named polygons in pixel coords; vehicles get
a lane label and per-lane counts.

## 5. Analytics / Events / Map / 3D

Same views, full-page. Events page supports severity and text filters.

## 6. Sessions

Every analysis is stored: open a past session, replay its stream,
or jump to Reports. Delete removes the session and its output files.

## 7. Reports

**Generate Report** builds, then download:
PDF summary, JSON summary, annotated video, tracks/detections/events/analytics CSVs.

## 8. Settings

Model (device, imgsz 320–960, conf/IoU), tracker (ByteTrack/BoT-SORT,
max_age, min_hits), video mode, group thresholds, event rules, overlay options,
and a Performance panel (CPU/RAM/disk/GPU, model load state).

## 9. Model installation (for real detection)

```bash
pip install ultralytics
# place yolov8n.pt (or compatible) at CTAS/models/default_model.pt
```

Until then the dashboard honestly shows **MODEL NOT AVAILABLE** — the demo
source still exercises the full pipeline end to end.

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| Backend not reachable | start backend: `cd backend && uvicorn app.main:app --port 8000` |
| MODEL NOT AVAILABLE | install ultralytics + weights (see §9) |
| RTSP won't connect | Test first; check credentials/IP; firewall |
| Slow inference | Settings → Model → device `cuda` if GPU, or `fast` video mode, imgsz 416 |
| Port in use | stop the other process or edit ports in `start_*` / compose file |
