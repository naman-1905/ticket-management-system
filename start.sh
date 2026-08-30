#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "Starting Ticket Management System..."

# Backend
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "Backend virtual environment not found."
    echo "Create it first with:"
    echo "  python3 -m venv backend/.venv"
    exit 1
fi

source "$BACKEND_DIR/.venv/bin/activate"

echo "Starting FastAPI backend on http://127.0.0.1:8000..."
(
    cd "$BACKEND_DIR"
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &

BACKEND_PID=$!

# Frontend
echo "Starting Next.js frontend on http://localhost:3000..."
(
    cd "$FRONTEND_DIR"
    npm run dev
) &

FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping services..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

wait