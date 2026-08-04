from __future__ import annotations

from typing import Any

from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.runner import final_report_runner
from app.schemas.tasks import FinalReportRead, TaskDetailRead
from app.services.task_harness import HarnessAction, StageName
from jobuwant.db import initialize_database as initialize_job_tables


def write_final_report(task_id: str) -> TaskDetailRead:
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
        updated = analysis_tasks.start_action(
            conn,
            task_id=task_id,
            action=HarnessAction.WRITE_FINAL_REPORT,
            message='最终报告生成已进入本地后台队列。',
            payload={
                'report_input_id': report_input_id,
                'report_input_path': str(artifact.get('path') or ''),
                'runner_status': 'queued',
            },
        )
    except Exception:
        conn.close()
        raise

    try:
        submitted = final_report_runner.submit_final_report(task_id)
    except Exception as exc:  # noqa: BLE001
        failure_conn = connect()
        try:
            analysis_tasks.mark_stage_failed(
                failure_conn,
                task_id=task_id,
                stage_name=StageName.WRITE_FINAL_REPORT,
                error_code=type(exc).__name__,
                error_message=str(exc)[:1000],
            )
        finally:
            failure_conn.close()
        raise ValueError(f'final report runner submit failed: {exc}') from exc
    finally:
        conn.close()

    if not submitted:
        raise ValueError('final report runner is already active for this task')
    return updated


def get_live_final_report(task_id: str) -> FinalReportRead:
    conn = connect()
    try:
        initialize_task_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        analysis_tasks.ensure_task_exists(conn, row_id, task_id)
        artifact = analysis_tasks.get_latest_artifact(conn, row_id, 'report')
        path = str(artifact.get('path') or '')
        if not path:
            raise FileNotFoundError(f'final report is not generated for task: {task_id}')
        payload = final_report_runner.read_report_payload(conn, artifact)
        return final_report_from_payload(task_id=task_id, path=path, payload=payload)
    finally:
        conn.close()


def final_report_from_payload(task_id: str, path: str, payload: dict[str, Any]) -> FinalReportRead:
    sections = {
        key: value
        for key, value in payload.items()
        if key not in {'report_title', 'audience_summary'}
    }
    return FinalReportRead(
        task_id=task_id,
        path=path,
        report_title=str(payload.get('report_title') or ''),
        audience_summary=str(payload.get('audience_summary') or ''),
        sections=sections,
        raw=payload,
    )