from __future__ import annotations

from dataclasses import dataclass

from app.runner import structuring_runner
from app.services.task_harness import StageName, StageStatus
from tests.test_scoring_service import temp_connect
from tests.test_structuring_service import seed_sampled_task


@dataclass(frozen=True)
class FakeSettings:
    model: str = 'fake-model'


def test_run_structuring_batches_queues_runner_without_model_call(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import structuring_service, task_service

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(structuring_service.structuring_runner, 'submit_structuring', lambda task_id: True)
    task_service.start_structuring(task_id)

    updated = task_service.run_structuring_batches(task_id)

    stage = next(stage for stage in updated.stages if stage.stage_name == StageName.AI_STRUCTURING.value)
    assert stage.status == StageStatus.RUNNING.value


def test_structuring_runner_completes_fake_batch(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import structuring_service, task_service

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(structuring_runner, 'connect', connect_temp)
    monkeypatch.setattr(structuring_service.structuring_runner, 'submit_structuring', lambda task_id: True)
    monkeypatch.setattr(structuring_runner, 'load_settings', lambda **kwargs: FakeSettings())
    monkeypatch.setattr(
        structuring_runner,
        'execute_structuring_batch',
        lambda conn, request: {
            'model_name': 'fake-model',
            'requested_jobs': len(request.job_ids),
            'returned_jobs': len(request.job_ids),
            'saved_count': len(request.job_ids),
            'unexpected_job_ids': [],
            'input_tokens': 123,
            'output_tokens': 45,
            'estimated_cny': 0.01,
        },
    )
    task_service.start_structuring(task_id)
    task_service.run_structuring_batches(task_id)

    structuring_runner.run_structuring_for_task(task_id)

    status = task_service.get_structuring_status(task_id)
    assert status.batches[0].status == StageStatus.COMPLETED.value
    assert status.batches[0].model_name == 'fake-model'
    assert status.batches[0].input_tokens == 123
    detail = task_service.get_task_detail(task_id)
    stage = next(stage for stage in detail.stages if stage.stage_name == StageName.AI_STRUCTURING.value)
    assert stage.status == StageStatus.COMPLETED.value
    assert detail.artifact_paths['extractions'] == ''


def test_structuring_runner_marks_failed_batch(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import structuring_service, task_service

    def fail_batch(conn, request):
        raise RuntimeError('fake batch failure')

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(structuring_runner, 'connect', connect_temp)
    monkeypatch.setattr(structuring_service.structuring_runner, 'submit_structuring', lambda task_id: True)
    monkeypatch.setattr(structuring_runner, 'load_settings', lambda **kwargs: FakeSettings())
    monkeypatch.setattr(structuring_runner, 'execute_structuring_batch', fail_batch)
    task_service.start_structuring(task_id)
    task_service.run_structuring_batches(task_id)

    structuring_runner.run_structuring_for_task(task_id)

    status = task_service.get_structuring_status(task_id)
    assert status.batches[0].status == StageStatus.FAILED.value
    detail = task_service.get_task_detail(task_id)
    stage = next(stage for stage in detail.stages if stage.stage_name == StageName.AI_STRUCTURING.value)
    assert stage.status == StageStatus.FAILED.value


def test_run_structuring_batches_api_rejects_before_plan(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from app.main import create_app
    from tests.test_structuring_service import seed_sampled_task

    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import structuring_service, task_service

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    client = TestClient(create_app())

    response = client.post(f'/api/tasks/{task_id}/actions/run-structuring-batches')

    assert response.status_code == 409

