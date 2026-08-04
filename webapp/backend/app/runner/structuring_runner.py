from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.core.paths import PROJECT_ROOT
from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.services.task_harness import StageName, StageStatus

PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
if PROJECT_ROOT_TEXT not in sys.path:
    sys.path.append(PROJECT_ROOT_TEXT)

from jobuwant.ai_job_extract import (  # noqa: E402
    DEFAULT_EXTRACTOR_NAME,
    DEFAULT_SCHEMA_VERSION,
    SourceJob,
    extract_jobs_with_openai,
    save_extractions,
    store_usage,
    load_settings,
)
from jobuwant.analysis_budget import resolve_budget  # noqa: E402
from jobuwant.db import initialize_database as initialize_job_tables  # noqa: E402


@dataclass(frozen=True)
class StructuringBatchRequest:
    task_id: str
    task_row_id: int
    sample_id: int
    search_run_id: int
    batch_id: int
    batch_index: int
    job_ids: list[int]
    model_name: str
    budget_tier: str = 'auto'
    request_timeout: float = 120.0
    max_output_tokens: int = 0


_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='jobuwant-structuring')
_LOCK = threading.Lock()
_ACTIVE_TASKS: set[str] = set()


def submit_structuring(task_id: str) -> bool:
    with _LOCK:
        if task_id in _ACTIVE_TASKS:
            return False
        _ACTIVE_TASKS.add(task_id)
    future = _EXECUTOR.submit(_run_and_release, task_id)
    future.add_done_callback(_consume_background_exception)
    return True


def _run_and_release(task_id: str) -> None:
    try:
        run_structuring_for_task(task_id)
    finally:
        with _LOCK:
            _ACTIVE_TASKS.discard(task_id)


def _consume_background_exception(future: Future[None]) -> None:
    try:
        future.result()
    except Exception:
        pass


def run_structuring_for_task(task_id: str) -> None:
    conn = connect()
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        sample = analysis_tasks.get_latest_sample(conn, row_id)
        sample_id = int(sample.get('sample_id') or 0)
        search_run_id = int(sample.get('search_run_id') or 0)
        if sample_id <= 0 or search_run_id <= 0:
            raise ValueError('confirmed sample is required before structuring execution')
        pending_batches = analysis_tasks.list_pending_batch_runs(conn, row_id)
        if not pending_batches:
            raise ValueError('no pending structuring batches are available')
        settings = load_settings(
            api_key=None,
            base_url=None,
            model=None,
            secrets_path=PROJECT_ROOT / '.streamlit' / 'secrets.toml',
            estimated_cny_per_call=0.1,
        )
        analysis_tasks.append_event(
            conn,
            task_id=row_id,
            event_type='ai_structuring_runner_started',
            message='AI 结构化执行器已开始运行。',
            payload={'sample_id': sample_id, 'batch_count': len(pending_batches), 'model': settings.model},
        )
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.close()
        _fail_stage(task_id, type(exc).__name__, str(exc)[:1000])
        return

    try:
        completed = 0
        failed = 0
        for batch in pending_batches:
            request = StructuringBatchRequest(
                task_id=task_id,
                task_row_id=row_id,
                sample_id=sample_id,
                search_run_id=search_run_id,
                batch_id=int(batch['batch_id']),
                batch_index=int(batch['batch_index']),
                job_ids=[int(job_id) for job_id in batch['job_ids']],
                model_name=settings.model,
            )
            analysis_tasks.mark_batch_running(conn, request.batch_id)
            analysis_tasks.append_event(
                conn,
                task_id=row_id,
                event_type='ai_structuring_batch_started',
                message=f"AI 结构化批次 {request.batch_index} 已开始。",
                payload={'batch_id': request.batch_id, 'job_ids': request.job_ids},
            )
            conn.commit()
            try:
                summary = execute_structuring_batch(conn, request)
                analysis_tasks.mark_batch_completed(
                    conn,
                    batch_id=request.batch_id,
                    model_name=str(summary.get('model_name') or request.model_name),
                    input_tokens=int(summary.get('input_tokens') or 0),
                    output_tokens=int(summary.get('output_tokens') or 0),
                    estimated_cny=float(summary.get('estimated_cny') or 0),
                )
                completed += 1
                analysis_tasks.append_event(
                    conn,
                    task_id=row_id,
                    event_type='ai_structuring_batch_completed',
                    message=f"AI 结构化批次 {request.batch_index} 已完成。",
                    payload={'batch_id': request.batch_id, **summary},
                )
                conn.commit()
            except Exception as exc:  # noqa: BLE001
                failed += 1
                analysis_tasks.mark_batch_failed(conn, request.batch_id, type(exc).__name__, str(exc)[:1000])
                analysis_tasks.append_event(
                    conn,
                    task_id=row_id,
                    level='error',
                    event_type='ai_structuring_batch_failed',
                    message=str(exc)[:1000],
                    payload={'batch_id': request.batch_id, 'error_code': type(exc).__name__},
                )
                conn.commit()
                break

        status_counts = analysis_tasks.count_batch_statuses(conn, row_id)
        output_payload = {
            'sample_id': sample_id,
            'search_run_id': search_run_id,
            'completed_batches': completed,
            'failed_batches': failed,
            'batch_status_counts': status_counts,
        }
        if failed:
            analysis_tasks.mark_stage_failed(
                conn,
                task_id=task_id,
                stage_name=StageName.AI_STRUCTURING,
                error_code='BatchFailed',
                error_message='one or more structuring batches failed',
            )
        else:
            analysis_tasks.mark_stage_completed(
                conn,
                task_id=task_id,
                stage_name=StageName.AI_STRUCTURING,
                output_payload=output_payload,
                artifact_type='extractions',
                artifact_path='',
                artifact_summary=output_payload,
                related_table='analysis_samples',
                related_id=sample_id,
            )
    finally:
        conn.close()


def execute_structuring_batch(conn: Any, request: StructuringBatchRequest) -> dict[str, Any]:
    settings = load_settings(
        api_key=None,
        base_url=None,
        model=None,
        secrets_path=PROJECT_ROOT / '.streamlit' / 'secrets.toml',
        estimated_cny_per_call=0.1,
    )
    jobs = load_source_jobs_for_batch(conn, request.search_run_id, request.job_ids)
    if not jobs:
        raise ValueError(f'no jobs found for batch {request.batch_id}')
    budget = resolve_budget(request.budget_tier, len(jobs))
    max_text_chars = budget.max_text_chars_per_job
    max_output_tokens = request.max_output_tokens or budget.max_output_tokens
    output, usage, _raw_json = extract_jobs_with_openai(
        jobs=jobs,
        settings=settings,
        budget=budget,
        max_text_chars_per_job=max_text_chars,
        request_timeout=request.request_timeout,
        max_output_tokens=max_output_tokens,
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
    store_usage(conn, model_name=settings.model, usage=usage)
    return {
        'model_name': settings.model,
        'requested_jobs': len(jobs),
        'returned_jobs': len(output.jobs),
        'saved_count': int(save_summary.get('saved_count') or 0),
        'unexpected_job_ids': list(save_summary.get('unexpected_job_ids') or []),
        'input_tokens': int(usage.get('input_tokens') or 0),
        'output_tokens': int(usage.get('output_tokens') or 0),
        'estimated_cny': float(usage.get('estimated_cny') or 0),
    }


def load_source_jobs_for_batch(conn: Any, search_run_id: int, job_ids: list[int]) -> list[SourceJob]:
    if not job_ids:
        return []
    placeholders = ','.join('?' for _ in job_ids)
    rows = conn.execute(
        f'''
        SELECT
            jd.id,
            jd.company_name,
            jd.job_title,
            jd.city,
            jd.raw_job_text,
            jd.raw_text_hash,
            jd.technical_keywords_json,
            jd.source_metadata_json,
            sri.match_score,
            sri.match_status,
            sri.role_intent,
            jsr.query_city,
            jsr.query_keyword
        FROM job_search_run_items sri
        JOIN job_details jd ON jd.id = sri.job_detail_id
        JOIN job_search_runs jsr ON jsr.id = sri.search_run_id
        WHERE sri.search_run_id = ?
          AND jd.id IN ({placeholders})
        ORDER BY sri.source_rank, jd.id
        ''',
        (search_run_id, *job_ids),
    ).fetchall()
    by_id = {int(row['id']): row_to_source_job(row) for row in rows}
    return [by_id[job_id] for job_id in job_ids if job_id in by_id]


def row_to_source_job(row: Any) -> SourceJob:
    metadata = parse_json_object(row['source_metadata_json'])
    return SourceJob(
        job_id=int(row['id']),
        company_name=str(row['company_name'] or ''),
        job_title=str(row['job_title'] or ''),
        city=str(row['city'] or ''),
        salary=str(metadata.get('salary') or ''),
        experience=str(metadata.get('experience') or ''),
        education=str(metadata.get('education') or ''),
        skills=parse_json_list(row['technical_keywords_json']),
        raw_text_hash=str(row['raw_text_hash'] or ''),
        raw_job_text=str(row['raw_job_text'] or ''),
        match_score=float(row['match_score'] or 0),
        match_status=str(row['match_status'] or ''),
        role_intent_hint=str(row['role_intent'] or ''),
        query_city=str(row['query_city'] or ''),
        query_keyword=str(row['query_keyword'] or ''),
    )


def parse_json_object(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or '{}'))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_json_list(value: object) -> list[str]:
    try:
        parsed = json.loads(str(value or '[]'))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _fail_stage(task_id: str, error_code: str, error_message: str) -> None:
    conn = connect()
    try:
        initialize_task_tables(conn)
        analysis_tasks.mark_stage_failed(
            conn,
            task_id=task_id,
            stage_name=StageName.AI_STRUCTURING,
            error_code=error_code,
            error_message=error_message,
        )
    finally:
        conn.close()
