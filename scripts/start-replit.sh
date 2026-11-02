#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${PORT:-3000}"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$ROOT_DIR"

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

if ! "$PYTHON_BIN" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  if [ "$PYTHON_BIN" = "python" ]; then
    python -m venv "$ROOT_DIR/.venv"
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  fi
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON_BIN" -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
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
PORT="$FRONTEND_PORT" BACKEND_PORT="$BACKEND_PORT" exec npm start
