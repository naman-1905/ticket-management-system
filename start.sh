#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to start the frontend and backend." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (the 'docker compose' command)." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "No .env file found; creating one from .env.example. Update JWT_SECRET before production use."
  cp .env.example .env
fi

if ! docker network inspect naman-private-network >/dev/null 2>&1; then
  docker network create naman-private-network >/dev/null
fi

echo "Starting PostgreSQL, Redis, RabbitMQ, backend, and frontend..."
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"

exec docker compose --profile local up --build
