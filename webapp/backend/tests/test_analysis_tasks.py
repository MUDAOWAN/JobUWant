from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories import analysis_tasks
from app.repositories.database import initialize_task_tables
from app.schemas.tasks import AnalysisTaskCreate
from app.services.task_harness import HarnessAction, StageName, StageStatus, TaskStatus


def memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    initialize_task_tables(conn)
    return conn


def test_create_live_task_initializes_stages_and_event() -> None:
    conn = memory_conn()
    detail = analysis_tasks.create_task(
        conn,
        AnalysisTaskCreate(
            task_name='广州 GIS 分析',
            city='广州',
            city_code='101280100',
            keyword='GIS',
            job_type='any',
            expected_job_count=30,
            batch_size=10,
        ),
    )

    assert detail.task.id == 'task-1'
    assert detail.task.status == 'ready'
    assert detail.task.source_type == 'webapp_task_1'
    assert [stage.stage_name for stage in detail.stages] == [stage.value for stage in StageName]
    assert {stage.status for stage in detail.stages} == {StageStatus.PENDING.value}

    events = analysis_tasks.list_events(conn, detail.task.id)
    assert len(events) == 1
    assert events[0].event_type == 'task_created'
    assert events[0].payload['task_public_id'] == 'task-1'


def test_list_live_tasks_orders_latest_first() -> None:
    conn = memory_conn()
    first = analysis_tasks.create_task(conn, AnalysisTaskCreate(city='杭州', keyword='Agent工程师'))
    second = analysis_tasks.create_task(conn, AnalysisTaskCreate(city='广州', keyword='GIS'))

    rows = analysis_tasks.list_tasks(conn)
    assert [row.id for row in rows] == [second.task.id, first.task.id]


def test_create_task_api_uses_temporary_database(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'

    def connect_temp() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    from app.services import task_service

    monkeypatch.setattr(task_service, 'connect', connect_temp)
    client = TestClient(create_app())
    response = client.post(
        '/api/tasks',
        json={
            'city': '杭州',
            'city_code': '101210100',
            'keyword': 'Agent工程师',
            'job_type': 'intern',
            'expected_job_count': 40,
            'batch_size': 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert payload['message'] == 'task created'
    assert payload['data']['task']['id'] == 'task-1'
    assert payload['data']['task']['task_name'] == '杭州 Agent工程师 岗位分析'
    assert len(payload['data']['stages']) == 6

def test_start_collection_marks_stage_running() -> None:
    conn = memory_conn()
    detail = analysis_tasks.create_task(conn, AnalysisTaskCreate(city='广州', keyword='GIS'))

    updated = analysis_tasks.start_action(
        conn,
        task_id=detail.task.id,
        action=HarnessAction.START_COLLECTION,
        message='采集阶段已启动。',
        payload={'runner_status': 'not_connected_yet'},
    )

    assert updated.task.status == 'running'
    collect_stage = next(stage for stage in updated.stages if stage.stage_name == 'collect_jobs')
    assert collect_stage.status == 'running'
    events = analysis_tasks.list_events(conn, detail.task.id)
    assert [event.event_type for event in events] == ['task_created', 'collect_jobs_started']


def test_cancel_running_task_marks_active_stage_canceled() -> None:
    conn = memory_conn()
    detail = analysis_tasks.create_task(conn, AnalysisTaskCreate(city='广州', keyword='GIS'))
    analysis_tasks.start_action(
        conn,
        task_id=detail.task.id,
        action=HarnessAction.START_COLLECTION,
        message='采集阶段已启动。',
        payload={'runner_status': 'queued'},
    )

    updated = analysis_tasks.cancel_task(conn, detail.task.id, reason='用户已中断任务。')

    assert updated.task.status == TaskStatus.CANCELED.value
    statuses = {stage.stage_name: stage.status for stage in updated.stages}
    assert statuses[StageName.COLLECT_JOBS.value] == StageStatus.CANCELED.value
    assert statuses[StageName.SCORE_JOBS.value] == StageStatus.SKIPPED.value
    events = analysis_tasks.list_events(conn, detail.task.id)
    assert events[-1].event_type == 'task_canceled'

def test_start_collection_api_rejects_duplicate_start(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'

    def connect_temp() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    from app.services import task_service

    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service.collection_runner, 'submit_collection', lambda task_id: True)
    client = TestClient(create_app())
    created = client.post(
        '/api/tasks',
        json={'city': '广州', 'city_code': '101280100', 'keyword': 'GIS'},
    ).json()['data']['task']['id']

    first = client.post(f'/api/tasks/{created}/actions/start-collection')
    second = client.post(f'/api/tasks/{created}/actions/start-collection')

    assert first.status_code == 200
    assert first.json()['data']['task']['status'] == 'running'
    assert second.status_code == 409

def test_cancel_task_api_marks_running_task_canceled(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'

    def connect_temp() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    from app.services import task_service

    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service.collection_runner, 'submit_collection', lambda task_id: True)
    monkeypatch.setattr(task_service.collection_runner, 'cancel_collection', lambda task_id: True)
    client = TestClient(create_app())
    created = client.post(
        '/api/tasks',
        json={'city': '广州', 'city_code': '101280100', 'keyword': 'GIS'},
    ).json()['data']['task']['id']
    client.post(f'/api/tasks/{created}/actions/start-collection')

    response = client.post(f'/api/tasks/{created}/actions/cancel')

    assert response.status_code == 200
    payload = response.json()
    assert payload['message'] == 'task canceled'
    assert payload['data']['task']['status'] == 'canceled'
    assert payload['data']['stages'][0]['status'] == 'canceled'


def test_task_detail_includes_metrics_from_stages_artifacts_and_batches() -> None:
    conn = memory_conn()
    detail = analysis_tasks.create_task(conn, AnalysisTaskCreate(city='杭州', keyword='Agent工程师'))
    row_id = analysis_tasks.parse_public_task_id(detail.task.id)

    analysis_tasks.start_action(
        conn,
        task_id=detail.task.id,
        action=HarnessAction.START_COLLECTION,
        message='查找已启动。',
        payload={},
    )
    analysis_tasks.mark_stage_completed(
        conn,
        task_id=detail.task.id,
        stage_name=StageName.COLLECT_JOBS,
        output_payload={'description': '查找完成。'},
    )
    conn.execute(
        'UPDATE task_stage_runs SET elapsed_seconds = ? WHERE task_id = ? AND stage_name = ?',
        (12.5, row_id, StageName.COLLECT_JOBS.value),
    )

    analysis_tasks.start_action(
        conn,
        task_id=detail.task.id,
        action=HarnessAction.START_SCORING,
        message='本地评分已启动。',
        payload={},
    )
    analysis_tasks.mark_stage_completed(
        conn,
        task_id=detail.task.id,
        stage_name=StageName.SCORE_JOBS,
        output_payload={'average_score': 86.4},
        artifact_type='scored_jobs',
        artifact_summary={'average_score': 86.4},
    )
    conn.execute(
        'UPDATE task_stage_runs SET elapsed_seconds = ? WHERE task_id = ? AND stage_name = ?',
        (3.0, row_id, StageName.SCORE_JOBS.value),
    )
    conn.execute(
        '''
        INSERT INTO batch_runs (task_id, sample_id, batch_index, batch_size, status, input_tokens, output_tokens, estimated_cny)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (row_id, 1, 1, 2, StageStatus.COMPLETED.value, 120, 45, 0.0123),
    )
    conn.commit()

    updated = analysis_tasks.get_task_detail(conn, detail.task.id)

    assert updated.metrics.collection_seconds == 12.5
    assert updated.metrics.scoring_seconds == 3.0
    assert updated.metrics.average_match_score == 86.4
    assert updated.metrics.input_tokens == 120
    assert updated.metrics.output_tokens == 45
    assert updated.metrics.total_tokens == 165
    assert updated.metrics.estimated_cny == 0.0123
    assert updated.metrics.usage_recorded is True
