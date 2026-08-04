from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobuwant.ai_job_extract import (
    DEFAULT_EXTRACTOR_NAME,
    DEFAULT_SCHEMA_VERSION,
    count_candidate_jobs,
    extract_jobs_with_openai,
    load_jobs,
    save_extractions,
    store_usage as store_extract_usage,
)
from jobuwant.ai_report_writer import (
    load_report_input,
    save_report,
    store_usage as store_report_usage,
    write_report_with_openai,
)
from jobuwant.analysis_budget import resolve_budget
from jobuwant.boss_adapter import import_boss_json
from jobuwant.config import OpenAISettings
from jobuwant.job_match_score import score_jobs
from jobuwant.job_report import build_report_input, store_report_input


DEFAULT_COLLECT_OUTPUT = Path("ai-param-flow-test/output/hz_agent_intern_40_full_jobs.json")
DEFAULT_SOURCE_TYPE = "boss_hz_agent_intern_20260726_probe40"
DEFAULT_REPORT_INPUT = Path("data/job_report_input_hz_agent_intern_probe40.json")
DEFAULT_REPORT_OUTPUT = Path("data/job_report_hz_agent_intern_probe40.json")


@dataclass(frozen=True)
class PipelineStats:
    source_type: str
    job_count: int
    latest_run_id: int | None
    latest_run_status_counts: dict[str, int]
    latest_run_extraction_count: int
    latest_report_input_id: int | None
    latest_report_id: int | None


def collect_command(
    output_path: Path,
    source_type: str,
    target_count: int,
    page_size: int,
    max_pages: int,
    detail_limit: int,
) -> str:
    return (
        "cd /home/votally/projects/JobUWant/ai-param-flow-test && "
        ".venv/bin/python src/collect_boss_jobs_slow.py "
        f"--target-count {target_count} "
        f"--detail-limit {detail_limit} "
        f"--page-size {page_size} "
        f"--max-pages {max_pages} "
        f"--output {output_path.as_posix()} "
        f"--source-type {source_type}"
    )


def load_collection_preview(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    jobs = payload.get("jobs") if isinstance(payload.get("jobs"), list) else []
    lengths = [len(str(job.get("desc") or "")) for job in jobs if isinstance(job, dict)]
    return {
        "exists": True,
        "path": str(path),
        "query": payload.get("query") or {},
        "stop_reason": payload.get("stop_reason") or "",
        "stats": payload.get("stats") or {},
        "code36_seen": bool(payload.get("code36_seen")),
        "check_page_seen": bool(payload.get("check_page_seen")),
        "job_count": len(jobs),
        "desc_len_min": min(lengths) if lengths else 0,
        "desc_len_max": max(lengths) if lengths else 0,
        "desc_len_under_120": sum(1 for value in lengths if value < 120),
    }


def get_pipeline_stats(conn: sqlite3.Connection, source_type: str) -> PipelineStats:
    job_count = int(
        conn.execute("SELECT COUNT(*) FROM job_details WHERE source_type = ?", (source_type,)).fetchone()[0]
    )
    run = conn.execute(
        """
        SELECT id
        FROM job_search_runs
        WHERE source_type = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_type,),
    ).fetchone()
    latest_run_id = int(run["id"]) if run else None
    status_counts: dict[str, int] = {}
    extraction_count = 0
    if latest_run_id is not None:
        rows = conn.execute(
            """
            SELECT match_status, COUNT(*) AS count
            FROM job_search_run_items
            WHERE search_run_id = ?
            GROUP BY match_status
            ORDER BY match_status
            """,
            (latest_run_id,),
        ).fetchall()
        status_counts = {str(row["match_status"]): int(row["count"]) for row in rows}
        extraction_count = int(
            conn.execute(
                """
                SELECT COUNT(DISTINCT sri.job_detail_id)
                FROM job_search_run_items sri
                JOIN job_extractions je
                  ON je.job_detail_id = sri.job_detail_id
                 AND je.status = 'completed'
                WHERE sri.search_run_id = ?
                """,
                (latest_run_id,),
            ).fetchone()[0]
        )
    report_input = conn.execute(
        """
        SELECT id
        FROM job_report_inputs
        WHERE source_type = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_type,),
    ).fetchone()
    report = conn.execute(
        """
        SELECT id
        FROM job_reports
        WHERE source_type = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_type,),
    ).fetchone()
    return PipelineStats(
        source_type=source_type,
        job_count=job_count,
        latest_run_id=int(report_input["id"]) if False and report_input else latest_run_id,
        latest_run_status_counts=status_counts,
        latest_run_extraction_count=extraction_count,
        latest_report_input_id=int(report_input["id"]) if report_input else None,
        latest_report_id=int(report["id"]) if report else None,
    )


def import_collection(conn: sqlite3.Connection, path: Path, limit: int | None = None) -> dict[str, Any]:
    result = import_boss_json(conn, path, limit=limit)
    return {
        "input_path": str(result.input_path),
        "read_count": result.read_count,
        "normalized_count": result.normalized_count,
        "saved_count": result.saved_count,
        "skipped_count": result.skipped_count,
    }


def score_source(
    conn: sqlite3.Connection,
    source_type: str,
    city: str,
    keyword: str,
    keywords: list[str],
    expected_intent: str,
    allow_intern: bool,
) -> dict[str, Any]:
    return score_jobs(
        conn=conn,
        source_type=source_type,
        target_city=city,
        target_keyword=keyword,
        target_keywords=keywords,
        expected_intent=expected_intent,
        allow_intern=allow_intern,
    )


def extract_next_batch(
    conn: sqlite3.Connection,
    search_run_id: int,
    settings: OpenAISettings,
    match_statuses: list[str],
    batch_size: int,
    budget_tier: str,
    request_timeout: float,
    max_output_tokens: int,
) -> dict[str, Any]:
    candidate_count = count_candidate_jobs(
        conn=conn,
        search_run_id=search_run_id,
        source_type="",
        match_statuses=match_statuses,
        sample_limit=batch_size,
    )
    budget = resolve_budget(budget_tier, max(1, candidate_count))
    max_text_chars = budget.max_text_chars_per_job
    output_tokens = max_output_tokens or budget.max_output_tokens
    jobs = load_jobs(
        conn=conn,
        search_run_id=search_run_id,
        source_type="",
        match_statuses=match_statuses,
        sample_limit=batch_size,
        include_cached=False,
        extractor_name=DEFAULT_EXTRACTOR_NAME,
        schema_version=DEFAULT_SCHEMA_VERSION,
        model_name=settings.model,
        max_text_chars=max_text_chars,
    )
    if not jobs:
        return {"status": "no_jobs", "requested_jobs": 0, "saved_count": 0}
    output, usage, _raw_json = extract_jobs_with_openai(
        jobs=jobs,
        settings=settings,
        budget=budget,
        max_text_chars_per_job=max_text_chars,
        request_timeout=request_timeout,
        max_output_tokens=output_tokens,
    )
    save_summary = save_extractions(
        conn=conn,
        jobs=jobs,
        output=output,
        extractor_name=DEFAULT_EXTRACTOR_NAME,
        schema_version=DEFAULT_SCHEMA_VERSION,
        model_name=settings.model,
        max_text_chars=max_text_chars,
    )
    store_extract_usage(conn, model_name=settings.model, usage=usage)
    return {
        "status": "completed",
        "requested_jobs": len(jobs),
        "returned_jobs": len(output.jobs),
        "saved_count": save_summary["saved_count"],
        "unexpected_job_ids": save_summary["unexpected_job_ids"],
        "budget_tier": budget.tier,
        "usage": usage,
    }


def build_and_store_report_input(
    conn: sqlite3.Connection,
    search_run_id: int,
    source_type: str,
    match_statuses: list[str],
    output_path: Path,
) -> dict[str, Any]:
    payload = build_report_input(
        conn=conn,
        search_run_id=search_run_id,
        source_type=source_type,
        match_statuses=match_statuses,
        top_n=15,
        max_evidence_per_item=1,
    )
    token_budget = int((payload.get("budget") or {}).get("report_token_budget") or 0)
    report_input_id = store_report_input(
        conn=conn,
        payload=payload,
        output_path=output_path,
        token_budget=token_budget,
    )
    return {
        "report_input_id": report_input_id,
        "output": str(output_path),
        "total_jobs": payload["sample"]["total_jobs"],
        "estimated_prompt_tokens": payload["estimated_prompt_tokens"],
        "budget": payload["budget"],
        "evidence_quality": payload["evidence_quality"],
    }


def write_final_report(
    conn: sqlite3.Connection,
    settings: OpenAISettings,
    input_path: Path,
    output_path: Path,
    request_timeout: float,
    max_output_tokens: int,
) -> dict[str, Any]:
    report_input_id, report_input = load_report_input(conn, report_input_id=0, input_path=input_path)
    report, usage, _raw_json = write_report_with_openai(
        report_input=report_input,
        settings=settings,
        request_timeout=request_timeout,
        max_output_tokens=max_output_tokens,
    )
    report_id = save_report(
        conn=conn,
        report_input_id=report_input_id,
        report_input=report_input,
        report=report,
        model_name=settings.model,
        output_path=output_path,
    )
    store_report_usage(conn, model_name=settings.model, usage=usage)
    return {
        "report_id": report_id,
        "title": report.report_title,
        "output": str(output_path),
        "usage": usage,
    }
