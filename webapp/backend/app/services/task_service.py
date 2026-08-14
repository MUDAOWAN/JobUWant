from __future__ import annotations

from app.repositories import analysis_tasks
from app.repositories.database import connect
from app.runner import collection_runner, final_report_runner, structuring_runner
from app.schemas.tasks import AnalysisTaskCreate, AnalysisTaskRead, FinalReportRead, JobListRead, ReportInputPreview, SampleConfirmRequest, StructuringStatusRead, TaskDetailRead, TaskEventRead
from app.services import final_report_service, fixture_service, report_input_service, sample_service, scoring_service, structuring_service
from app.services.task_harness import HarnessAction, StageName


def create_task(payload: AnalysisTaskCreate) -> TaskDetailRead:
    conn = connect()
    try:
        return analysis_tasks.create_task(conn, payload)
    finally:
        conn.close()


def list_tasks() -> list[AnalysisTaskRead]:
    conn = connect()
    try:
        live_tasks = analysis_tasks.list_tasks(conn)
    finally:
        conn.close()
    return live_tasks + fixture_service.list_tasks()


def get_task_detail(task_id: str) -> TaskDetailRead:
    if task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        conn = connect()
        try:
            return analysis_tasks.get_task_detail(conn, task_id)
        finally:
            conn.close()
    return fixture_service.get_task_detail(task_id)


def list_events(task_id: str) -> list[TaskEventRead]:
    if task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        conn = connect()
        try:
            return analysis_tasks.list_events(conn, task_id)
        finally:
            conn.close()
    return fixture_service.list_events(task_id)


def list_jobs(
    task_id: str,
    match_status: str | None = None,
    role_intent: str | None = None,
    company_keyword: str | None = None,
    title_keyword: str | None = None,
    selected_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> JobListRead:
    if task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        conn = connect()
        try:
            row_id = analysis_tasks.parse_public_task_id(task_id)
            detail = analysis_tasks.get_task_detail(conn, task_id)
            if detail.task.search_run_id <= 0:
                return JobListRead(task_id=task_id, total=0, limit=limit, offset=offset, rows=[])
            rows = fixture_service.load_job_rows(conn, detail.task.search_run_id)
            selection = analysis_tasks.get_latest_sample_selection(conn, row_id)
            if selection:
                rows = [row.model_copy(update={'selected': bool(selection.get(row.job_id, False))}) for row in rows]
            rows = fixture_service.filter_jobs(
                rows,
                match_status=match_status,
                role_intent=role_intent,
                company_keyword=company_keyword,
                title_keyword=title_keyword,
                selected_only=selected_only,
            )
            safe_limit = min(max(limit, 1), 200)
            safe_offset = max(offset, 0)
            return JobListRead(
                task_id=task_id,
                total=len(rows),
                limit=safe_limit,
                offset=safe_offset,
                rows=rows[safe_offset:safe_offset + safe_limit],
            )
        finally:
            conn.close()
    return fixture_service.list_jobs(
        task_id=task_id,
        match_status=match_status,
        role_intent=role_intent,
        company_keyword=company_keyword,
        title_keyword=title_keyword,
        selected_only=selected_only,
        limit=limit,
        offset=offset,
    )


def get_report_input(task_id: str) -> ReportInputPreview:
    if task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        return report_input_service.get_live_report_input(task_id)
    return fixture_service.get_report_input(task_id)


def get_final_report(task_id: str) -> FinalReportRead:
    if task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        return final_report_service.get_live_final_report(task_id)
    return fixture_service.get_final_report(task_id)


def start_collection(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    conn = connect()
    try:
        detail = analysis_tasks.get_task_detail(conn, task_id)
        validate_collection_inputs(detail)
        updated = analysis_tasks.start_action(
            conn,
            task_id=task_id,
            action=HarnessAction.START_COLLECTION,
            message='采集阶段已启动，执行器已进入本地后台队列。',
            payload={
                'city': detail.task.city,
                'city_code': detail.task.city_code,
                'keyword': detail.task.keyword,
                'job_type': detail.task.job_type,
                'platform_job_type': collection_runner.map_job_type(detail.task.job_type),
                'expected_job_count': detail.task.expected_job_count,
                'source_type': detail.task.source_type,
                'runner_status': 'queued',
            },
        )
    except Exception:
        conn.close()
        raise

    try:
        submitted = collection_runner.submit_collection(task_id)
    except Exception as exc:  # noqa: BLE001
        failure_conn = connect()
        try:
            analysis_tasks.mark_stage_failed(
                failure_conn,
                task_id=task_id,
                stage_name=StageName.COLLECT_JOBS,
                error_code=type(exc).__name__,
                error_message=str(exc)[:1000],
            )
        finally:
            failure_conn.close()
        raise ValueError(f'collection runner submit failed: {exc}') from exc
    finally:
        conn.close()

    if not submitted:
        raise ValueError('collection runner is already active for this task')
    return updated


def validate_collection_inputs(detail: TaskDetailRead) -> None:
    if not detail.task.city_code.strip():
        raise ValueError('city_code is required before starting collection')
    if not detail.task.keyword.strip():
        raise ValueError('keyword is required before starting collection')
    if detail.task.expected_job_count <= 0:
        raise ValueError('expected_job_count must be greater than zero')
    collection_runner.map_job_type(detail.task.job_type)


def cancel_task(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    collection_cancel_requested = collection_runner.cancel_collection(task_id)
    structuring_cancel_requested = structuring_runner.cancel_structuring(task_id)
    final_report_cancel_requested = final_report_runner.cancel_final_report(task_id)
    conn = connect()
    try:
        return analysis_tasks.cancel_task(
            conn,
            task_id=task_id,
            reason='任务已中断，本次未完成的执行结果不会进入后续流程。',
            payload={
                'collection_cancel_requested': collection_cancel_requested,
                'structuring_cancel_requested': structuring_cancel_requested,
                'final_report_cancel_requested': final_report_cancel_requested,
            },
        )
    finally:
        conn.close()


def start_scoring(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return scoring_service.start_scoring(task_id)


def save_sample(task_id: str, payload: SampleConfirmRequest) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return sample_service.save_sample(task_id, payload)


def start_structuring(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return structuring_service.start_structuring(task_id)


def get_structuring_status(task_id: str) -> StructuringStatusRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return structuring_service.get_structuring_status(task_id)


def run_structuring_batches(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return structuring_service.run_structuring_batches(task_id)


def build_report_input(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return report_input_service.build_task_report_input(task_id)


def write_final_report(task_id: str) -> TaskDetailRead:
    if not task_id.startswith(analysis_tasks.LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    return final_report_service.write_final_report(task_id)

