from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.repositories import analysis_tasks
from app.repositories.database import initialize_task_tables
from app.runner import collection_runner
from app.schemas.tasks import AnalysisTaskCreate
from app.services.task_harness import HarnessAction, StageName
from jobuwant.db import initialize_database as initialize_job_tables


@dataclass(frozen=True)
class ImportSummary:
    input_path: Path
    read_count: int
    normalized_count: int
    saved_count: int
    skipped_count: int


def temp_connect(db_path: Path):
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    return _connect


def test_build_collection_request_maps_task_fields(tmp_path) -> None:
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    initialize_task_tables(conn)
    detail = analysis_tasks.create_task(
        conn,
        AnalysisTaskCreate(
            city='杭州',
            city_code='101210100',
            keyword='Agent工程师',
            job_type='intern',
            expected_job_count=40,
        ),
    )
    row = conn.execute('SELECT * FROM analysis_tasks WHERE id = ?', (1,)).fetchone()

    request = collection_runner.build_collection_request(row)

    assert request.task_id == detail.task.id
    assert request.city_code == '101210100'
    assert request.keyword == 'Agent工程师'
    assert request.platform_job_type == '1902'
    assert request.expected_job_count == 40
    assert request.detail_limit == 40
    assert request.max_pages == 3


def test_run_collection_for_task_records_completed_stage_and_search_run(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    connect_temp = temp_connect(db_path)
    conn = connect_temp()
    initialize_task_tables(conn)
    initialize_job_tables(conn)
    detail = analysis_tasks.create_task(
        conn,
        AnalysisTaskCreate(
            city='广州',
            city_code='101280100',
            keyword='GIS',
            job_type='any',
            expected_job_count=2,
        ),
    )
    analysis_tasks.start_action(
        conn,
        task_id=detail.task.id,
        action=HarnessAction.START_COLLECTION,
        message='采集阶段已启动。',
        payload={'runner_status': 'queued'},
    )
    conn.close()

    monkeypatch.setattr(collection_runner, 'connect', connect_temp)
    monkeypatch.setattr(
        collection_runner,
        'execute_collection_script',
        lambda request: {'stop_reason': 'completed', 'stats': {'job_saved_count': 2}},
    )
    monkeypatch.setattr(
        collection_runner,
        'import_boss_json',
        lambda conn, path: ImportSummary(path, read_count=2, normalized_count=2, saved_count=2, skipped_count=0),
    )

    collection_runner.run_collection_for_task(detail.task.id)

    conn = connect_temp()
    try:
        updated = analysis_tasks.get_task_detail(conn, detail.task.id)
        collect_stage = next(stage for stage in updated.stages if stage.stage_name == StageName.COLLECT_JOBS.value)
        assert collect_stage.status == 'completed'
        assert updated.task.search_run_id == 1
        assert updated.task.collected_count == 2
        assert updated.artifact_paths['search_run'].endswith('collection.json')
        events = [event.event_type for event in analysis_tasks.list_events(conn, detail.task.id)]
        assert 'collection_runner_started' in events
        assert 'collect_jobs_completed' in events
    finally:
        conn.close()
