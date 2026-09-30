"""Analysis pipeline: capture -> detect -> track -> geometry -> analytics.

State machine: IDLE -> LOADING -> RUNNING -> (PAUSED | ERROR) -> STOPPING -> COMPLETE

Runs the capture loop and the processing loop on two threads joined by a
bounded FrameBuffer. REALTIME mode drops stale frames; ACCURATE processes
every frame; FAST subsamples and shrinks inference size.
"""
from __future__ import annotations

import csv
import logging
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from app import config
from app.analytics.aggregation import AnalyticsAggregator
from app.analytics.congestion import CongestionDetector
from app.analytics.events import EventEngine
from app.streaming.frame_buffer import FrameBuffer
from app.vision import calibration as calib_mod
from app.vision import detector as det_mod
from app.vision import tracker as tracker_mod
from app.vision.group_analysis import GroupAnalyzer
from app.vision.lane_detection import LaneAnalyzer
from app.vision.preprocessing import resize_keep_aspect
from app.vision.speed import SpeedEstimator
from app.vision.trajectory import TrajectoryStore
from app.vision.visualization import draw_banner, draw_lanes, draw_tracks

log = logging.getLogger("ctas.pipeline")

VALID_TRANSITIONS = {
    "IDLE": {"LOADING"},
    "LOADING": {"RUNNING", "ERROR", "STOPPING"},
    "RUNNING": {"PAUSED", "ERROR", "STOPPING"},
    "PAUSED": {"RUNNING", "STOPPING", "ERROR"},
    "ERROR": {"IDLE", "STOPPING"},
    "STOPPING": {"COMPLETE", "ERROR", "IDLE"},
    "COMPLETE": {"IDLE", "LOADING"},
}


class AnalysisPipeline:
    def __init__(self, session_id: str, source, settings: dict,
               out_dir: Path, on_event=None, on_status=None):
        self.session_id = session_id
        self.source = source
        self.settings = settings
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.on_event = on_event      # callback(event_dict)
        self.on_status = on_status    # callback(status_dict)

        self.state = "IDLE"
        self.frame_no = 0
        self.processed_frames = 0
        self.dropped_frames = 0
        self.inference_fps = 0.0
        self.latency_ms = 0.0
        self.error: str | None = None

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()

        # vision stack
        self.detector = det_mod.get_detector(settings)
        self.tracker = tracker_mod.create_tracker(settings)
        self.calibration = calib_mod.Calibration()
        self.lanes = LaneAnalyzer()
        self.groups = GroupAnalyzer(**{k: v for k, v in settings.get("groups", {}).items()
                                       if k in ("dmax", "hmax_deg", "tmin_sec", "min_vehicles", "enabled")})
        self.speeds = SpeedEstimator()
        self.trajectories = TrajectoryStore()
        self.events = EventEngine(settings)
        self.agg = AnalyticsAggregator()
        ev_cfg = settings.get("events", {})
        self.congestion = CongestionDetector(int(ev_cfg.get("congestion_density", 25)),
                                            float(ev_cfg.get("congestion_seconds", 10.0)))

        self._latest_jpeg: bytes | None = None
        self._writer = None
        self._csv_files: dict[str, any] = {}
        self._csv_writers: dict[str, csv.writer] = {}
        self._known_group_ids: set[int] = set()
        self._track_group: dict[int, int] = {}
        self._start_wall = 0.0

    # ---------------------------------------------------------- state
    def _set_state(self, new: str) -> None:
        if new not in VALID_TRANSITIONS.get(self.state, set()):
            raise RuntimeError(f"Illegal pipeline transition {self.state} -> {new}")
        log.info("Session %s: %s -> %s", self.session_id, self.state, new)
        self.state = new

    # ---------------------------------------------------------- control
    def start(self) -> None:
        self._set_state("LOADING")
        info = self.source.open()
        self.info = info
        cal = self.settings.get("calibration", {})
        if cal.get("image_points") and cal.get("world_points"):
            try:
                self.calibration.set_points(cal["image_points"], cal["world_points"],
                                            cal.get("units", "meters"))
            except Exception as exc:  # noqa: BLE001
                log.warning("Calibration failed: %s", exc)
        lanes = self.settings.get("lanes", [])
        if lanes:
            self.lanes.set_lanes(lanes)
        else:
            self.lanes.estimate_lanes(info.width or 1280, info.height or 720, 3)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = info.fps if info.fps and not info.is_live else 25.0
        # writer dimensions must match the PROCESSED frame size (post-resize),
        # not the raw source size
        max_w0 = int(self.settings.get("video", {}).get("max_width", 1280))
        probe = resize_keep_aspect(
            np.zeros((info.height or 720, info.width or 1280, 3), dtype=np.uint8), max_w0)
        self._writer_size = (probe.shape[1], probe.shape[0])
        self._writer = cv2.VideoWriter(
            str(self.out_dir / "annotated_video.mp4"), fourcc, fps, self._writer_size)
        self._open_csvs()
        self._set_state("RUNNING")
        self._start_wall = time.time()
        self.events.lifecycle("started", 0.0, f"Analysis started on {info.location}")
        self._buffer = FrameBuffer(maxsize=8)
        self._threads = [
            threading.Thread(target=self._capture_loop, daemon=True, name="capture"),
            threading.Thread(target=self._process_loop, daemon=True, name="process"),
        ]
        for t in self._threads:
            t.start()

    def pause(self) -> None:
        if self.state == "RUNNING":
            self._set_state("PAUSED")
            self._pause.set()

    def resume(self) -> None:
        if self.state == "PAUSED":
            self._pause.clear()
            self._set_state("RUNNING")

    def stop(self) -> None:
        if self.state in ("COMPLETE", "IDLE"):
            return
        self._set_state("STOPPING")
        self._stop.set()
        self._pause.clear()
        self._buffer.close()
        me = threading.current_thread()
        for t in self._threads:
            if t is not me:  # never join the calling thread (natural EOF)
                t.join(timeout=10)
        try:
            self.source.release()
        except Exception:  # noqa: BLE001
            pass
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        # order matters: lifecycle event first, then flush events to CSV,
        # then close files, then write summary JSON
        self.events.lifecycle("stopped", self._elapsed(), "Analysis stopped")
        self._flush_events()
        self._close_csvs()
        self._write_session_json()
        if self.state == "STOPPING":
            self._set_state("COMPLETE")

    # ---------------------------------------------------------- loops
    def _elapsed(self) -> float:
        return time.time() - self._start_wall if self._start_wall else 0.0

    def _capture_loop(self) -> None:
        mode = self.settings.get("video", {}).get("mode", "realtime")
        while not self._stop.is_set():
            if self._pause.is_set():
                time.sleep(0.05)
                continue
            ok, frame, ts = self.source.read()
            if not ok:
                if getattr(self.source, "kind", "") in ("video", "image", "image_dir"):
                    log.info("Source exhausted — finishing")
                    break
                time.sleep(0.2)
                continue
            self.frame_no += 1
            if mode == "realtime":
                self._buffer.put_latest((frame, ts))  # drops stale
            else:
                self._buffer.put_latest((frame, ts))
        self._buffer.close()

    def _process_loop(self) -> None:
        mode = self.settings.get("video", {}).get("mode", "realtime")
        interval = max(1, int(self.settings.get("video", {}).get("frame_interval", 1)))
        max_w = int(self.settings.get("video", {}).get("max_width", 1280))
        ui = self.settings.get("ui", {})
        infer_times = []
        while not self._stop.is_set():
            if self._pause.is_set():
                time.sleep(0.05)
                continue
            item = self._buffer.get(timeout=0.5)
            if item is None:
                if self._buffer.closed and self._buffer.qsize() == 0:
                    break
                continue
            frame, ts = item
            if mode == "fast" and (self.processed_frames % interval != 0):
                self.processed_frames += 1
                self.dropped_frames += 1
                continue
            t0 = time.perf_counter()
            try:
                self._process_frame(frame, ts, ui, max_w)
            except Exception as exc:  # noqa: BLE001
                log.exception("Frame processing failed: %s", exc)
            dt = time.perf_counter() - t0
            infer_times.append(dt)
            if len(infer_times) > 30:
                infer_times.pop(0)
            self.inference_fps = len(infer_times) / max(sum(infer_times), 1e-6)
            self.processed_frames += 1
        # natural end of a file source
        if not self._stop.is_set():
            self.stop()

    # ---------------------------------------------------------- frame
    def _process_frame(self, frame: np.ndarray, ts: float, ui: dict, max_w: int) -> None:
        frame = resize_keep_aspect(frame, max_w)
        h, w = frame.shape[:2]

        # demo source injects perfect detections (clearly synthetic)
        detections = getattr(self.source, "_detections", None)
        if detections is None:
            t0 = time.perf_counter()
            detections = self.detector.predict(frame)
            self.latency_ms = (time.perf_counter() - t0) * 1000.0
            self.detector.last_latency_ms = self.latency_ms
        else:
            self.latency_ms = 0.5

        tracks = self.tracker.update(detections, ts)
        calibrated = self.calibration.is_calibrated
        unit = "km/h" if calibrated else "px/s"

        new_events = []
        # per-track enrichment
        for tr in tracks:
            cx, cy = tr.centroid
            world = self.calibration.to_world(cx, cy)
            tr.world_xy = world  # type: ignore[attr-defined]
            px, py = world if world else (cx, cy)
            raw, smooth, _u = self.speeds.update(tr.id, px, py, ts, calibrated)
            tr.speed = smooth
            tr.speed_unit = unit  # type: ignore[attr-defined]
            lane, changed = self.lanes.lane_of_track(tr.id, cx, cy)
            prev_lane = tr.lane
            tr.lane = lane
            if changed and prev_lane:
                ev = self.events.lane_change(tr.id, prev_lane, lane or "?", ts)
                if ev: new_events.append(ev)
            self.trajectories.push(tr.id, cx, cy, ts)
            ev = self.events.stopped_vehicle(tr.id, ts, smooth, calibrated)
            if ev: new_events.append(ev)

        # groups
        groups = self.groups.update(tracks, ts, calibrated)
        for g in groups:
            if g.id not in self._known_group_ids:
                self._known_group_ids.add(g.id)
                ev = self.events.group_formed(g.id, len(g.member_ids), ts)
                if ev: new_events.append(ev)
        current_group_of = {}
        for g in groups:
            for mid in g.member_ids:
                current_group_of[mid] = g.id
        for tr in tracks:
            old_g = self._track_group.get(tr.id)
            new_g = current_group_of.get(tr.id)
            if old_g and old_g != new_g:
                ev = self.events.group_left(tr.id, old_g, ts)
                if ev: new_events.append(ev)
            tr.group_id = new_g
            self._track_group[tr.id] = new_g  # type: ignore[assignment]

        # entered / exited
        active_ids = {t.id for t in tracks}
        before = set(self.events._known_ids)
        evs = self.events.entered_exited(active_ids, ts)
        new_events.extend(evs)
        entered_now = len(active_ids - before)

        # spacing warnings (leader gaps)
        if calibrated:
            from app.analytics import spacing as spacing_mod
            sp = spacing_mod.spacing_stats(tracks, calibrated)
            # warn on the closest follower pair only (avoid spam)
            pts = sorted(tracks, key=lambda t: (t.world_xy or t.centroid)[1])
            for a, b in zip(pts, pts[1:]):
                pa = a.world_xy or a.centroid
                pb = b.world_xy or b.centroid
                gap = ((pa[0]-pb[0])**2 + (pa[1]-pb[1])**2) ** 0.5
                ev = self.events.spacing_threshold(b.id, gap, ts, calibrated)
                if ev:
                    new_events.append(ev)
                    break

        # congestion
        if self.congestion.update(len(tracks), ts):
            ev = self.events.congestion(ts, len(tracks))
            if ev: new_events.append(ev)

        # analytics snapshot (1 Hz)
        snap = self.agg.update(ts, tracks, calibrated, groups, entered_now)
        if snap:
            self._write_snapshot(snap)

        # persist track points (sampled: every 5th processed frame)
        if self.processed_frames % 5 == 0:
            self._write_track_points(tracks, ts)

        # detection + trajectory CSV rows (every processed frame)
        self._write_detection_rows(detections, tracks, ts)
        self._write_trajectory_rows(tracks, ts)

        # render annotated frame
        annotated = draw_tracks(
            frame.copy(), tracks,
            show_trajectories=ui.get("show_trajectories", True),
            trajectory_seconds=float(ui.get("trajectory_seconds", 5.0)),
            show_labels=ui.get("show_labels", True),
            show_confidence=ui.get("show_confidence", True),
            now=ts)
        draw_lanes(annotated, self.lanes.lanes)
        if getattr(self.source, "kind", "") == "demo":
            draw_banner(annotated, "DEMO / SYNTHETIC DATA")
        if self._writer is not None:
            ww, wh = self._writer_size
            if (annotated.shape[1], annotated.shape[0]) != (ww, wh):
                annotated = cv2.resize(annotated, (ww, wh))
            self._writer.write(annotated)
        ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            with self._lock:
                self._latest_jpeg = buf.tobytes()

        # stream out events + status callback
        for ev in new_events:
            if self.on_event:
                self.on_event(ev.to_dict())
        if self.on_status and self.processed_frames % 5 == 0:
            self.on_status(self.status_dict())

    # ---------------------------------------------------------- output
    def status_dict(self) -> dict:
        total = getattr(getattr(self, "info", None), "total_frames", 0) or 0
        return {
            "session_id": self.session_id,
            "state": self.state,
            "frame": self.frame_no,
            "total_frames": total,
            "fps": round(getattr(getattr(self, "info", None), "fps", 0) or 0, 1),
            "inference_fps": round(self.inference_fps, 1),
            "latency_ms": round(self.latency_ms, 1),
            "progress": round(self.frame_no / total * 100, 1) if total else 0.0,
            "source": getattr(getattr(self, "info", None), "location", ""),
            "model_loaded": bool(self.detector.loaded),
            "dropped_frames": self.dropped_frames,
            "queue": self._buffer.qsize() if hasattr(self, "_buffer") else 0,
            "error": self.error,
        }

    def latest_jpeg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpeg

    def snapshot(self, path: Path) -> Path:
        jpg = self.latest_jpeg()
        if jpg is None:
            raise RuntimeError("No frame available yet")
        path.write_bytes(jpg)
        return path

    # ---------------------------------------------------------- storage
    def _open_csvs(self) -> None:
        import csv as _csv
        specs = {
            "detections.csv": ["timestamp", "frame", "track_id", "class", "confidence",
                               "x1", "y1", "x2", "y2"],
            "tracks.csv": ["timestamp", "frame", "track_id", "class", "confidence",
                           "pixel_x", "pixel_y", "world_x", "world_y",
                           "speed", "heading", "lane", "group_id"],
            "trajectories.csv": ["track_id", "timestamp", "pixel_x", "pixel_y"],
            "events.csv": ["timestamp", "event_type", "severity", "track_id", "description"],
            "analytics.csv": ["timestamp", "vehicle_count", "class_counts",
                              "average_speed", "average_spacing", "group_count"],
        }
        for name, header in specs.items():
            f = open(self.out_dir / name, "w", newline="", encoding="utf-8")
            w = _csv.writer(f)
            w.writerow(header)
            self._csv_files[name] = f
            self._csv_writers[name] = w

    def _write_detection_rows(self, detections, tracks, ts: float) -> None:
        w = self._csv_writers.get("detections.csv")
        if not w:
            return
        # map each detection to the track it was matched to (best IoU), -1 if none
        track_boxes = [(tr.id, tr.bbox) for tr in tracks]
        for d in detections:
            db = [float(x) for x in d.bbox]
            tid = -1
            best = 0.0
            for t_id, tb in track_boxes:
                ix1, iy1 = max(db[0], tb[0]), max(db[1], tb[1])
                ix2, iy2 = min(db[2], tb[2]), min(db[3], tb[3])
                inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
                area = (db[2] - db[0]) * (db[3] - db[1]) + (tb[2] - tb[0]) * (tb[3] - tb[1])
                iou = inter / max(area - inter, 1e-6)
                if iou > best:
                    best, tid = iou, t_id
            w.writerow([round(ts, 2), self.frame_no, tid, d.class_name,
                        round(float(d.confidence), 3),
                        round(db[0], 1), round(db[1], 1), round(db[2], 1), round(db[3], 1)])

    def _write_trajectory_rows(self, tracks, ts: float) -> None:
        w = self._csv_writers.get("trajectories.csv")
        if not w:
            return
        for tr in tracks:
            w.writerow([tr.id, round(ts, 2), round(tr.centroid[0], 1), round(tr.centroid[1], 1)])

    def _write_snapshot(self, snap: dict) -> None:
        import json as _json
        w = self._csv_writers.get("analytics.csv")
        if w:
            w.writerow([snap["t"], snap["vehicle_count"], _json.dumps(snap["class_counts"]),
                        snap["average_speed"], snap["average_spacing"], snap["group_count"]])

    def _write_track_points(self, tracks, ts: float) -> None:
        w = self._csv_writers.get("tracks.csv")
        if not w:
            return
        for tr in tracks:
            wx, wy = (tr.world_xy if getattr(tr, "world_xy", None) else (None, None))
            w.writerow([round(ts, 2), self.frame_no, tr.id, tr.class_name,
                        round(tr.confidence, 3), round(tr.centroid[0], 1), round(tr.centroid[1], 1),
                        "" if wx is None else round(wx, 2), "" if wy is None else round(wy, 2),
                        "" if tr.speed is None else round(tr.speed, 2),
                        "" if tr.heading is None else round(tr.heading, 1),
                        tr.lane or "", tr.group_id if tr.group_id is not None else ""])

    def _flush_events(self) -> None:
        w = self._csv_writers.get("events.csv")
        if w:
            for ev in self.events.events:
                w.writerow([round(ev.timestamp, 2), ev.event_type, ev.severity,
                            ev.track_id if ev.track_id is not None else "", ev.description])

    def _close_csvs(self) -> None:
        for f in self._csv_files.values():
            try:
                f.close()
            except Exception:  # noqa: BLE001
                pass
        self._csv_files.clear()
        self._csv_writers.clear()

    def _write_session_json(self) -> None:
        import json as _json
        payload = {
            "session_id": self.session_id,
            "state": self.state,
            "frames": self.frame_no,
            "processed_frames": self.processed_frames,
            "dropped_frames": self.dropped_frames,
            "inference_fps": self.inference_fps,
            "calibrated": self.calibration.is_calibrated,
            "calibration": self.calibration.as_dict(),
            "lanes": [{"id": l.id, "name": l.name, "polygon": l.polygon} for l in self.lanes.lanes],
            "analytics": self.agg.chart_payload(),
            "settings": self.settings,
        }
        (self.out_dir / "session.json").write_text(_json.dumps(payload, indent=2), encoding="utf-8")
        (self.out_dir / "analytics.json").write_text(
            _json.dumps(self.agg.chart_payload(), indent=2), encoding="utf-8")
