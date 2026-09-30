"""API tests: health, upload validation, settings."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["database"] is True
    assert "version" in body


def test_upload_rejects_bad_extension():
    r = client.post("/api/videos/upload", files={"file": ("evil.exe", b"nope", "application/octet-stream")})
    assert r.status_code == 400


def test_settings_roundtrip():
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert "model" in r.json()
    r2 = client.put("/api/settings", json={"patch": {"ui": {"trajectory_seconds": 7.0}}})
    assert r2.status_code == 200
    assert r2.json()["settings"]["ui"]["trajectory_seconds"] == 7.0
    # restore
    client.put("/api/settings", json={"patch": {"ui": {"trajectory_seconds": 5.0}}})


def test_model_info_honest_when_missing():
    r = client.get("/api/settings/model")
    assert r.status_code == 200
    body = r.json()
    assert "loaded" in body and "hint" in body


def test_stream_test_rejects_garbage():
    r = client.post("/api/streams/test", json={"url": "rtsp://127.0.0.1:1/nope", "kind": "rtsp"})
    assert r.status_code in (400, 422)


def test_analysis_start_rejects_unknown_source():
    r = client.post("/api/analysis/start",
                    json={"source_type": "video", "location": "/nonexistent/x.mp4", "name": "t"})
    assert r.status_code in (400, 404)
