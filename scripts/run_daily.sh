#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
mkdir -p logs
exec "$PROJECT_DIR/.venv/bin/python" -m etl.pipeline >> "logs/etl-$(date +%Y%m%d-%H%M%S).log" 2>&1
