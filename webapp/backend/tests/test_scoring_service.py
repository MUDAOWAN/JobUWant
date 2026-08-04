from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories import analysis_tasks
from app.repositories.database import initialize_task_tables
from app.schemas.tasks import AnalysisTaskCreate
from app.services.task_harness import HarnessAction, StageName
from jobuwant.db import initialize_database as initialize_job_tables


def temp_connect(db_path: Path):
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    return _connect


def seed_collected_task(db_path: Path) -> str:
    conn = temp_connect(db_path)()
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
    source_type = detail.task.source_type
    insert_job(conn, source_type, '空间智能公司', 'GIS开发工程师', '广州', '负责 GIS 平台开发，使用 Python、PostGIS、地图服务和空间数据处理。')
    insert_job(conn, source_type, '泛科技公司', '销售顾问', '深圳', '负责客户沟通和商务拓展。')
    cursor = conn.execute(
        '''
        INSERT INTO job_search_runs (
            source_type, source_name, query_city, query_keyword, input_path,
            requested_limit, collected_count, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (source_type, 'test_collection', '广州', 'GIS', 'data/task_artifacts/task-1/collection.json', 2, 2, 'collected'),
    )
    search_run_id = int(cursor.lastrowid)
    analysis_tasks.start_action(
        conn,
        task_id=detail.task.id,
        action=HarnessAction.START_COLLECTION,
        message='采集阶段已启动。',
        payload={},
    )
    analysis_tasks.mark_stage_completed(
        conn,
        task_id=detail.task.id,
        stage_name=StageName.COLLECT_JOBS,
        output_payload={'search_run_id': search_run_id, 'collected_count': 2},
        artifact_type='search_run',
        artifact_path='data/task_artifacts/task-1/collection.json',
        related_table='job_search_runs',
        related_id=search_run_id,
        artifact_summary={'search_run_id': search_run_id, 'collected_count': 2},
    )
    conn.close()
    return detail.task.id


def insert_job(conn: sqlite3.Connection, source_type: str, company: str, title: str, city: str, raw_text: str) -> None:
    text_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    conn.execute(
        '''
        INSERT INTO job_details (
            company_name, job_title, city, recruitment_stage, responsibilities,
            requirements, technical_keywords_json, original_url, raw_job_text,
            raw_text_hash, source_type, source_confidence, parse_confidence,
            source_metadata_json, review_status, error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            company,
            title,
            city,
            'social',
            '',
            '',
            json.dumps(['GIS', 'Python'], ensure_ascii=True),
            f'https://example.test/{text_hash}',
            raw_text,
            text_hash,
            source_type,
            'high',
            'source_imported',
            json.dumps({'salary': '10-15K', 'experience': '不限', 'education': '本科'}, ensure_ascii=True),
            'imported',
            '',
        ),
    )
    conn.commit()


def test_start_scoring_scores_existing_collection_run(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_collected_task(db_path)
    connect_temp = temp_connect(db_path)

    from app.services import scoring_service, task_service

    monkeypatch.setattr(scoring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)

    updated = task_service.start_scoring(task_id)

    score_stage = next(stage for stage in updated.stages if stage.stage_name == StageName.SCORE_JOBS.value)
    assert score_stage.status == 'completed'
    assert updated.task.search_run_id == 1
    assert updated.task.collected_count == 2
    assert updated.task.analysis_ready_count >= 1
    assert updated.match_status_counts
    assert updated.artifact_paths['scored_jobs'].endswith('collection.json')

    jobs = task_service.list_jobs(task_id, selected_only=True, limit=10)
    assert jobs.total >= 1
    assert any(row.job_title == 'GIS开发工程师' for row in jobs.rows)


def test_start_scoring_api_returns_conflict_before_collection(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'

    def connect_temp() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    from app.services import scoring_service, task_service

    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(scoring_service, 'connect', connect_temp)
    client = TestClient(create_app())
    task_id = client.post(
        '/api/tasks',
        json={'city': '广州', 'city_code': '101280100', 'keyword': 'GIS'},
    ).json()['data']['task']['id']

    response = client.post(f'/api/tasks/{task_id}/actions/start-scoring')
    detail = client.get(f'/api/tasks/{task_id}').json()['data']

    assert response.status_code == 409
    assert detail['task']['status'] == 'ready'
    assert next(stage for stage in detail['stages'] if stage['stage_name'] == 'score_jobs')['status'] == 'pending'

