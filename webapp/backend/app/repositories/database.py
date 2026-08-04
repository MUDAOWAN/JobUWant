from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.paths import DB_PATH


TASK_SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    city TEXT NOT NULL,
    city_code TEXT NOT NULL DEFAULT '',
    keyword TEXT NOT NULL,
    job_type TEXT NOT NULL,
    expected_job_count INTEGER NOT NULL DEFAULT 0,
    batch_size INTEGER NOT NULL DEFAULT 10,
    source_type TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status_updated
    ON analysis_tasks(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_query
    ON analysis_tasks(city, keyword, job_type);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_source
    ON analysis_tasks(source_type);

CREATE TABLE IF NOT EXISTS task_stage_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT,
    finished_at TEXT,
    elapsed_seconds REAL NOT NULL DEFAULT 0,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES analysis_tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_task_stage_runs_task_stage_status
    ON task_stage_runs(task_id, stage_name, status);
CREATE INDEX IF NOT EXISTS idx_task_stage_runs_task_updated
    ON task_stage_runs(task_id, updated_at);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    stage_run_id INTEGER,
    level TEXT NOT NULL DEFAULT 'info',
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES analysis_tasks(id),
    FOREIGN KEY(stage_run_id) REFERENCES task_stage_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_id
    ON task_events(task_id, id);
CREATE INDEX IF NOT EXISTS idx_task_events_task_type
    ON task_events(task_id, event_type);

CREATE TABLE IF NOT EXISTS analysis_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    search_run_id INTEGER NOT NULL,
    sample_version INTEGER NOT NULL DEFAULT 1,
    selected_count INTEGER NOT NULL DEFAULT 0,
    excluded_count INTEGER NOT NULL DEFAULT 0,
    selected_job_ids_json TEXT NOT NULL DEFAULT '[]',
    excluded_job_ids_json TEXT NOT NULL DEFAULT '[]',
    selection_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES analysis_tasks(id),
    FOREIGN KEY(search_run_id) REFERENCES job_search_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_analysis_samples_task_version
    ON analysis_samples(task_id, sample_version);
CREATE INDEX IF NOT EXISTS idx_analysis_samples_search_run
    ON analysis_samples(search_run_id);

CREATE TABLE IF NOT EXISTS analysis_sample_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER NOT NULL,
    job_detail_id INTEGER NOT NULL,
    selected INTEGER NOT NULL DEFAULT 1,
    match_score REAL NOT NULL DEFAULT 0,
    match_status TEXT NOT NULL DEFAULT 'unscored',
    role_intent TEXT NOT NULL DEFAULT 'unknown',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sample_id) REFERENCES analysis_samples(id),
    FOREIGN KEY(job_detail_id) REFERENCES job_details(id)
);

CREATE INDEX IF NOT EXISTS idx_analysis_sample_items_selected
    ON analysis_sample_items(sample_id, selected);
CREATE INDEX IF NOT EXISTS idx_analysis_sample_items_job
    ON analysis_sample_items(sample_id, job_detail_id);

CREATE TABLE IF NOT EXISTS batch_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    sample_id INTEGER NOT NULL,
    stage_run_id INTEGER,
    batch_index INTEGER NOT NULL,
    batch_size INTEGER NOT NULL,
    job_ids_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending',
    model_name TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cny REAL NOT NULL DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    elapsed_seconds REAL NOT NULL DEFAULT 0,
    error_code TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES analysis_tasks(id),
    FOREIGN KEY(sample_id) REFERENCES analysis_samples(id),
    FOREIGN KEY(stage_run_id) REFERENCES task_stage_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_batch_runs_task_sample_index
    ON batch_runs(task_id, sample_id, batch_index);
CREATE INDEX IF NOT EXISTS idx_batch_runs_task_status
    ON batch_runs(task_id, status);

CREATE TABLE IF NOT EXISTS task_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    artifact_type TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '',
    related_table TEXT NOT NULL DEFAULT '',
    related_id INTEGER,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES analysis_tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_task_artifacts_task_type
    ON task_artifacts(task_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_task_artifacts_related
    ON task_artifacts(related_table, related_id);
'''


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_task_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(TASK_SCHEMA_SQL)
    conn.commit()
