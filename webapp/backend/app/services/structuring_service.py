from __future__ import annotations

from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.schemas.tasks import StructuringBatchRead, StructuringStatusRead, TaskDetailRead
from app.runner import structuring_runner
from app.services.task_harness import HarnessAction, StageName, StageStatus
from jobuwant.db import initialize_database as initialize_job_tables


def start_structuring(task_id: str) -> TaskDetailRead:
    conn = connect()
    stage_started = False
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        detail = analysis_tasks.get_task_detail(conn, task_id)
        sample = analysis_tasks.get_latest_sample(conn, row_id)
        sample_id = int(sample.get('sample_id') or 0)
        if sample_id <= 0:
            raise ValueError('sample artifact is required before structuring')
        selected_job_ids = analysis_tasks.list_selected_sample_job_ids(conn, sample_id)
        if not selected_job_ids:
            raise ValueError('confirmed sample does not contain selected jobs')
        batch_size = max(1, int(detail.task.batch_size or 10))
        stage_detail = analysis_tasks.start_action(
            conn,
            task_id=task_id,
            action=HarnessAction.START_STRUCTURING,
            message='AI 结构化批次计划已开始创建。',
            payload={
                'sample_id': sample_id,
                'selected_count': len(selected_job_ids),
                'batch_size': batch_size,
                'runner_status': 'plan_only',
            },
        )
        stage_started = True
        stage_run_id = analysis_tasks.get_stage_run_id(conn, row_id, StageName.AI_STRUCTURING)
        batches = analysis_tasks.create_structuring_batches(
            conn,
            row_id=row_id,
            sample_id=sample_id,
            stage_run_id=stage_run_id,
            job_ids=selected_job_ids,
            batch_size=batch_size,
        )
        output_payload = {
            'sample_id': sample_id,
            'sample_version': int(sample.get('sample_version') or 0),
            'selected_count': len(selected_job_ids),
            'batch_size': batch_size,
            'total_batches': len(batches),
            'runner_status': 'waiting_for_model_approval',
            'model_call_started': False,
        }
        analysis_tasks.record_artifact(
            conn,
            row_id,
            artifact_type='batch_runs',
            path='',
            related_table='analysis_samples',
            related_id=sample_id,
            summary=output_payload,
        )
        conn.commit()
        return analysis_tasks.mark_stage_waiting(
            conn,
            task_id=task_id,
            stage_name=StageName.AI_STRUCTURING,
            message='AI 结构化批次计划已创建，等待用户确认后再调用模型。',
            output_payload=output_payload,
        )
    except Exception as exc:  # noqa: BLE001
        if stage_started:
            try:
                analysis_tasks.mark_stage_failed(
                    conn,
                    task_id=task_id,
                    stage_name=StageName.AI_STRUCTURING,
                    error_code=type(exc).__name__,
                    error_message=str(exc)[:1000],
                )
            except Exception:
                pass
        raise
    finally:
        conn.close()


def get_structuring_status(task_id: str) -> StructuringStatusRead:
    conn = connect()
    try:
        initialize_task_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        analysis_tasks.ensure_task_exists(conn, row_id, task_id)
        sample = analysis_tasks.get_latest_sample(conn, row_id)
        batches = [StructuringBatchRead(**row) for row in analysis_tasks.list_batch_runs(conn, row_id)]
        return StructuringStatusRead(
            task_id=task_id,
            sample_id=int(sample.get('sample_id') or 0),
            sample_version=int(sample.get('sample_version') or 0),
            selected_count=int(sample.get('selected_count') or 0),
            batch_size=max((batch.batch_size for batch in batches), default=0),
            total_batches=len(batches),
            batches=batches,
        )
    finally:
        conn.close()


def run_structuring_batches(task_id: str) -> TaskDetailRead:
    conn = connect()
    try:
        initialize_task_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        analysis_tasks.ensure_task_exists(conn, row_id, task_id)
        statuses = analysis_tasks.get_stage_statuses(conn, row_id)
        if statuses.get(StageName.AI_STRUCTURING.value) != StageStatus.WAITING_FOR_USER.value:
            raise ValueError('ai_structuring must be waiting before batch execution')
        pending_batches = analysis_tasks.list_pending_batch_runs(conn, row_id)
        if not pending_batches:
            raise ValueError('no pending structuring batches are available')
        updated = analysis_tasks.resume_waiting_stage(
            conn,
            task_id=task_id,
            stage_name=StageName.AI_STRUCTURING,
            message='AI 结构化批次执行已进入本地后台队列。',
            input_payload={'pending_batches': len(pending_batches), 'runner_status': 'queued'},
        )
    except Exception:
        conn.close()
        raise

    try:
        submitted = structuring_runner.submit_structuring(task_id)
    except Exception as exc:  # noqa: BLE001
        failure_conn = connect()
        try:
            analysis_tasks.mark_stage_failed(
                failure_conn,
                task_id=task_id,
                stage_name=StageName.AI_STRUCTURING,
                error_code=type(exc).__name__,
                error_message=str(exc)[:1000],
            )
        finally:
            failure_conn.close()
        raise ValueError(f'structuring runner submit failed: {exc}') from exc
    finally:
        conn.close()

    if not submitted:
        raise ValueError('structuring runner is already active for this task')
    return updated
