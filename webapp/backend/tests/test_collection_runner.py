from __future__ import annotations

import json
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


def test_run_collection_for_task_cancels_without_importing_output(tmp_path, monkeypatch) -> None:
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

    output_paths: list[Path] = []

    def fake_execute(request: collection_runner.CollectionRunRequest) -> dict[str, object]:
        output_paths.append(request.output_path)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_text('{"jobs": []}', encoding='utf-8')
        raise collection_runner.CollectionCanceled('user requested')

    def fail_import(*args, **kwargs):
        raise AssertionError('import should not run after cancellation')

    monkeypatch.setattr(collection_runner, 'connect', connect_temp)
    monkeypatch.setattr(collection_runner, 'execute_collection_script', fake_execute)
    monkeypatch.setattr(collection_runner, 'import_boss_json', fail_import)

    collection_runner.run_collection_for_task(detail.task.id)

    conn = connect_temp()
    try:
        updated = analysis_tasks.get_task_detail(conn, detail.task.id)
        collect_stage = next(stage for stage in updated.stages if stage.stage_name == StageName.COLLECT_JOBS.value)
        assert updated.task.status == 'canceled'
        assert collect_stage.status == 'canceled'
        assert updated.task.search_run_id == 0
        assert 'search_run' not in updated.artifact_paths
        assert output_paths
        assert not output_paths[0].exists()
        events = [event.event_type for event in analysis_tasks.list_events(conn, detail.task.id)]
        assert 'task_canceled' in events
    finally:
        conn.close()


def test_handle_progress_line_records_login_events(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    connect_temp = temp_connect(db_path)
    conn = connect_temp()
    initialize_task_tables(conn)
    detail = analysis_tasks.create_task(
        conn,
        AnalysisTaskCreate(
            city='杭州',
            city_code='101210100',
            keyword='Agent工程师',
            job_type='intern',
            expected_job_count=2,
        ),
    )
    row_id = analysis_tasks.parse_public_task_id(detail.task.id)
    conn.close()

    monkeypatch.setattr(collection_runner, 'connect', connect_temp)

    collection_runner.handle_progress_line(
        detail.task.id,
        row_id,
        'AUTH_OPENING ' + json.dumps({'message': 'opening'}, ensure_ascii=False),
    )
    collection_runner.handle_progress_line(
        detail.task.id,
        row_id,
        'AUTH_CHECKING ' + json.dumps({'timeout_seconds': 300}, ensure_ascii=False),
    )
    collection_runner.handle_progress_line(
        detail.task.id,
        row_id,
        'AUTH_REQUIRED ' + json.dumps({'timeout_seconds': 300, 'login_hint': '扫码登录'}, ensure_ascii=False),
    )

    conn = connect_temp()
    try:
        events = analysis_tasks.list_events(conn, detail.task.id)
        assert [event.event_type for event in events[-3:]] == [
            'collection_login_opening',
            'collection_login_checking',
            'collection_login_required',
        ]
        assert '扫码登录' in events[-1].message
        assert events[-1].payload['timeout_seconds'] == 300
    finally:
        conn.close()


def test_run_collection_for_task_marks_login_timeout_failed(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    connect_temp = temp_connect(db_path)
    conn = connect_temp()
    initialize_task_tables(conn)
    initialize_job_tables(conn)
    detail = analysis_tasks.create_task(
        conn,
        AnalysisTaskCreate(
            city='杭州',
            city_code='101210100',
            keyword='Agent工程师',
            job_type='intern',
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

    output_paths: list[Path] = []

    def fake_execute(request: collection_runner.CollectionRunRequest) -> dict[str, object]:
        output_paths.append(request.output_path)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_text(json.dumps({'jobs': []}), encoding='utf-8')
        return {'stop_reason': 'login_timeout', 'stats': {}}

    def fail_import(*args, **kwargs):
        raise AssertionError('import should not run after login timeout')

    monkeypatch.setattr(collection_runner, 'connect', connect_temp)
    monkeypatch.setattr(collection_runner, 'execute_collection_script', fake_execute)
    monkeypatch.setattr(collection_runner, 'import_boss_json', fail_import)

    collection_runner.run_collection_for_task(detail.task.id)

    conn = connect_temp()
    try:
        updated = analysis_tasks.get_task_detail(conn, detail.task.id)
        collect_stage = next(stage for stage in updated.stages if stage.stage_name == StageName.COLLECT_JOBS.value)
        assert updated.task.status == 'failed'
        assert collect_stage.status == 'failed'
        assert '扫码登录超时' in collect_stage.message
        assert updated.task.search_run_id == 0
        assert output_paths
        assert not output_paths[0].exists()
    finally:
        conn.close()
