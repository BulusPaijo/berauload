#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Test modules create their own temporary SQLite databases; production is not used.
if python3 -c "import pytest, httpx, fastapi, sqlalchemy" >/dev/null 2>&1; then
  PYTHONPATH="$ROOT/backend" python3 -m pytest -q backend/tests
else
  echo "Menyiapkan virtualenv QA terisolasi..."
  python3 -m venv .qa-venv
  .qa-venv/bin/python -m pip install -q -r backend/requirements-dev.txt
  PYTHONPATH="$ROOT/backend" .qa-venv/bin/python -m pytest -q backend/tests
fi
python3 -m compileall -q backend/app
