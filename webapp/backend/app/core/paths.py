from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
WEBAPP_ROOT = PROJECT_ROOT / 'webapp'
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'jobuwant.sqlite3'
