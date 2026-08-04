from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.core.paths import DATA_DIR, PROJECT_ROOT
from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.schemas.tasks import ReportInputPreview, TaskDetailRead
from app.services.task_harness import HarnessAction, StageName
from jobuwant.db import initialize_database as initialize_job_tables

PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
if PROJECT_ROOT_TEXT not in sys.path:
    sys.path.append(PROJECT_ROOT_TEXT)

from jobuwant.job_report import build_report_input, store_report_input  # noqa: E402

REPORT_INPUT_FILENAME = 'report_input.json'


def build_task_report_input(task_id: str) -> TaskDetailRead:
    conn = connect()
    stage_started = False
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        task_row = analysis_tasks.get_task_row(conn, row_id)
        detail = analysis_tasks.get_task_detail(conn, task_id)
        sample = analysis_tasks.get_latest_sample(conn, row_id)
        sample_id = int(sample.get('sample_id') or 0)
        search_run_id = int(sample.get('search_run_id') or detail.task.search_run_id or 0)
        if sample_id <= 0 or search_run_id <= 0:
            raise ValueError('confirmed sample is required before report input generation')
        extraction_artifact = analysis_tasks.get_latest_artifact(conn, row_id, 'extractions')
        if int(extraction_artifact.get('related_id') or 0) != sample_id:
            raise ValueError('completed extraction artifact is required before report input generation')
        selected_job_ids = analysis_tasks.list_selected_sample_job_ids(conn, sample_id)
        if not selected_job_ids:
            raise ValueError('confirmed sample does not contain selected jobs')

        analysis_tasks.start_action(
            conn,
            task_id=task_id,
            action=HarnessAction.BUILD_REPORT_INPUT,
            message='报告输入生成已开始。',
            payload={
                'sample_id': sample_id,
                'search_run_id': search_run_id,
                'selected_count': len(selected_job_ids),
            },
        )
        stage_started = True
        output_path = DATA_DIR / 'task_artifacts' / task_id / REPORT_INPUT_FILENAME
        payload = build_report_input(
            conn=conn,
            search_run_id=search_run_id,
            source_type=str(task_row.get('source_type') or ''),
            match_statuses=['strong_match', 'review', 'weak_match'],
            top_n=15,
            max_evidence_per_item=1,
            job_ids=selected_job_ids,
        )
        token_budget = int((payload.get('budget') or {}).get('report_token_budget') or 0)
        report_input_id = store_report_input(
            conn=conn,
            payload=payload,
            output_path=output_path,
            token_budget=token_budget,
        )
        output_payload = {
            'report_input_id': report_input_id,
            'sample_id': sample_id,
            'search_run_id': search_run_id,
            'output_path': str(output_path),
            'total_jobs': int((payload.get('sample') or {}).get('total_jobs') or 0),
            'estimated_prompt_tokens': int(payload.get('estimated_prompt_tokens') or 0),
            'token_budget': token_budget,
            'evidence_quality': dict(payload.get('evidence_quality') or {}),
        }
        return analysis_tasks.mark_stage_completed(
            conn,
            task_id=task_id,
            stage_name=StageName.BUILD_REPORT_INPUT,
            output_payload=output_payload,
            artifact_type='report_input',
            artifact_path=str(output_path),
            artifact_summary=output_payload,
            related_table='job_report_inputs',
            related_id=report_input_id,
        )
    except Exception as exc:  # noqa: BLE001
        if stage_started:
            try:
                analysis_tasks.mark_stage_failed(
                    conn,
                    task_id=task_id,
                    stage_name=StageName.BUILD_REPORT_INPUT,
                    error_code=type(exc).__name__,
                    error_message=str(exc)[:1000],
                )
            except Exception:
                pass
        raise
    finally:
        conn.close()


def get_live_report_input(task_id: str) -> ReportInputPreview:
    conn = connect()
    try:
        initialize_task_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        analysis_tasks.ensure_task_exists(conn, row_id, task_id)
        artifact = analysis_tasks.get_latest_artifact(conn, row_id, 'report_input')
        path = str(artifact.get('path') or '')
        if not path:
            raise FileNotFoundError(f'report input is not generated for task: {task_id}')
        payload = read_report_input_payload(conn, artifact)
        return preview_from_payload(task_id=task_id, path=path, payload=payload)
    finally:
        conn.close()


def read_report_input_payload(conn: Any, artifact: dict[str, Any]) -> dict[str, Any]:
    report_input_id = int(artifact.get('related_id') or 0)
    if report_input_id > 0 and artifact.get('related_table') == 'job_report_inputs':
        row = conn.execute('SELECT input_json FROM job_report_inputs WHERE id = ?', (report_input_id,)).fetchone()
        if row is not None:
            return parse_json_object(row['input_json'])
    path = Path(str(artifact.get('path') or ''))
    if not path.exists():
        raise FileNotFoundError(f'report input file not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def preview_from_payload(task_id: str, path: str, payload: dict[str, Any]) -> ReportInputPreview:
    return ReportInputPreview(
        task_id=task_id,
        path=path,
        query=dict(payload.get('query') or {}),
        sample=dict(payload.get('sample') or {}),
        technical_terms_top=list(payload.get('technical_terms_top') or [])[:15],
        salary_summary=dict(payload.get('salary_summary') or {}),
        evidence_quality=dict(payload.get('evidence_quality') or {}),
        estimated_prompt_tokens=int(payload.get('estimated_prompt_tokens') or 0),
        raw=payload,
    )


def parse_json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or '{}'))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
