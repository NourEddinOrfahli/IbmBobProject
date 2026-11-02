#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${PORT:-3000}"
PYTHON_BIN="${PYTHON_BIN:-python}"
BACKEND_PID=""
FRONTEND_PID=""

cd "$ROOT_DIR"

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, httpx, pydantic, dotenv, apscheduler, multipart" >/dev/null 2>&1; then
  if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
    "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  fi
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON_BIN" -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

cleanup() {
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "FastAPI failed to start." >&2
    exit 1
  fi
  sleep 1
done

if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
  echo "FastAPI did not become ready within 30 seconds." >&2
  exit 1
fi

cd "$ROOT_DIR/al-tariq-frontend"
PORT="$FRONTEND_PORT" BACKEND_PORT="$BACKEND_PORT" node server.js &
FRONTEND_PID=$!

sleep 1
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo "Static frontend failed to start." >&2
  exit 1
fi

wait "$FRONTEND_PID"
