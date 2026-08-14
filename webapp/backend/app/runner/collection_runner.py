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
_CANCEL_REQUESTS: set[str] = set()
_ACTIVE_PROCESSES: dict[str, subprocess.Popen[str]] = {}


class CollectionCanceled(RuntimeError):
    pass


class CollectionLoginTimeout(RuntimeError):
    pass


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
            _ACTIVE_PROCESSES.pop(task_id, None)
            _CANCEL_REQUESTS.discard(task_id)


def cancel_collection(task_id: str) -> bool:
    with _LOCK:
        active = task_id in _ACTIVE_TASKS
        _CANCEL_REQUESTS.add(task_id)
        process = _ACTIVE_PROCESSES.get(task_id)
    if process is not None and process.poll() is None:
        process.terminate()
    return active


def _is_cancel_requested(task_id: str) -> bool:
    with _LOCK:
        return task_id in _CANCEL_REQUESTS


def _remove_output_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


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
        if str(result.get('stop_reason') or '') == 'login_timeout':
            _remove_output_file(request.output_path)
            raise CollectionLoginTimeout('waiting for BOSS login timed out')
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
    except CollectionCanceled as exc:
        _remove_output_file(request.output_path)
        conn = connect()
        try:
            initialize_task_tables(conn)
            analysis_tasks.cancel_task(
                conn,
                task_id=task_id,
                reason='岗位信息搜集已中断，本次输出已清理。',
                payload={'output_path': str(request.output_path), 'reason': str(exc)},
            )
        finally:
            conn.close()
    except CollectionLoginTimeout as exc:
        conn = connect()
        try:
            initialize_task_tables(conn)
            analysis_tasks.mark_stage_failed(
                conn,
                task_id=task_id,
                stage_name=StageName.COLLECT_JOBS,
                error_code='LoginTimeout',
                error_message='等待 BOSS 扫码登录超时，请重新开始查找。',
            )
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        if _is_cancel_requested(task_id):
            _remove_output_file(request.output_path)
            conn = connect()
            try:
                initialize_task_tables(conn)
                analysis_tasks.cancel_task(
                    conn,
                    task_id=task_id,
                    reason='岗位信息搜集已中断，本次输出已清理。',
                    payload={'output_path': str(request.output_path), 'reason': str(exc)},
                )
            finally:
                conn.close()
            return
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
    if _is_cancel_requested(request.task_id):
        _remove_output_file(request.output_path)
        raise CollectionCanceled('collection canceled before process start')
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
    with _LOCK:
        _ACTIVE_PROCESSES[request.task_id] = process
    assert process.stdout is not None
    try:
        for line in process.stdout:
            if _is_cancel_requested(request.task_id):
                process.terminate()
                break
            handle_progress_line(request.task_id, request.task_row_id, line.rstrip('\n'))
        return_code = process.wait()
    finally:
        with _LOCK:
            if _ACTIVE_PROCESSES.get(request.task_id) is process:
                _ACTIVE_PROCESSES.pop(request.task_id, None)
    if _is_cancel_requested(request.task_id):
        _remove_output_file(request.output_path)
        raise CollectionCanceled('collection canceled')
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
    elif line.startswith('AUTH_OPENING '):
        event_type = 'collection_login_opening'
        payload = parse_line_payload(line.removeprefix('AUTH_OPENING '))
    elif line.startswith('AUTH_CHECKING '):
        event_type = 'collection_login_checking'
        payload = parse_line_payload(line.removeprefix('AUTH_CHECKING '))
    elif line.startswith('AUTH_REQUIRED '):
        event_type = 'collection_login_required'
        payload = parse_line_payload(line.removeprefix('AUTH_REQUIRED '))
    elif line.startswith('AUTH_WAITING '):
        event_type = 'collection_login_waiting'
        payload = parse_line_payload(line.removeprefix('AUTH_WAITING '))
    elif line.startswith('AUTH_READY '):
        event_type = 'collection_login_ready'
        payload = parse_line_payload(line.removeprefix('AUTH_READY '))
    elif line.startswith('AUTH_TIMEOUT '):
        event_type = 'collection_login_timeout'
        payload = parse_line_payload(line.removeprefix('AUTH_TIMEOUT '))
    if not event_type:
        if not should_record_process_output(line):
            return
        event_type = 'collection_process_output'
        payload = {'line': line[:500]}

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


def should_record_process_output(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    markers = (
        'Traceback',
        'Error',
        'Exception',
        'RuntimeError',
        'ValueError',
        'SyntaxError',
        'ImportError',
        'ModuleNotFoundError',
        'Drission',
    )
    return any(marker in text for marker in markers)


def parse_line_payload(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {'raw': value[:500]}
    return parsed if isinstance(parsed, dict) else {'raw': value[:500]}


def build_progress_message(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == 'collection_list_page':
        page = payload.get('page', '')
        count = payload.get('job_count', 0)
        added = payload.get('added_unique', 0)
        return f'列表页 {page} 返回 {count} 条，新增 {added} 条。'
    if event_type == 'collection_detail':
        index = payload.get('index', '')
        length = payload.get('final_desc_len', 0)
        return f'岗位详情 {index} 已处理，正文长度 {length}。'
    if event_type == 'collection_login_opening':
        return '正在打开 BOSS 窗口；如果出现扫码登录，请完成扫码，系统会自动继续。'
    if event_type == 'collection_login_checking':
        return '正在确认 BOSS 登录状态。'
    if event_type == 'collection_login_required':
        return '请在弹出的 BOSS 窗口扫码登录，登录成功后会自动继续查找。'
    if event_type == 'collection_login_waiting':
        elapsed = payload.get('elapsed_seconds', 0)
        return f'正在等待扫码登录，已等待 {elapsed} 秒。'
    if event_type == 'collection_login_ready':
        return 'BOSS 登录状态已确认，继续查找岗位。'
    if event_type == 'collection_login_timeout':
        return '等待 BOSS 扫码登录超时，请重新开始查找。'
    if event_type == 'collection_process_output':
        line = str(payload.get('line') or '')[:460]
        return f'执行输出：{line}'
    return str(payload.get('line') or '')[:500]


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
