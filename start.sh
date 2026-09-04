#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Ticket Management System..."

# Backend
"$PROJECT_ROOT/backend/start-backend.sh" &
BACKEND_PID=$!

# Frontend
"$PROJECT_ROOT/frontend/start-frontend.sh" &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping services..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

wait