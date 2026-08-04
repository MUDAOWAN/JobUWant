from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.repositories.database import initialize_task_tables
from app.schemas.tasks import AnalysisTaskCreate, AnalysisTaskRead, FixtureBinding, TaskDetailRead, TaskEventRead, TaskStageRunRead
from app.services.task_harness import HarnessAction, StageName, StageStatus, TaskStatus, assert_action_allowed, derive_task_status, list_stage_specs

LIVE_TASK_PREFIX = 'task-'


def public_task_id(row_id: int) -> str:
    return f'{LIVE_TASK_PREFIX}{row_id}'


def parse_public_task_id(task_id: str) -> int:
    if not task_id.startswith(LIVE_TASK_PREFIX):
        raise KeyError(task_id)
    raw_id = task_id.removeprefix(LIVE_TASK_PREFIX)
    if not raw_id.isdigit():
        raise KeyError(task_id)
    return int(raw_id)


def create_task(conn: sqlite3.Connection, payload: AnalysisTaskCreate) -> TaskDetailRead:
    initialize_task_tables(conn)
    task_name = payload.task_name.strip()
    city = payload.city.strip()
    city_code = payload.city_code.strip()
    keyword = payload.keyword.strip()
    source_type = payload.source_type.strip()
    notes = payload.notes.strip()
    if not task_name:
        task_name = f'{city} {keyword} 岗位分析'
    with conn:
        cursor = conn.execute(
            '''
            INSERT INTO analysis_tasks (
                task_name, city, city_code, keyword, job_type, expected_job_count,
                batch_size, source_type, status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                task_name,
                city,
                city_code,
                keyword,
                payload.job_type,
                payload.expected_job_count,
                payload.batch_size,
                source_type,
                TaskStatus.READY.value,
                notes,
            ),
        )
        row_id = int(cursor.lastrowid)
        if not source_type:
            source_type = f'webapp_task_{row_id}'
            conn.execute('UPDATE analysis_tasks SET source_type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (source_type, row_id))
        for spec in list_stage_specs():
            conn.execute(
                '''
                INSERT INTO task_stage_runs (task_id, stage_name, status, input_json, output_json)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    row_id,
                    spec.name.value,
                    StageStatus.PENDING.value,
                    json.dumps({'stage_order': spec.order, 'action': spec.action.value if spec.action else None}, ensure_ascii=False),
                    json.dumps({'label': spec.label, 'description': spec.description}, ensure_ascii=False),
                ),
            )
        append_event(
            conn,
            task_id=row_id,
            event_type='task_created',
            message='分析任务已创建，等待开始采集岗位。',
            payload={'task_public_id': public_task_id(row_id), 'source_type': source_type},
        )
    return get_task_detail(conn, public_task_id(row_id))




def start_action(conn: sqlite3.Connection, task_id: str, action: HarnessAction, message: str, payload: dict[str, Any] | None = None) -> TaskDetailRead:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    ensure_task_exists(conn, row_id, task_id)
    stage_statuses = get_stage_statuses(conn, row_id)
    spec = assert_action_allowed(action, stage_statuses)
    with conn:
        stage_run_id = mark_stage_running(conn, row_id, spec.name, input_payload=payload or {})
        conn.execute('UPDATE analysis_tasks SET status = ?, started_at = COALESCE(started_at, CURRENT_TIMESTAMP), updated_at = CURRENT_TIMESTAMP WHERE id = ?', (TaskStatus.RUNNING.value, row_id))
        append_event(
            conn,
            task_id=row_id,
            stage_run_id=stage_run_id,
            event_type=f'{spec.name.value}_started',
            message=message,
            payload={'action': action.value, **(payload or {})},
        )
    return get_task_detail(conn, task_id)


def mark_stage_running(conn: sqlite3.Connection, row_id: int, stage_name: StageName, input_payload: dict[str, Any] | None = None) -> int:
    stage_run_id = get_stage_run_id(conn, row_id, stage_name)
    conn.execute(
        '''
        UPDATE task_stage_runs
        SET status = ?, started_at = COALESCE(started_at, CURRENT_TIMESTAMP), updated_at = CURRENT_TIMESTAMP,
            input_json = ?, error_code = '', error_message = ''
        WHERE id = ?
        ''',
        (StageStatus.RUNNING.value, json.dumps(input_payload or {}, ensure_ascii=False), stage_run_id),
    )
    return stage_run_id


def mark_stage_completed(
    conn: sqlite3.Connection,
    task_id: str,
    stage_name: StageName,
    output_payload: dict[str, Any] | None = None,
    artifact_type: str = '',
    artifact_path: str = '',
    artifact_summary: dict[str, Any] | None = None,
    related_table: str = '',
    related_id: int | None = None,
) -> TaskDetailRead:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    ensure_task_exists(conn, row_id, task_id)
    stage_run_id = get_stage_run_id(conn, row_id, stage_name)
    with conn:
        conn.execute(
            '''
            UPDATE task_stage_runs
            SET status = ?, finished_at = CURRENT_TIMESTAMP,
                elapsed_seconds = CASE
                    WHEN started_at IS NULL THEN elapsed_seconds
                    ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400 AS REAL)
                END,
                output_json = ?, error_code = '', error_message = '', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (StageStatus.COMPLETED.value, json.dumps(output_payload or {}, ensure_ascii=False), stage_run_id),
        )
        if artifact_type:
            record_artifact(
                conn,
                row_id,
                artifact_type=artifact_type,
                path=artifact_path,
                related_table=related_table,
                related_id=related_id,
                summary=artifact_summary or output_payload or {},
            )
        append_event(
            conn,
            task_id=row_id,
            stage_run_id=stage_run_id,
            event_type=f'{stage_name.value}_completed',
            message=f'{stage_name.value} completed.',
            payload=output_payload or {},
        )
        refresh_task_status(conn, row_id)
    return get_task_detail(conn, task_id)


def mark_stage_failed(conn: sqlite3.Connection, task_id: str, stage_name: StageName, error_code: str, error_message: str) -> TaskDetailRead:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    ensure_task_exists(conn, row_id, task_id)
    stage_run_id = get_stage_run_id(conn, row_id, stage_name)
    with conn:
        conn.execute(
            '''
            UPDATE task_stage_runs
            SET status = ?, finished_at = CURRENT_TIMESTAMP, error_code = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (StageStatus.FAILED.value, error_code, error_message, stage_run_id),
        )
        conn.execute('UPDATE analysis_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (TaskStatus.FAILED.value, row_id))
        append_event(
            conn,
            task_id=row_id,
            stage_run_id=stage_run_id,
            level='error',
            event_type=f'{stage_name.value}_failed',
            message=error_message,
            payload={'error_code': error_code},
        )
    return get_task_detail(conn, task_id)

def resume_waiting_stage(
    conn: sqlite3.Connection,
    task_id: str,
    stage_name: StageName,
    message: str,
    input_payload: dict[str, Any] | None = None,
) -> TaskDetailRead:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    ensure_task_exists(conn, row_id, task_id)
    stage_statuses = get_stage_statuses(conn, row_id)
    if stage_statuses.get(stage_name.value) != StageStatus.WAITING_FOR_USER.value:
        raise ValueError(f'stage must be waiting before resume: {stage_name.value}')
    with conn:
        stage_run_id = mark_stage_running(conn, row_id, stage_name, input_payload=input_payload or {})
        conn.execute('UPDATE analysis_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (TaskStatus.RUNNING.value, row_id))
        append_event(
            conn,
            task_id=row_id,
            stage_run_id=stage_run_id,
            event_type=f'{stage_name.value}_resumed',
            message=message,
            payload=input_payload or {},
        )
    return get_task_detail(conn, task_id)

def mark_stage_waiting(
    conn: sqlite3.Connection,
    task_id: str,
    stage_name: StageName,
    message: str,
    output_payload: dict[str, Any] | None = None,
) -> TaskDetailRead:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    ensure_task_exists(conn, row_id, task_id)
    stage_run_id = get_stage_run_id(conn, row_id, stage_name)
    with conn:
        conn.execute(
            '''
            UPDATE task_stage_runs
            SET status = ?, output_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (StageStatus.WAITING_FOR_USER.value, json.dumps(output_payload or {}, ensure_ascii=False), stage_run_id),
        )
        append_event(
            conn,
            task_id=row_id,
            stage_run_id=stage_run_id,
            event_type=f'{stage_name.value}_waiting',
            message=message,
            payload=output_payload or {},
        )
        refresh_task_status(conn, row_id)
    return get_task_detail(conn, task_id)


def get_stage_statuses(conn: sqlite3.Connection, row_id: int) -> dict[str, str]:
    rows = conn.execute('SELECT stage_name, status FROM task_stage_runs WHERE task_id = ?', (row_id,)).fetchall()
    return {str(row['stage_name']): str(row['status']) for row in rows}


def get_stage_run_id(conn: sqlite3.Connection, row_id: int, stage_name: StageName) -> int:
    row = conn.execute('SELECT id FROM task_stage_runs WHERE task_id = ? AND stage_name = ?', (row_id, stage_name.value)).fetchone()
    if row is None:
        raise KeyError(f'{public_task_id(row_id)}:{stage_name.value}')
    return int(row['id'])


def record_artifact(
    conn: sqlite3.Connection,
    row_id: int,
    artifact_type: str,
    path: str = '',
    related_table: str = '',
    related_id: int | None = None,
    summary: dict[str, Any] | None = None,
) -> int:
    cursor = conn.execute(
        '''
        INSERT INTO task_artifacts (task_id, artifact_type, path, related_table, related_id, summary_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (row_id, artifact_type, path, related_table, related_id, json.dumps(summary or {}, ensure_ascii=False)),
    )
    return int(cursor.lastrowid)


def refresh_task_status(conn: sqlite3.Connection, row_id: int) -> TaskStatus:
    status = derive_task_status(get_stage_statuses(conn, row_id))
    conn.execute('UPDATE analysis_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (status.value, row_id))
    return status


def ensure_task_exists(conn: sqlite3.Connection, row_id: int, public_id: str) -> None:
    exists = conn.execute('SELECT 1 FROM analysis_tasks WHERE id = ?', (row_id,)).fetchone()
    if exists is None:
        raise KeyError(public_id)


def list_tasks(conn: sqlite3.Connection) -> list[AnalysisTaskRead]:
    initialize_task_tables(conn)
    rows = conn.execute(
        '''
        SELECT *
        FROM analysis_tasks
        ORDER BY datetime(updated_at) DESC, id DESC
        '''
    ).fetchall()
    return [row_to_task_read(conn, row) for row in rows]


def get_task_detail(conn: sqlite3.Connection, task_id: str) -> TaskDetailRead:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    row = conn.execute('SELECT * FROM analysis_tasks WHERE id = ?', (row_id,)).fetchone()
    if row is None:
        raise KeyError(task_id)
    stages = list_stage_runs(conn, row_id)
    stage_statuses = {stage.stage_name: stage.status for stage in stages}
    derived_status = derive_task_status(stage_statuses).value
    if row['status'] != derived_status:
        conn.execute('UPDATE analysis_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (derived_status, row_id))
        conn.commit()
        row = conn.execute('SELECT * FROM analysis_tasks WHERE id = ?', (row_id,)).fetchone()
    search_run_id = live_task_metrics(conn, row_id)['search_run_id']
    return TaskDetailRead(
        task=row_to_task_read(conn, row),
        stages=stages,
        match_status_counts=count_run_field(conn, search_run_id, 'match_status') if search_run_id else {},
        role_intent_counts=count_run_field(conn, search_run_id, 'role_intent') if search_run_id else {},
        artifact_paths=list_artifact_paths(conn, row_id),
    )


def list_stage_runs(conn: sqlite3.Connection, row_id: int) -> list[TaskStageRunRead]:
    rows = conn.execute(
        '''
        SELECT stage_name, status, elapsed_seconds, output_json, error_message
        FROM task_stage_runs
        WHERE task_id = ?
        ORDER BY id
        ''',
        (row_id,),
    ).fetchall()
    return [stage_row_to_read(row) for row in rows]


def list_events(conn: sqlite3.Connection, task_id: str) -> list[TaskEventRead]:
    initialize_task_tables(conn)
    row_id = parse_public_task_id(task_id)
    exists = conn.execute('SELECT 1 FROM analysis_tasks WHERE id = ?', (row_id,)).fetchone()
    if exists is None:
        raise KeyError(task_id)
    rows = conn.execute(
        '''
        SELECT id, level, event_type, message, payload_json, created_at
        FROM task_events
        WHERE task_id = ?
        ORDER BY id
        ''',
        (row_id,),
    ).fetchall()
    return [event_row_to_read(row) for row in rows]


def append_event(
    conn: sqlite3.Connection,
    task_id: int,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
    level: str = 'info',
    stage_run_id: int | None = None,
) -> int:
    cursor = conn.execute(
        '''
        INSERT INTO task_events (task_id, stage_run_id, level, event_type, message, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (task_id, stage_run_id, level, event_type, message, json.dumps(payload or {}, ensure_ascii=False)),
    )
    return int(cursor.lastrowid)


def list_artifact_paths(conn: sqlite3.Connection, row_id: int) -> dict[str, str]:
    rows = conn.execute(
        '''
        SELECT artifact_type, path
        FROM task_artifacts
        WHERE task_id = ?
        ORDER BY id
        ''',
        (row_id,),
    ).fetchall()
    return {str(row['artifact_type']): str(row['path'] or '') for row in rows}


def get_task_row(conn: sqlite3.Connection, row_id: int) -> dict[str, Any]:
    row = conn.execute('SELECT * FROM analysis_tasks WHERE id = ?', (row_id,)).fetchone()
    if row is None:
        raise KeyError(public_task_id(row_id))
    return {key: row[key] for key in row.keys()}

def get_latest_artifact(conn: sqlite3.Connection, row_id: int, artifact_type: str) -> dict[str, Any]:
    row = conn.execute(
        '''
        SELECT artifact_type, path, related_table, related_id, summary_json
        FROM task_artifacts
        WHERE task_id = ? AND artifact_type = ?
        ORDER BY id DESC
        LIMIT 1
        ''',
        (row_id, artifact_type),
    ).fetchone()
    if row is None:
        return {}
    return {
        'artifact_type': str(row['artifact_type'] or ''),
        'path': str(row['path'] or ''),
        'related_table': str(row['related_table'] or ''),
        'related_id': int(row['related_id'] or 0),
        'summary': parse_json_object(row['summary_json']),
    }

def list_scored_job_ids(conn: sqlite3.Connection, search_run_id: int) -> list[int]:
    rows = conn.execute(
        '''
        SELECT job_detail_id
        FROM job_search_run_items
        WHERE search_run_id = ?
        ORDER BY source_rank, job_detail_id
        ''',
        (search_run_id,),
    ).fetchall()
    return [int(row['job_detail_id']) for row in rows]


def create_analysis_sample(
    conn: sqlite3.Connection,
    row_id: int,
    search_run_id: int,
    selected_job_ids: list[int],
    excluded_job_ids: list[int],
    selection_note: str = '',
) -> dict[str, Any]:
    version_row = conn.execute(
        'SELECT COALESCE(MAX(sample_version), 0) + 1 AS next_version FROM analysis_samples WHERE task_id = ?',
        (row_id,),
    ).fetchone()
    sample_version = int(version_row['next_version'] or 1)
    cursor = conn.execute(
        '''
        INSERT INTO analysis_samples (
            task_id, search_run_id, sample_version, selected_count, excluded_count,
            selected_job_ids_json, excluded_job_ids_json, selection_note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            row_id,
            search_run_id,
            sample_version,
            len(selected_job_ids),
            len(excluded_job_ids),
            json.dumps(selected_job_ids, ensure_ascii=False),
            json.dumps(excluded_job_ids, ensure_ascii=False),
            selection_note,
        ),
    )
    sample_id = int(cursor.lastrowid)
    selected_set = set(selected_job_ids)
    rows = conn.execute(
        '''
        SELECT job_detail_id, match_score, match_status, role_intent
        FROM job_search_run_items
        WHERE search_run_id = ?
        ORDER BY source_rank, job_detail_id
        ''',
        (search_run_id,),
    ).fetchall()
    for row in rows:
        job_id = int(row['job_detail_id'])
        conn.execute(
            '''
            INSERT INTO analysis_sample_items (
                sample_id, job_detail_id, selected, match_score, match_status, role_intent
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                sample_id,
                job_id,
                1 if job_id in selected_set else 0,
                float(row['match_score'] or 0),
                str(row['match_status'] or 'unscored'),
                str(row['role_intent'] or 'unknown'),
            ),
        )
    return {
        'sample_id': sample_id,
        'sample_version': sample_version,
        'search_run_id': search_run_id,
        'selected_count': len(selected_job_ids),
        'excluded_count': len(excluded_job_ids),
        'selected_job_ids': selected_job_ids,
        'excluded_job_ids': excluded_job_ids,
    }


def get_latest_sample_selection(conn: sqlite3.Connection, row_id: int) -> dict[int, bool]:
    sample = conn.execute(
        '''
        SELECT id
        FROM analysis_samples
        WHERE task_id = ?
        ORDER BY sample_version DESC, id DESC
        LIMIT 1
        ''',
        (row_id,),
    ).fetchone()
    if sample is None:
        return {}
    rows = conn.execute(
        '''
        SELECT job_detail_id, selected
        FROM analysis_sample_items
        WHERE sample_id = ?
        ''',
        (int(sample['id']),),
    ).fetchall()
    return {int(row['job_detail_id']): bool(row['selected']) for row in rows}

def get_latest_sample(conn: sqlite3.Connection, row_id: int) -> dict[str, Any]:
    row = conn.execute(
        '''
        SELECT id, search_run_id, sample_version, selected_count, excluded_count
        FROM analysis_samples
        WHERE task_id = ?
        ORDER BY sample_version DESC, id DESC
        LIMIT 1
        ''',
        (row_id,),
    ).fetchone()
    if row is None:
        return {}
    return {
        'sample_id': int(row['id']),
        'search_run_id': int(row['search_run_id']),
        'sample_version': int(row['sample_version']),
        'selected_count': int(row['selected_count']),
        'excluded_count': int(row['excluded_count']),
    }


def list_selected_sample_job_ids(conn: sqlite3.Connection, sample_id: int) -> list[int]:
    rows = conn.execute(
        '''
        SELECT job_detail_id
        FROM analysis_sample_items
        WHERE sample_id = ? AND selected = 1
        ORDER BY id
        ''',
        (sample_id,),
    ).fetchall()
    return [int(row['job_detail_id']) for row in rows]


def create_structuring_batches(
    conn: sqlite3.Connection,
    row_id: int,
    sample_id: int,
    stage_run_id: int,
    job_ids: list[int],
    batch_size: int,
) -> list[dict[str, Any]]:
    conn.execute('DELETE FROM batch_runs WHERE task_id = ? AND sample_id = ? AND status = ?', (row_id, sample_id, StageStatus.PENDING.value))
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(job_ids), batch_size):
        batch_index = len(batches) + 1
        batch_job_ids = job_ids[offset:offset + batch_size]
        cursor = conn.execute(
            '''
            INSERT INTO batch_runs (
                task_id, sample_id, stage_run_id, batch_index, batch_size, job_ids_json, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                row_id,
                sample_id,
                stage_run_id,
                batch_index,
                batch_size,
                json.dumps(batch_job_ids, ensure_ascii=False),
                StageStatus.PENDING.value,
            ),
        )
        batches.append(
            {
                'batch_id': int(cursor.lastrowid),
                'batch_index': batch_index,
                'batch_size': len(batch_job_ids),
                'job_ids': batch_job_ids,
                'status': StageStatus.PENDING.value,
            }
        )
    return batches


def list_pending_batch_runs(conn: sqlite3.Connection, row_id: int) -> list[dict[str, Any]]:
    return [batch for batch in list_batch_runs(conn, row_id) if batch['status'] == StageStatus.PENDING.value]


def mark_batch_running(conn: sqlite3.Connection, batch_id: int) -> None:
    conn.execute(
        '''
        UPDATE batch_runs
        SET status = ?, started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
            error_code = '', error_message = '', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''',
        (StageStatus.RUNNING.value, batch_id),
    )
    conn.commit()


def mark_batch_completed(
    conn: sqlite3.Connection,
    batch_id: int,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cny: float,
) -> None:
    conn.execute(
        '''
        UPDATE batch_runs
        SET status = ?, model_name = ?, input_tokens = ?, output_tokens = ?, estimated_cny = ?,
            finished_at = CURRENT_TIMESTAMP,
            elapsed_seconds = CASE
                WHEN started_at IS NULL THEN elapsed_seconds
                ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400 AS REAL)
            END,
            error_code = '', error_message = '', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''',
        (StageStatus.COMPLETED.value, model_name, input_tokens, output_tokens, estimated_cny, batch_id),
    )
    conn.commit()


def mark_batch_failed(conn: sqlite3.Connection, batch_id: int, error_code: str, error_message: str) -> None:
    conn.execute(
        '''
        UPDATE batch_runs
        SET status = ?, finished_at = CURRENT_TIMESTAMP,
            elapsed_seconds = CASE
                WHEN started_at IS NULL THEN elapsed_seconds
                ELSE CAST((julianday(CURRENT_TIMESTAMP) - julianday(started_at)) * 86400 AS REAL)
            END,
            error_code = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''',
        (StageStatus.FAILED.value, error_code, error_message, batch_id),
    )
    conn.commit()


def count_batch_statuses(conn: sqlite3.Connection, row_id: int) -> dict[str, int]:
    rows = conn.execute(
        '''
        SELECT status, COUNT(*) AS count
        FROM batch_runs
        WHERE task_id = ?
        GROUP BY status
        ''',
        (row_id,),
    ).fetchall()
    return {str(row['status'] or ''): int(row['count'] or 0) for row in rows}

def list_batch_runs(conn: sqlite3.Connection, row_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        '''
        SELECT id, sample_id, stage_run_id, batch_index, batch_size, job_ids_json, status,
               model_name, input_tokens, output_tokens, estimated_cny,
               elapsed_seconds, error_code, error_message, created_at, updated_at
        FROM batch_runs
        WHERE task_id = ?
        ORDER BY sample_id DESC, batch_index
        ''',
        (row_id,),
    ).fetchall()
    return [
        {
            'batch_id': int(row['id']),
            'sample_id': int(row['sample_id']),
            'stage_run_id': int(row['stage_run_id'] or 0),
            'batch_index': int(row['batch_index']),
            'batch_size': int(row['batch_size']),
            'job_ids': parse_json_list(row['job_ids_json']),
            'status': str(row['status'] or StageStatus.PENDING.value),
            'model_name': str(row['model_name'] or ''),
            'input_tokens': int(row['input_tokens'] or 0),
            'output_tokens': int(row['output_tokens'] or 0),
            'estimated_cny': float(row['estimated_cny'] or 0),
            'elapsed_seconds': float(row['elapsed_seconds'] or 0),
            'error_code': str(row['error_code'] or ''),
            'error_message': str(row['error_message'] or ''),
            'created_at': str(row['created_at'] or ''),
            'updated_at': str(row['updated_at'] or ''),
        }
        for row in rows
    ]


def count_run_field(conn: sqlite3.Connection, search_run_id: int, field_name: str) -> dict[str, int]:
    if field_name not in {'match_status', 'role_intent'}:
        raise ValueError(f'unsupported count field: {field_name}')
    rows = conn.execute(
        f'''
        SELECT {field_name} AS value, COUNT(*) AS count
        FROM job_search_run_items
        WHERE search_run_id = ?
        GROUP BY {field_name}
        ORDER BY {field_name}
        ''',
        (search_run_id,),
    ).fetchall()
    return {str(row['value'] or ''): int(row['count'] or 0) for row in rows}


def row_to_task_read(conn: sqlite3.Connection, row: sqlite3.Row) -> AnalysisTaskRead:
    metrics = live_task_metrics(conn, int(row['id']))
    return AnalysisTaskRead(
        id=public_task_id(int(row['id'])),
        task_name=str(row['task_name'] or ''),
        city=str(row['city'] or ''),
        city_code=str(row['city_code'] or ''),
        keyword=str(row['keyword'] or ''),
        job_type=str(row['job_type'] or ''),
        expected_job_count=int(row['expected_job_count'] or 0),
        batch_size=int(row['batch_size'] or 10),
        status=str(row['status'] or TaskStatus.READY.value),
        source_type=str(row['source_type'] or ''),
        search_run_id=metrics['search_run_id'],
        collected_count=metrics['collected_count'],
        analysis_ready_count=metrics['analysis_ready_count'],
        created_at=str(row['created_at'] or ''),
        updated_at=str(row['updated_at'] or ''),
        fixture=FixtureBinding(
            fixture_id='',
            source_type=str(row['source_type'] or ''),
            search_run_id=metrics['search_run_id'],
            report_input_path='',
            report_path='',
            timing_path='',
        ),
    )


def live_task_metrics(conn: sqlite3.Connection, row_id: int) -> dict[str, int]:
    artifact = conn.execute(
        '''
        SELECT related_table, related_id, summary_json
        FROM task_artifacts
        WHERE task_id = ? AND artifact_type = ?
        ORDER BY id DESC
        LIMIT 1
        ''',
        (row_id, 'search_run'),
    ).fetchone()
    if artifact is None:
        return {'search_run_id': 0, 'collected_count': 0, 'analysis_ready_count': 0}

    summary = parse_json_object(artifact['summary_json'])
    search_run_id = int(artifact['related_id'] or 0) if str(artifact['related_table'] or '') == 'job_search_runs' else 0
    collected_count = int(summary.get('collected_count') or summary.get('saved_count') or 0)
    analysis_ready_count = int(summary.get('analysis_ready_count') or 0)

    if search_run_id:
        run = conn.execute(
            '''
            SELECT collected_count, analysis_ready_count
            FROM job_search_runs
            WHERE id = ?
            ''',
            (search_run_id,),
        ).fetchone()
        if run is not None:
            collected_count = int(run['collected_count'] or collected_count)
            analysis_ready_count = int(run['analysis_ready_count'] or analysis_ready_count)

    return {
        'search_run_id': search_run_id,
        'collected_count': collected_count,
        'analysis_ready_count': analysis_ready_count,
    }


def stage_row_to_read(row: sqlite3.Row) -> TaskStageRunRead:
    message = str(row['error_message'] or '')
    if not message:
        output = parse_json_object(row['output_json'])
        message = str(output.get('description') or output.get('label') or '')
    return TaskStageRunRead(
        stage_name=str(row['stage_name'] or ''),
        status=str(row['status'] or StageStatus.PENDING.value),
        elapsed_seconds=float(row['elapsed_seconds'] or 0),
        message=message,
    )


def event_row_to_read(row: sqlite3.Row) -> TaskEventRead:
    return TaskEventRead(
        id=int(row['id']),
        level=str(row['level'] or 'info'),
        event_type=str(row['event_type'] or ''),
        message=str(row['message'] or ''),
        created_at=str(row['created_at'] or ''),
        payload=parse_json_object(row['payload_json']),
    )


def parse_json_list(value: object) -> list[int]:
    if isinstance(value, list):
        parsed = value
    else:
        try:
            parsed = json.loads(str(value or '[]'))
        except json.JSONDecodeError:
            return []
    if not isinstance(parsed, list):
        return []
    output: list[int] = []
    for item in parsed:
        try:
            output.append(int(item))
        except (TypeError, ValueError):
            continue
    return output

def parse_json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or '{}'))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}





