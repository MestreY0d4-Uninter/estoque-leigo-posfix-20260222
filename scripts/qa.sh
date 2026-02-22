#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  uv venv -q
fi

uv pip install -q -e "./backend[dev]"

uv run ruff format --check backend
uv run ruff check backend
uv run mypy backend/app
uv run pytest -q
