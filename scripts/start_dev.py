#!/usr/bin/env python3
"""One-command development launcher (backend + frontend).

Usage: python scripts/start_dev.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

VENV_PY = BACKEND / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
UVICORN = BACKEND / (".venv/Scripts/uvicorn.exe" if os.name == "nt" else ".venv/bin/uvicorn")


def ensure_venv() -> None:
    if UVICORN.exists():
        return
    print("[start_dev] creating venv + installing backend requirements (first run)...")
    subprocess.check_call([sys.executable, "-m", "venv", str(BACKEND / ".venv")])
    subprocess.check_call([str(BACKEND / (".venv/Scripts/pip.exe" if os.name == "nt" else ".venv/bin/pip")),
                           "install", "-r", str(BACKEND / "requirements.txt")])


def ensure_node() -> None:
    if (FRONTEND / "node_modules").exists():
        return
    print("[start_dev] npm install (first run)...")
    subprocess.check_call(["npm", "install"], cwd=str(FRONTEND))


def main() -> None:
    ensure_venv()
    ensure_node()
    env = os.environ.copy()
    backend = subprocess.Popen([str(UVICORN), "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                               cwd=str(BACKEND), env=env)
    time.sleep(2)
    npm = "npm.cmd" if os.name == "nt" else "npm"
    frontend = subprocess.Popen([npm, "run", "dev"], cwd=str(FRONTEND))
    print("\n============================================")
    print(" CTAS is running:")
    print("  Frontend: http://localhost:5173")
    print("  Backend:  http://localhost:8000  (docs: /docs)")
    print(" Press Ctrl+C to stop.")
    print("============================================\n")
    try:
        frontend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()
