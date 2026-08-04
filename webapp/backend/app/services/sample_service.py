from __future__ import annotations

from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.schemas.tasks import SampleConfirmRequest, TaskDetailRead
from app.services.task_harness import HarnessAction, StageName
from jobuwant.db import initialize_database as initialize_job_tables


def save_sample(task_id: str, payload: SampleConfirmRequest) -> TaskDetailRead:
    conn = connect()
    stage_started = False
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        detail = analysis_tasks.get_task_detail(conn, task_id)
        scored_artifact = analysis_tasks.get_latest_artifact(conn, row_id, 'scored_jobs')
        search_run_id = int(scored_artifact.get('related_id') or detail.task.search_run_id or 0)
        if search_run_id <= 0 or scored_artifact.get('related_table') != 'job_search_runs':
            raise ValueError('scored_jobs artifact is required before sample confirmation')

        all_job_ids = analysis_tasks.list_scored_job_ids(conn, search_run_id)
        selected_job_ids, excluded_job_ids = normalize_selection(
            all_job_ids=all_job_ids,
            selected_job_ids=payload.selected_job_ids,
            excluded_job_ids=payload.excluded_job_ids,
        )

        analysis_tasks.start_action(
            conn,
            task_id=task_id,
            action=HarnessAction.SAVE_SAMPLE,
            message='样本确认已开始保存。',
            payload={
                'search_run_id': search_run_id,
                'selected_count': len(selected_job_ids),
                'excluded_count': len(excluded_job_ids),
            },
        )
        stage_started = True
        sample = analysis_tasks.create_analysis_sample(
            conn,
            row_id=row_id,
            search_run_id=search_run_id,
            selected_job_ids=selected_job_ids,
            excluded_job_ids=excluded_job_ids,
            selection_note=payload.selection_note.strip(),
        )
        return analysis_tasks.mark_stage_completed(
            conn,
            task_id=task_id,
            stage_name=StageName.CONFIRM_SAMPLE,
            output_payload=sample,
            artifact_type='sample',
            artifact_path='',
            artifact_summary=sample,
            related_table='analysis_samples',
            related_id=int(sample['sample_id']),
        )
    except Exception as exc:  # noqa: BLE001
        if stage_started:
            try:
                analysis_tasks.mark_stage_failed(
                    conn,
                    task_id=task_id,
                    stage_name=StageName.CONFIRM_SAMPLE,
                    error_code=type(exc).__name__,
                    error_message=str(exc)[:1000],
                )
            except Exception:
                pass
        raise
    finally:
        conn.close()


def normalize_selection(
    all_job_ids: list[int],
    selected_job_ids: list[int],
    excluded_job_ids: list[int],
) -> tuple[list[int], list[int]]:
    all_set = set(all_job_ids)
    if not all_set:
        raise ValueError('no scored jobs are available for sample confirmation')
    selected = dedupe_positive_ids(selected_job_ids)
    explicit_excluded = dedupe_positive_ids(excluded_job_ids)
    if not selected:
        raise ValueError('selected_job_ids must contain at least one job id')
    unknown = (set(selected) | set(explicit_excluded)) - all_set
    if unknown:
        raise ValueError(f'job ids do not belong to this task: {sorted(unknown)}')
    overlap = set(selected) & set(explicit_excluded)
    if overlap:
        raise ValueError(f'job ids cannot be both selected and excluded: {sorted(overlap)}')
    excluded = [job_id for job_id in all_job_ids if job_id not in set(selected)]
    return selected, excluded


def dedupe_positive_ids(values: list[int]) -> list[int]:
    output: list[int] = []
    seen: set[int] = set()
    for value in values:
        job_id = int(value)
        if job_id <= 0 or job_id in seen:
            continue
        seen.add(job_id)
        output.append(job_id)
    return output
