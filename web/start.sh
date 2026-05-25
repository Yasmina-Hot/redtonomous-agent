#!/usr/bin/env bash
# Redtonomous Web — start all three services
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "⚡ Starting Redtonomous Web..."

# ── Backend ──
echo "  [1/3] Installing Python backend deps..."
cd "$ROOT/api"
pip install -q -r requirements.txt
echo "  [1/3] Starting FastAPI backend on :8000..."
uvicorn main:app --port 8000 --reload &
BACKEND_PID=$!

# ── Chat UI ──
echo "  [2/3] Installing Chat UI deps..."
cd "$ROOT/chat"
npm install --silent
echo "  [2/3] Starting Chat UI on :3000..."
npm run dev &
CHAT_PID=$!

# ── RDX ──
echo "  [3/3] Installing RDX deps..."
cd "$ROOT/rdx"
npm install --silent
echo "  [3/3] Starting RDX on :3001..."
npm run dev &
RDX_PID=$!

echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │  Chat UI  →  http://localhost:3000       │"
echo "  │  RDX      →  http://localhost:3001       │"
echo "  │  API      →  http://localhost:8000       │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  Press Ctrl-C to stop all services."

trap "kill $BACKEND_PID $CHAT_PID $RDX_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
