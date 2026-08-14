from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.core.paths import DATA_DIR, PROJECT_ROOT
from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.services import report_input_service
from app.services.task_harness import StageName
from jobuwant.db import initialize_database as initialize_job_tables

PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
if PROJECT_ROOT_TEXT not in sys.path:
    sys.path.append(PROJECT_ROOT_TEXT)

from jobuwant.ai_report_writer import (  # noqa: E402
    load_settings,
    save_report,
    store_usage,
    write_report_with_openai,
)

REPORT_FILENAME = 'final_report.json'

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='jobuwant-final-report')
_LOCK = threading.Lock()
_ACTIVE_TASKS: set[str] = set()
_CANCEL_REQUESTS: set[str] = set()


class FinalReportCanceled(RuntimeError):
    pass


def submit_final_report(task_id: str) -> bool:
    with _LOCK:
        if task_id in _ACTIVE_TASKS:
            return False
        _ACTIVE_TASKS.add(task_id)
    future = _EXECUTOR.submit(_run_and_release, task_id)
    future.add_done_callback(_consume_background_exception)
    return True


def _run_and_release(task_id: str) -> None:
    try:
        run_final_report_for_task(task_id)
    finally:
        with _LOCK:
            _ACTIVE_TASKS.discard(task_id)
            _CANCEL_REQUESTS.discard(task_id)



def cancel_final_report(task_id: str) -> bool:
    with _LOCK:
        active = task_id in _ACTIVE_TASKS
        if active:
            _CANCEL_REQUESTS.add(task_id)
    return active


def _is_cancel_requested(task_id: str) -> bool:
    with _LOCK:
        return task_id in _CANCEL_REQUESTS


def _consume_background_exception(future: Future[None]) -> None:
    try:
        future.result()
    except Exception:
        pass


def run_final_report_for_task(task_id: str) -> None:
    conn = connect()
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        analysis_tasks.ensure_task_exists(conn, row_id, task_id)
        artifact = analysis_tasks.get_latest_artifact(conn, row_id, 'report_input')
        report_input_id = int(artifact.get('related_id') or 0)
        if report_input_id <= 0 or artifact.get('related_table') != 'job_report_inputs':
            raise ValueError('report input artifact is required before final report generation')
        report_input = report_input_service.read_report_input_payload(conn, artifact)
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
            event_type='final_report_runner_started',
            message='最终报告生成执行器已开始运行。',
            payload={'report_input_id': report_input_id, 'model': settings.model},
        )
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.close()
        _fail_stage(task_id, type(exc).__name__, str(exc)[:1000])
        return

    try:
        if _is_cancel_requested(task_id):
            raise FinalReportCanceled('final report canceled')
        output_path = DATA_DIR / 'task_artifacts' / task_id / REPORT_FILENAME
        report, usage, _raw_json = write_report_with_openai(
            report_input=report_input,
            settings=settings,
            request_timeout=180.0,
            max_output_tokens=3500,
        )
        if _is_cancel_requested(task_id):
            raise FinalReportCanceled('final report canceled')
        report_id = save_report(
            conn=conn,
            report_input_id=report_input_id,
            report_input=report_input,
            report=report,
            model_name=settings.model,
            output_path=output_path,
        )
        store_usage(conn, model_name=settings.model, usage=usage)
        output_payload = {
            'report_id': report_id,
            'report_input_id': report_input_id,
            'search_run_id': int((report_input.get('query') or {}).get('search_run_id') or 0),
            'output_path': str(output_path),
            'report_title': report.report_title,
            'model_name': settings.model,
            'usage': {
                'model_calls': int(usage.get('model_calls') or 0),
                'input_tokens': int(usage.get('input_tokens') or 0),
                'output_tokens': int(usage.get('output_tokens') or 0),
                'estimated_cny': float(usage.get('estimated_cny') or 0),
            },
        }
        analysis_tasks.mark_stage_completed(
            conn,
            task_id=task_id,
            stage_name=StageName.WRITE_FINAL_REPORT,
            output_payload=output_payload,
            artifact_type='report',
            artifact_path=str(output_path),
            artifact_summary=output_payload,
            related_table='job_reports',
            related_id=report_id,
        )
    except FinalReportCanceled:
        analysis_tasks.cancel_task(
            conn,
            task_id=task_id,
            reason='分析已中断，最终报告不会写入任务产物。',
            payload={'stage': StageName.WRITE_FINAL_REPORT.value},
        )
    except Exception as exc:  # noqa: BLE001
        analysis_tasks.mark_stage_failed(
            conn,
            task_id=task_id,
            stage_name=StageName.WRITE_FINAL_REPORT,
            error_code=type(exc).__name__,
            error_message=str(exc)[:1000],
        )
    finally:
        conn.close()


def _fail_stage(task_id: str, error_code: str, error_message: str) -> None:
    conn = connect()
    try:
        initialize_task_tables(conn)
        analysis_tasks.mark_stage_failed(
            conn,
            task_id=task_id,
            stage_name=StageName.WRITE_FINAL_REPORT,
            error_code=error_code,
            error_message=error_message,
        )
    finally:
        conn.close()


def read_report_payload(conn: Any, artifact: dict[str, Any]) -> dict[str, Any]:
    report_id = int(artifact.get('related_id') or 0)
    if report_id > 0 and artifact.get('related_table') == 'job_reports':
        row = conn.execute('SELECT output_json FROM job_reports WHERE id = ?', (report_id,)).fetchone()
        if row is not None:
            return parse_json_object(row['output_json'])
    path = Path(str(artifact.get('path') or ''))
    if not path.exists():
        raise FileNotFoundError(f'final report file not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def parse_json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or '{}'))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


