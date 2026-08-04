#!/usr/bin/env bash
set -euo pipefail
cd /home/votally/projects/JobUWant/webapp/backend
export PYTHONPATH=.
exec /home/votally/projects/JobUWant/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
