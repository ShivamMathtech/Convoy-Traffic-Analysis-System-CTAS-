# Convoy & Traffic Analysis System (CTAS)

AI-powered video analytics platform: vehicle detection, multi-object tracking,
perspective localization, speed & spacing analysis, convoy/group detection,
event engine, and reporting — behind a dark operations dashboard.

> **Intended use:** traffic analytics, authorized fleet monitoring,
> transportation research, road safety, computer-vision research, logistics.
> No face recognition, no person identification, no weapon/targeting logic.

## Features

- **Sources:** uploaded video (MP4/AVI/MOV/MKV/WEBM), existing files, images /
  image directories, webcam/USB camera, RTSP, HTTP/MJPEG, and a clearly-marked
  synthetic **Demo** source.
- **Detection:** Ultralytics YOLO-compatible adapter (CPU/CUDA/MPS), configurable
  image size (320–960), confidence & IoU thresholds. Honest _MODEL NOT AVAILABLE_
  state when weights are missing — never fake detections.
- **Tracking:** ByteTrack and BoT-SORT adapters with persistent track IDs,
  trajectories, velocity/heading.
- **Localization:** operator calibration (4 image points → ground coords) via
  homography; metric speed (km/h) & distance only when calibrated, otherwise
  pixel units are labelled as such.
- **Analytics:** live counts, speed distribution, inter-vehicle spacing,
  class distribution, lane occupancy, flow rate, convoy/group analysis,
  stopped-vehicle & congestion detection.
- **Outputs:** annotated video, detections/tracks/trajectories/events/analytics
  CSVs, JSON, PDF report, session replay.

## Quick start

### Windows

```bat
start_windows.bat
```

### Linux / macOS

```bash
chmod +x start_linux.sh
./start_linux.sh
```

### Docker

```bash
docker compose up --build
```

CPU and GPU deployments are documented separately in `docs/`.

### Manual

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev
```

| Service  | URL                        |
| -------- | -------------------------- |
| Frontend | http://localhost:5173      |
| Backend  | http://localhost:8000      |
| Swagger  | http://localhost:8000/docs |

## Model installation

Real detection needs the Ultralytics stack and weights:

```bash
pip install ultralytics          # pulls in PyTorch (~2 GB)
# download yolov8n.pt from https://github.com/ultralytics/assets
# place it at:  CTAS/models/default_model.pt
```

Without it the backend still runs; the dashboard shows **MODEL NOT AVAILABLE**
and the Demo source can be used to exercise the whole pipeline.

## Usage

1. Open http://localhost:5173 → **＋ SELECT SOURCE**
2. Upload a video (or pick Demo for synthetic data)
3. Video preview appears → press **START ANALYSIS**
4. Watch live feed, 2D/3D localization, charts, events
5. (Optional) Live View → **Perspective Calibration**: enter 4 image points +
   known ground coordinates to unlock km/h & meters
6. Sessions → replay a finished session; Reports → generate PDF/CSV/JSON

See `docs/USER_GUIDE.md` for the full walkthrough, `docs/API.md` for the REST +
WebSocket reference, `docs/ARCHITECTURE.md` for system design, and
`docs/COMPUTER_VISION.md` for the math.

## Tests

```bash
cd backend
pytest app/tests -q        # 27 tests
cd ../frontend
npm run build              # typecheck + production build
```

## Folder structure

```
CTAS/
├── backend/        # FastAPI app: api/, vision/, streaming/, analytics/, ...
├── frontend/       # React + TypeScript + Vite dashboard
├── models/         # default_model.pt goes here (not shipped)
├── samples/        # sample traffic clip
├── docs/           # architecture, CV math, API, user guide
├── scripts/        # start_dev.py, sample generator
├── docker-compose.yml
├── start_windows.bat / start_linux.sh
└── Makefile
```

## License

MIT — see `LICENSE`.
