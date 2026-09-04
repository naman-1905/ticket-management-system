#!/usr/bin/env bash

set -e

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "Frontend dependencies not found."
    echo "Install them first with:"
    echo "  npm install"
    exit 1
fi

echo "Starting Next.js frontend on http://localhost:3000..."
cd "$FRONTEND_DIR"
npm run dev
