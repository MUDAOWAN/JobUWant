from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.tasks import SampleConfirmRequest
from app.services.task_harness import StageName, StageStatus
from tests.test_scoring_service import seed_collected_task, temp_connect


def seed_sampled_task(db_path: Path, monkeypatch) -> str:
    task_id = seed_collected_task(db_path)
    connect_temp = temp_connect(db_path)
    from app.services import sample_service, scoring_service, task_service

    monkeypatch.setattr(scoring_service, 'connect', connect_temp)
    monkeypatch.setattr(sample_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    task_service.start_scoring(task_id)
    jobs = task_service.list_jobs(task_id, limit=10)
    selected_ids = [row.job_id for row in jobs.rows[:1]]
    task_service.save_sample(task_id, SampleConfirmRequest(selected_job_ids=selected_ids))
    return task_id


def test_start_structuring_creates_pending_batches_without_model_call(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import structuring_service, task_service

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)

    updated = task_service.start_structuring(task_id)

    stage = next(stage for stage in updated.stages if stage.stage_name == StageName.AI_STRUCTURING.value)
    assert stage.status == StageStatus.WAITING_FOR_USER.value
    assert updated.artifact_paths['batch_runs'] == ''

    status = task_service.get_structuring_status(task_id)
    assert status.sample_id == 1
    assert status.selected_count == 1
    assert status.total_batches == 1
    assert status.batches[0].status == StageStatus.PENDING.value
    assert status.batches[0].input_tokens == 0
    assert status.batches[0].output_tokens == 0


def test_start_structuring_api_rejects_before_sample(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_collected_task(db_path)
    connect_temp = temp_connect(db_path)

    from app.services import scoring_service, structuring_service, task_service

    monkeypatch.setattr(scoring_service, 'connect', connect_temp)
    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    task_service.start_scoring(task_id)
    client = TestClient(create_app())

    response = client.post(f'/api/tasks/{task_id}/actions/start-structuring')
    detail = client.get(f'/api/tasks/{task_id}').json()['data']

    assert response.status_code == 409
    assert next(stage for stage in detail['stages'] if stage['stage_name'] == 'ai_structuring')['status'] == 'pending'


def test_structuring_status_api_returns_batches(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import structuring_service, task_service

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    task_service.start_structuring(task_id)
    client = TestClient(create_app())

    response = client.get(f'/api/tasks/{task_id}/structure')

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['task_id'] == task_id
    assert payload['total_batches'] == 1
    assert payload['batches'][0]['status'] == 'pending'
