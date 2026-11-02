#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${PORT:-3000}"

cd "$ROOT_DIR"

if [ ! -d "frontend/node_modules" ]; then
  (cd frontend && npm ci --no-audit --no-fund)
fi

if ! python -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  python -m pip install -r requirements.txt
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
python -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$ROOT_DIR/frontend"
exec npm run dev -- --hostname 0.0.0.0 --port "$FRONTEND_PORT"
