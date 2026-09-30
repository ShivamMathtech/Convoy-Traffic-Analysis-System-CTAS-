#!/usr/bin/env bash
# CTAS one-command launcher for Linux / macOS.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "[ERROR] node not found"; exit 1; }

if [ ! -d "$ROOT/backend/.venv" ]; then
  echo "Creating Python venv..."
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
fi

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "Installing frontend deps (first run, may take a few minutes)..."
  (cd "$ROOT/frontend" && npm install)
fi

echo "Starting backend on :8000 ..."
(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

echo "Starting frontend on :5173 ..."
(cd "$ROOT/frontend" && npm run dev) &
FRONT_PID=$!

trap "kill $BACKEND_PID $FRONT_PID 2>/dev/null" EXIT

echo
echo "============================================"
echo " CTAS is running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000  (docs: /docs)"
echo " Press Ctrl+C to stop."
echo "============================================"
wait
