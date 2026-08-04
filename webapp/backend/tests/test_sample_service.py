from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories import analysis_tasks
from app.schemas.tasks import SampleConfirmRequest
from app.services.task_harness import StageName
from tests.test_scoring_service import seed_collected_task, temp_connect


def seed_scored_task(db_path: Path, monkeypatch) -> str:
    task_id = seed_collected_task(db_path)
    connect_temp = temp_connect(db_path)
    from app.services import scoring_service, task_service

    monkeypatch.setattr(scoring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    task_service.start_scoring(task_id)
    return task_id


def test_save_sample_persists_selection_and_stage(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_scored_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import sample_service, task_service

    monkeypatch.setattr(sample_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)

    jobs = task_service.list_jobs(task_id, limit=10)
    selected_id = next(row.job_id for row in jobs.rows if row.job_title == 'GIS开发工程师')

    updated = task_service.save_sample(
        task_id,
        SampleConfirmRequest(selected_job_ids=[selected_id], selection_note='保留 GIS 开发岗位。'),
    )

    sample_stage = next(stage for stage in updated.stages if stage.stage_name == StageName.CONFIRM_SAMPLE.value)
    assert sample_stage.status == 'completed'
    assert updated.artifact_paths['sample'] == ''

    selected_jobs = task_service.list_jobs(task_id, selected_only=True, limit=10)
    assert selected_jobs.total == 1
    assert selected_jobs.rows[0].job_id == selected_id

    conn = connect_temp()
    try:
        sample = conn.execute('SELECT * FROM analysis_samples WHERE task_id = 1').fetchone()
        assert sample is not None
        assert int(sample['selected_count']) == 1
        assert int(sample['excluded_count']) == 1
        items = conn.execute('SELECT selected, COUNT(*) AS count FROM analysis_sample_items GROUP BY selected').fetchall()
        assert {int(row['selected']): int(row['count']) for row in items} == {0: 1, 1: 1}
    finally:
        conn.close()


def test_save_sample_api_rejects_unknown_job_id(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_scored_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import sample_service, scoring_service, task_service

    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(scoring_service, 'connect', connect_temp)
    monkeypatch.setattr(sample_service, 'connect', connect_temp)
    client = TestClient(create_app())

    response = client.post(f'/api/tasks/{task_id}/sample', json={'selected_job_ids': [9999]})
    detail = client.get(f'/api/tasks/{task_id}').json()['data']

    assert response.status_code == 409
    assert next(stage for stage in detail['stages'] if stage['stage_name'] == 'confirm_sample')['status'] == 'pending'
