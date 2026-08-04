from __future__ import annotations

import sqlite3
from pathlib import Path


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "jobuwant.sqlite3"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS candidate_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            snippet TEXT NOT NULL DEFAULT '',
            source_type TEXT NOT NULL DEFAULT 'unknown',
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS candidate_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            possible_category TEXT NOT NULL DEFAULT 'unknown',
            related_direction TEXT NOT NULL DEFAULT '',
            evidence_url TEXT NOT NULL,
            matched_keywords TEXT NOT NULL DEFAULT '',
            confidence_label TEXT NOT NULL DEFAULT 'low',
            official_domain TEXT NOT NULL DEFAULT '',
            official_domain_verified INTEGER NOT NULL DEFAULT 0,
            verification_notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'candidate',
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_name, evidence_url)
        );

        CREATE TABLE IF NOT EXISTS job_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'unknown',
            company_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            city TEXT NOT NULL,
            publish_time TEXT,
            content_hash TEXT NOT NULL,
            structured_fields_json TEXT NOT NULL DEFAULT '{}',
            summary TEXT NOT NULL DEFAULT '',
            confidence_label TEXT NOT NULL DEFAULT 'low',
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_url, content_hash)
        );

        CREATE TABLE IF NOT EXISTS job_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_company_id INTEGER,
            company_name TEXT NOT NULL,
            job_title_guess TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            snippet TEXT NOT NULL DEFAULT '',
            source_type TEXT NOT NULL DEFAULT 'unknown',
            source_confidence TEXT NOT NULL DEFAULT 'low',
            status TEXT NOT NULL DEFAULT 'candidate',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_name, url),
            FOREIGN KEY(candidate_company_id) REFERENCES candidate_companies(id)
        );

        CREATE TABLE IF NOT EXISTS job_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_lead_id INTEGER,
            candidate_company_id INTEGER,
            company_name TEXT NOT NULL,
            job_title TEXT NOT NULL,
            city TEXT NOT NULL DEFAULT '',
            recruitment_stage TEXT NOT NULL DEFAULT '',
            responsibilities TEXT NOT NULL DEFAULT '',
            requirements TEXT NOT NULL DEFAULT '',
            technical_keywords_json TEXT NOT NULL DEFAULT '[]',
            original_url TEXT NOT NULL DEFAULT '',
            raw_job_text TEXT NOT NULL,
            raw_text_hash TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'unknown',
            source_confidence TEXT NOT NULL DEFAULT 'low',
            parse_confidence TEXT NOT NULL DEFAULT 'low',
            source_metadata_json TEXT NOT NULL DEFAULT '{}',
            quality_status TEXT NOT NULL DEFAULT 'unreviewed',
            quality_flags_json TEXT NOT NULL DEFAULT '[]',
            quality_score INTEGER NOT NULL DEFAULT 0,
            quality_notes TEXT NOT NULL DEFAULT '',
            quality_updated_at TEXT,
            review_status TEXT NOT NULL DEFAULT 'auto_parsed',
            error_message TEXT NOT NULL DEFAULT '',
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_name, original_url, raw_text_hash),
            FOREIGN KEY(job_lead_id) REFERENCES job_leads(id),
            FOREIGN KEY(candidate_company_id) REFERENCES candidate_companies(id)
        );

        CREATE TABLE IF NOT EXISTS parse_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_lead_id INTEGER,
            job_detail_id INTEGER,
            stage TEXT NOT NULL DEFAULT 'job_detail_parse',
            model_name TEXT,
            input_hash TEXT NOT NULL DEFAULT '',
            input_chars INTEGER NOT NULL DEFAULT 0,
            output_json TEXT NOT NULL DEFAULT '{}',
            validation_errors TEXT NOT NULL DEFAULT '',
            parse_confidence TEXT NOT NULL DEFAULT 'low',
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_lead_id) REFERENCES job_leads(id),
            FOREIGN KEY(job_detail_id) REFERENCES job_details(id)
        );

        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage TEXT NOT NULL,
            model_name TEXT,
            model_calls INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            estimated_cny REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_search_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL DEFAULT 'unknown',
            source_name TEXT NOT NULL DEFAULT '',
            query_city TEXT NOT NULL DEFAULT '',
            query_keyword TEXT NOT NULL DEFAULT '',
            query_keywords_json TEXT NOT NULL DEFAULT '[]',
            input_path TEXT NOT NULL DEFAULT '',
            requested_limit INTEGER NOT NULL DEFAULT 0,
            collected_count INTEGER NOT NULL DEFAULT 0,
            analysis_ready_count INTEGER NOT NULL DEFAULT 0,
            config_json TEXT NOT NULL DEFAULT '{}',
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_search_run_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_run_id INTEGER NOT NULL,
            job_detail_id INTEGER NOT NULL,
            source_rank INTEGER NOT NULL DEFAULT 0,
            match_score REAL NOT NULL DEFAULT 0,
            match_status TEXT NOT NULL DEFAULT 'unscored',
            role_intent TEXT NOT NULL DEFAULT 'unknown',
            match_reasons_json TEXT NOT NULL DEFAULT '[]',
            review_reasons_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(search_run_id, job_detail_id),
            FOREIGN KEY(search_run_id) REFERENCES job_search_runs(id),
            FOREIGN KEY(job_detail_id) REFERENCES job_details(id)
        );

        CREATE TABLE IF NOT EXISTS job_extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_detail_id INTEGER NOT NULL,
            extractor_name TEXT NOT NULL DEFAULT 'unknown',
            schema_version TEXT NOT NULL DEFAULT 'v1',
            input_hash TEXT NOT NULL DEFAULT '',
            output_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'completed',
            validation_errors TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_detail_id, extractor_name, schema_version, input_hash),
            FOREIGN KEY(job_detail_id) REFERENCES job_details(id)
        );

        CREATE TABLE IF NOT EXISTS job_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_detail_id INTEGER NOT NULL,
            search_run_id INTEGER,
            term TEXT NOT NULL,
            normalized_term TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'unknown',
            source_field TEXT NOT NULL DEFAULT '',
            evidence TEXT NOT NULL DEFAULT '',
            confidence_label TEXT NOT NULL DEFAULT 'medium',
            extractor_name TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_detail_id, search_run_id, normalized_term, category, source_field),
            FOREIGN KEY(job_detail_id) REFERENCES job_details(id),
            FOREIGN KEY(search_run_id) REFERENCES job_search_runs(id)
        );

        CREATE TABLE IF NOT EXISTS job_report_inputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_run_id INTEGER,
            source_type TEXT NOT NULL DEFAULT 'unknown',
            report_type TEXT NOT NULL DEFAULT 'job_market_v1',
            input_hash TEXT NOT NULL,
            input_json TEXT NOT NULL DEFAULT '{}',
            token_budget INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(report_type, input_hash),
            FOREIGN KEY(search_run_id) REFERENCES job_search_runs(id)
        );

        CREATE TABLE IF NOT EXISTS job_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_input_id INTEGER,
            search_run_id INTEGER,
            source_type TEXT NOT NULL DEFAULT 'unknown',
            model_name TEXT NOT NULL DEFAULT '',
            report_type TEXT NOT NULL DEFAULT 'job_market_v1',
            output_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(report_input_id) REFERENCES job_report_inputs(id),
            FOREIGN KEY(search_run_id) REFERENCES job_search_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_job_search_runs_source
            ON job_search_runs(source_type, query_city, query_keyword);
        CREATE INDEX IF NOT EXISTS idx_job_search_run_items_job
            ON job_search_run_items(job_detail_id);
        CREATE INDEX IF NOT EXISTS idx_job_terms_lookup
            ON job_terms(normalized_term, category);
        """
    )
    _ensure_column(conn, "candidate_companies", "official_domain", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "candidate_companies", "official_domain_verified", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "candidate_companies", "verification_notes", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "job_details", "source_metadata_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(conn, "job_details", "quality_status", "TEXT NOT NULL DEFAULT 'unreviewed'")
    _ensure_column(conn, "job_details", "quality_flags_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(conn, "job_details", "quality_score", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "job_details", "quality_notes", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "job_details", "quality_updated_at", "TEXT")
    _ensure_column(conn, "job_details", "last_match_score", "REAL NOT NULL DEFAULT 0")
    _ensure_column(conn, "job_details", "last_match_status", "TEXT NOT NULL DEFAULT 'unscored'")
    _ensure_column(conn, "job_details", "last_match_reasons_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(conn, "job_details", "last_match_updated_at", "TEXT")
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
