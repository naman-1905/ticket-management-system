#!/usr/bin/env bash

set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "Backend virtual environment not found."
    echo "Create it first with:"
    echo "  python3 -m venv .venv"
    exit 1
fi

source "$BACKEND_DIR/.venv/bin/activate"

echo "Starting FastAPI backend on http://127.0.0.1:8000..."
cd "$BACKEND_DIR"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
