#!/usr/bin/env bash
set -euo pipefail

SYSTEM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="${GEODISK_PYTHON:-$SYSTEM_DIR/backend/.venv/bin/python}"

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  BACKEND_PYTHON="$(command -v python3)"
fi

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
  if [[ -n "${WEB_PID:-}" ]]; then kill "$WEB_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

cd "$SYSTEM_DIR/backend"
PYTHONPATH=src "$BACKEND_PYTHON" -m uvicorn geodisk_paper.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!

cd "$SYSTEM_DIR/frontend"
npm run dev &
WEB_PID=$!

echo "GeoDisk system is starting"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://127.0.0.1:8000/docs"
wait "$API_PID" "$WEB_PID"

