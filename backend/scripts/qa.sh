#!/usr/bin/env bash
set -euo pipefail

python -m ruff format --check .
python -m ruff check .
python -m mypy app tests
python -m pytest
