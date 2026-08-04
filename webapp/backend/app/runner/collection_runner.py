from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any, Callable

from app.core.paths import DATA_DIR, PROJECT_ROOT
from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.services.task_harness import StageName

PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
if PROJECT_ROOT_TEXT not in sys.path:
    sys.path.append(PROJECT_ROOT_TEXT)

from jobuwant.boss_adapter import import_boss_json  # noqa: E402
from jobuwant.db import initialize_database as initialize_job_tables  # noqa: E402


@dataclass(frozen=True)
class CollectionRunRequest:
    task_id: str
    task_row_id: int
    city: str
    city_code: str
    keyword: str
    job_type: str
    platform_job_type: str
    expected_job_count: int
    source_type: str
    output_path: Path
    page_size: int
    max_pages: int
    detail_limit: int


_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='jobuwant-collection')
_LOCK = threading.Lock()
_ACTIVE_TASKS: set[str] = set()


def submit_collection(task_id: str) -> bool:
    with _LOCK:
        if task_id in _ACTIVE_TASKS:
            return False
        _ACTIVE_TASKS.add(task_id)
    future = _EXECUTOR.submit(_run_and_release, task_id)
    future.add_done_callback(_consume_background_exception)
    return True


def _run_and_release(task_id: str) -> None:
    try:
        run_collection_for_task(task_id)
    finally:
        with _LOCK:
            _ACTIVE_TASKS.discard(task_id)


def _consume_background_exception(future: Future[None]) -> None:
    try:
        future.result()
    except Exception:
        pass


def build_collection_request(row: Any) -> CollectionRunRequest:
    task_id = analysis_tasks.public_task_id(int(row['id']))
    city_code = str(row['city_code'] or '').strip()
    if not city_code:
        raise ValueError('city_code is required before starting collection')
    keyword = str(row['keyword'] or '').strip()
    if not keyword:
        raise ValueError('keyword is required before starting collection')
    expected_job_count = int(row['expected_job_count'] or 0)
    if expected_job_count <= 0:
        raise ValueError('expected_job_count must be greater than zero')

    page_size = min(30, max(1, min(expected_job_count, 15)))
    max_pages = max(1, ceil(expected_job_count / page_size))
    source_type = str(row['source_type'] or '').strip() or f'webapp_task_{row["id"]}'
    output_path = DATA_DIR / 'task_artifacts' / task_id / 'collection.json'

    return CollectionRunRequest(
        task_id=task_id,
        task_row_id=int(row['id']),
        city=str(row['city'] or '').strip(),
        city_code=city_code,
        keyword=keyword,
        job_type=str(row['job_type'] or 'any').strip() or 'any',
        platform_job_type=map_job_type(str(row['job_type'] or 'any')),
        expected_job_count=expected_job_count,
        source_type=source_type,
        output_path=output_path,
        page_size=page_size,
        max_pages=max_pages,
        detail_limit=expected_job_count,
    )


def map_job_type(job_type: str) -> str:
    normalized = job_type.strip().lower()
    if normalized == 'intern':
        return '1902'
    if normalized in {'any', 'full_time'}:
        return ''
    raise ValueError(f'unsupported job_type: {job_type}')


def run_collection_for_task(task_id: str) -> None:
    conn = connect()
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        row = conn.execute('SELECT * FROM analysis_tasks WHERE id = ?', (row_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        request = build_collection_request(row)
        analysis_tasks.append_event(
            conn,
            task_id=row_id,
            event_type='collection_runner_started',
            message='采集执行器已开始运行。',
            payload={'output_path': str(request.output_path), 'source_type': request.source_type},
        )
        conn.commit()
    finally:
        conn.close()

    try:
        result = execute_collection_script(request)
        conn = connect()
        try:
            initialize_task_tables(conn)
            initialize_job_tables(conn)
            import_summary = import_boss_json(conn, request.output_path)
            search_run_id = record_collection_search_run(conn, request, result, import_summary)
            output_payload = build_output_payload(request, result, import_summary, search_run_id)
            analysis_tasks.mark_stage_completed(
                conn,
                task_id=task_id,
                stage_name=StageName.COLLECT_JOBS,
                output_payload=output_payload,
                artifact_type='search_run',
                artifact_path=str(request.output_path),
                artifact_summary=output_payload,
                related_table='job_search_runs',
                related_id=search_run_id,
            )
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        conn = connect()
        try:
            initialize_task_tables(conn)
            analysis_tasks.mark_stage_failed(
                conn,
                task_id=task_id,
                stage_name=StageName.COLLECT_JOBS,
                error_code=type(exc).__name__,
                error_message=str(exc)[:1000],
            )
        finally:
            conn.close()


def execute_collection_script(request: CollectionRunRequest) -> dict[str, Any]:
    script_dir = PROJECT_ROOT / 'ai-param-flow-test'
    python_path = script_dir / '.venv' / 'bin' / 'python'
    executable = str(python_path if python_path.exists() else Path(sys.executable))
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        'src/collect_boss_jobs_slow.py',
        '--city-code',
        request.city_code,
        '--query',
        request.keyword,
        '--job-type',
        request.platform_job_type,
        '--target-count',
        str(request.expected_job_count),
        '--detail-limit',
        str(request.detail_limit),
        '--page-size',
        str(request.page_size),
        '--max-pages',
        str(request.max_pages),
        '--source-type',
        request.source_type,
        '--cache-prefix',
        f'webapp-{request.task_id}',
        '--output',
        str(request.output_path),
    ]
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([PROJECT_ROOT_TEXT, env.get('PYTHONPATH', '')]).strip(os.pathsep)

    process = subprocess.Popen(
        command,
        cwd=script_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    assert process.stdout is not None
    for line in process.stdout:
        handle_progress_line(request.task_id, request.task_row_id, line.rstrip('\n'))
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f'collection script exited with code {return_code}')
    if not request.output_path.exists():
        raise FileNotFoundError(f'collection output not found: {request.output_path}')
    payload = json.loads(request.output_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('collection output root must be an object')
    return payload


def handle_progress_line(task_id: str, row_id: int, line: str) -> None:
    event_type = ''
    payload: dict[str, Any] = {'line': line[:500]}
    if line.startswith('LIST_PAGE '):
        event_type = 'collection_list_page'
        payload = parse_line_payload(line.removeprefix('LIST_PAGE '))
    elif line.startswith('DETAIL '):
        event_type = 'collection_detail'
        payload = parse_line_payload(line.removeprefix('DETAIL '))
    if not event_type:
        return

    conn = connect()
    try:
        analysis_tasks.append_event(
            conn,
            task_id=row_id,
            event_type=event_type,
            message=build_progress_message(event_type, payload),
            payload=payload,
        )
        conn.commit()
    finally:
        conn.close()


def parse_line_payload(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {'raw': value[:500]}
    return parsed if isinstance(parsed, dict) else {'raw': value[:500]}


def build_progress_message(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == 'collection_list_page':
        return f"列表页 {payload.get('page', '')} 返回 {payload.get('job_count', 0)} 条，新增 {payload.get('added_unique', 0)} 条。"
    return f"岗位详情 {payload.get('index', '')} 已处理，正文长度 {payload.get('final_desc_len', 0)}。"


def record_collection_search_run(
    conn: Any,
    request: CollectionRunRequest,
    result: dict[str, Any],
    import_summary: Any,
) -> int:
    stats = result.get('stats') if isinstance(result.get('stats'), dict) else {}
    saved_count = int(getattr(import_summary, 'saved_count', 0))
    status = 'collected' if saved_count >= request.expected_job_count else 'collection_incomplete'
    cursor = conn.execute(
        '''
        INSERT INTO job_search_runs (
            source_type, source_name, query_city, query_keyword, query_keywords_json,
            input_path, requested_limit, collected_count, analysis_ready_count,
            config_json, notes, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            request.source_type,
            'boss_collection_runner',
            request.city,
            request.keyword,
            json.dumps([request.keyword], ensure_ascii=True),
            str(request.output_path),
            request.expected_job_count,
            saved_count,
            0,
            json.dumps(
                {
                    'city_code': request.city_code,
                    'job_type': request.job_type,
                    'platform_job_type': request.platform_job_type,
                    'page_size': request.page_size,
                    'max_pages': request.max_pages,
                    'detail_limit': request.detail_limit,
                    'stop_reason': result.get('stop_reason') or '',
                    'stats': stats,
                },
                ensure_ascii=True,
            ),
            'created by webapp collection runner',
            status,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def build_output_payload(
    request: CollectionRunRequest,
    result: dict[str, Any],
    import_summary: Any,
    search_run_id: int,
) -> dict[str, Any]:
    stats = result.get('stats') if isinstance(result.get('stats'), dict) else {}
    saved_count = int(getattr(import_summary, 'saved_count', 0))
    return {
        'search_run_id': search_run_id,
        'source_type': request.source_type,
        'output_path': str(request.output_path),
        'target_count': request.expected_job_count,
        'collected_count': saved_count,
        'read_count': int(getattr(import_summary, 'read_count', 0)),
        'normalized_count': int(getattr(import_summary, 'normalized_count', 0)),
        'saved_count': saved_count,
        'skipped_count': int(getattr(import_summary, 'skipped_count', 0)),
        'stop_reason': str(result.get('stop_reason') or ''),
        'incomplete': saved_count < request.expected_job_count,
        'stats': stats,
    }
