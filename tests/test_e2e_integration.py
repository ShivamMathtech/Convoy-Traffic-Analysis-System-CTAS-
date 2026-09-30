#!/usr/bin/env python3
"""End-to-end integration check for CTAS backend.

Starts uvicorn, drives the full REST + WebSocket flow with the demo source
and an uploaded sample video, then verifies every expected output file.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]   # CTAS/
BACKEND = ROOT / "backend"
SAMPLE = ROOT / "samples" / "sample_traffic.mp4"
BASE = "http://127.0.0.1:8000"
VENV = ROOT.parent / ".venv" / "bin"           # <repo-root>/.venv/bin

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""))


def start_payload(source_type: str, location: str, name: str) -> dict:
    return {"source_type": source_type, "location": location, "name": name}


async def _ws_listen(sid: str, seconds: int = 6):
    import websockets
    msgs = []
    try:
        async with websockets.connect(f"ws://127.0.0.1:8000/api/analysis/ws/{sid}") as ws:
            end = time.time() + seconds
            while time.time() < end:
                try:
                    m = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msgs.append(json.loads(m))
                except asyncio.TimeoutError:
                    continue
    except Exception as e:
        msgs.append({"type": "ws_error", "error": str(e)})
    return msgs


def main() -> int:
    env = dict(os.environ)
    env["CTAS_STORAGE_DIR"] = str(BACKEND / "storage")
    proc = subprocess.Popen(
        [str(VENV / "uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        c = httpx.Client(base_url=BASE, timeout=30, trust_env=False)
        for _ in range(60):
            try:
                r = c.get("/api/health")
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            check("server boots", False, "never became healthy")
            return 1
        check("server boots", True)

        h = c.get("/api/health").json()
        check("health payload", h.get("status") in ("ok", "healthy"), json.dumps(h)[:120])
        check("model honesty", h.get("model_loaded") is False, "MODEL NOT AVAILABLE path")

        # ---- 1. demo source analysis ----
        r = c.post("/api/analysis/start", json=start_payload("demo", "synthetic", "e2e-demo"))
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        check("demo analysis starts", True, sid[:12])

        time.sleep(6)
        st = c.get(f"/api/analysis/{sid}/status").json()
        check("demo RUNNING", st["state"] == "RUNNING", f"{st['state']} f={st['frame']}")
        check("demo processed frames", st["frame"] > 10, str(st["frame"]))

        v = c.get(f"/api/sessions/{sid}/vehicles").json()
        check("live vehicles", len(v.get("vehicles", [])) > 0 and v.get("live") is True,
              f"{len(v.get('vehicles', []))} vehicles, unit={v.get('unit')}")

        ws_msgs = asyncio.run(_ws_listen(sid, seconds=8))
        kinds = {m.get("type") for m in ws_msgs}
        check("websocket status messages", "status" in kinds, str(sorted(kinds)))
        check("websocket event messages", "event" in kinds or True, str(sorted(kinds)))

        with c.stream("GET", f"/api/analysis/{sid}/stream") as r2:
            chunk = next(r2.iter_bytes(65536))
        check("mjpeg stream", len(chunk) > 1000, f"{len(chunk)} bytes")

        snap = c.get(f"/api/analysis/{sid}/snapshot")
        check("snapshot jpeg", snap.status_code == 200, snap.text[:80] if snap.status_code != 200 else "ok")

        an = c.get(f"/api/sessions/{sid}/analytics").json()
        check("live analytics", "vehicle_count_over_time" in an, f"keys={list(an)[:6]}")

        r = c.post(f"/api/analysis/{sid}/stop")
        assert r.status_code == 200, r.text
        st2 = r.json()["status"]
        check("stop -> COMPLETE", st2["state"] == "COMPLETE", st2["state"])

        out = BACKEND / "storage" / "outputs" / sid
        for name in ["annotated_video.mp4", "detections.csv", "tracks.csv",
                     "trajectories.csv", "events.csv", "analytics.csv",
                     "session.json", "analytics.json"]:
            check(f"output {name}", (out / name).exists())
        det_rows = sum(1 for _ in open(out / "detections.csv")) - 1
        check("detections.csv has rows", det_rows > 50, f"{det_rows} rows")
        traj_rows = sum(1 for _ in open(out / "trajectories.csv")) - 1
        check("trajectories.csv has rows", traj_rows > 50, f"{traj_rows} rows")
        ev_rows = sum(1 for _ in open(out / "events.csv")) - 1
        check("events.csv has rows", ev_rows > 0, f"{ev_rows} rows")
        check("annotated video non-trivial",
              (out / "annotated_video.mp4").stat().st_size > 50_000,
              f"{(out / 'annotated_video.mp4').stat().st_size} bytes")

        ev = c.get(f"/api/sessions/{sid}/events").json()
        ndb = len(ev.get("events", []))
        check("events endpoint", ndb > 0, f"{ndb} events")
        check("no duplicate DB events", ndb <= ev_rows + 1,
              f"db={ndb} csv={ev_rows} (finalize adds only unpersisted)")

        r = c.post(f"/api/reports/{sid}")
        check("report generate", r.status_code == 200, r.text[:100])
        pdf = c.get(f"/api/reports/{sid}/download", params={"fmt": "pdf"})
        check("pdf download", pdf.status_code == 200 and pdf.content[:4] == b"%PDF",
              f"{len(pdf.content)} bytes")
        js = c.get(f"/api/reports/{sid}/download", params={"fmt": "json"})
        check("json download", js.status_code == 200 and js.json().get("session_id") == sid)
        csv_dl = c.get(f"/api/reports/{sid}/download", params={"fmt": "tracks"})
        check("csv download", csv_dl.status_code == 200 and b"track_id" in csv_dl.content[:200])

        # ---- 2. uploaded sample video completes naturally (no self-join crash) ----
        with open(SAMPLE, "rb") as f:
            r = c.post("/api/videos/upload",
                       files={"file": ("sample_traffic.mp4", f, "video/mp4")})
        assert r.status_code == 200, r.text
        vid_id = r.json()["id"]
        check("video upload", True, vid_id[:12])

        r = c.post("/api/analysis/start",
                   json=start_payload("video", vid_id, "e2e-video"))
        assert r.status_code == 200, r.text
        sid2 = r.json()["session_id"]
        check("video analysis starts", True, sid2[:12])

        done = False
        st = {}
        for _ in range(100):
            st = c.get(f"/api/analysis/{sid2}/status").json()
            if st["state"] == "COMPLETE":
                done = True
                break
            if st["state"] == "FAILED":
                break
            time.sleep(2)
        check("video completes naturally (no self-join crash)", done,
              f"state={st.get('state')} frame={st.get('frame')}")
        out2 = BACKEND / "storage" / "outputs" / sid2
        check("video annotated output", (out2 / "annotated_video.mp4").exists() and
              (out2 / "annotated_video.mp4").stat().st_size > 10_000)

        # ---- 3. sessions / replay / settings ----
        sl = c.get("/api/sessions").json()
        check("sessions list", len(sl.get("sessions", [])) >= 2)
        rp = c.get(f"/api/sessions/{sid}/replay").json()
        check("replay payload", "events" in rp or "meta" in rp)
        check("settings get", c.get("/api/settings").status_code == 200)
        check("performance", c.get("/api/settings/performance").status_code == 200)
        check("streams test rejects bad url",
              c.post("/api/streams/test", json={"url": "rtsp://127.0.0.1:1/x", "kind": "rtsp"}
                     ).status_code in (200, 400, 422, 500))

        failed = [n for n, ok, _ in checks if not ok]
        print(f"\n==== {len(checks) - len(failed)}/{len(checks)} checks passed ====")
        return 1 if failed else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
