from __future__ import annotations

import sys
from typing import Any

from app.core.paths import PROJECT_ROOT
from app.repositories import analysis_tasks
from app.repositories.database import connect, initialize_task_tables
from app.schemas.tasks import TaskDetailRead
from app.services.task_harness import HarnessAction, StageName

PROJECT_ROOT_TEXT = str(PROJECT_ROOT)
if PROJECT_ROOT_TEXT not in sys.path:
    sys.path.append(PROJECT_ROOT_TEXT)

from jobuwant.db import initialize_database as initialize_job_tables  # noqa: E402
from jobuwant.job_match_score import score_jobs  # noqa: E402


def start_scoring(task_id: str) -> TaskDetailRead:
    conn = connect()
    stage_started = False
    try:
        initialize_task_tables(conn)
        initialize_job_tables(conn)
        row_id = analysis_tasks.parse_public_task_id(task_id)
        detail = analysis_tasks.get_task_detail(conn, task_id)
        artifact = analysis_tasks.get_latest_artifact(conn, row_id, 'search_run')
        search_run_id = int(artifact.get('related_id') or 0)
        if search_run_id <= 0 or artifact.get('related_table') != 'job_search_runs':
            raise ValueError('collection search_run artifact is required before scoring')

        analysis_tasks.start_action(
            conn,
            task_id=task_id,
            action=HarnessAction.START_SCORING,
            message='本地评分已开始。',
            payload={
                'search_run_id': search_run_id,
                'source_type': detail.task.source_type,
                'city': detail.task.city,
                'keyword': detail.task.keyword,
                'job_type': detail.task.job_type,
            },
        )
        stage_started = True

        score_summary = score_jobs(
            conn=conn,
            source_type=detail.task.source_type,
            target_city=detail.task.city,
            target_keyword=detail.task.keyword,
            target_keywords=[],
            expected_intent=expected_intent_for_job_type(detail.task.job_type),
            allow_intern=allow_intern_for_job_type(detail.task.job_type),
            limit=0,
            existing_run_id=search_run_id,
        )
        output_payload = normalize_score_summary(score_summary)
        return analysis_tasks.mark_stage_completed(
            conn,
            task_id=task_id,
            stage_name=StageName.SCORE_JOBS,
            output_payload=output_payload,
            artifact_type='scored_jobs',
            artifact_path=str(artifact.get('path') or ''),
            artifact_summary=output_payload,
            related_table='job_search_runs',
            related_id=search_run_id,
        )
    except Exception as exc:  # noqa: BLE001
        if stage_started:
            try:
                analysis_tasks.mark_stage_failed(
                    conn,
                    task_id=task_id,
                    stage_name=StageName.SCORE_JOBS,
                    error_code=type(exc).__name__,
                    error_message=str(exc)[:1000],
                )
            except Exception:
                pass
        raise
    finally:
        conn.close()


def expected_intent_for_job_type(job_type: str) -> str:
    normalized = job_type.strip().lower()
    if normalized == 'intern':
        return 'intern'
    if normalized == 'full_time':
        return 'engineering'
    return 'any'


def allow_intern_for_job_type(job_type: str) -> bool:
    return job_type.strip().lower() in {'intern', 'any'}


def normalize_score_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        'search_run_id': int(summary.get('search_run_id') or 0),
        'source_type': str(summary.get('source_type') or ''),
        'target_city': str(summary.get('target_city') or ''),
        'target_keyword': str(summary.get('target_keyword') or ''),
        'query_terms': list(summary.get('query_terms') or []),
        'evaluated_count': int(summary.get('evaluated_count') or 0),
        'match_status_counts': dict(summary.get('match_status_counts') or {}),
        'role_intent_counts': dict(summary.get('role_intent_counts') or {}),
        'average_score': float(summary.get('average_score') or 0),
        'top_matches': list(summary.get('top_matches') or []),
    }

