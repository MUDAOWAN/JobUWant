from __future__ import annotations

import pytest

from app.services.task_harness import (
    HarnessAction,
    StageName,
    StageStatus,
    TaskStatus,
    assert_action_allowed,
    derive_task_status,
    harness_manifest,
    initial_stage_statuses,
    next_runnable_stage,
    next_stage_name,
)


def test_stage_order_is_linear() -> None:
    assert next_stage_name(StageName.COLLECT_JOBS) == StageName.SCORE_JOBS
    assert next_stage_name(StageName.SCORE_JOBS) == StageName.CONFIRM_SAMPLE
    assert next_stage_name(StageName.CONFIRM_SAMPLE) == StageName.AI_STRUCTURING
    assert next_stage_name(StageName.AI_STRUCTURING) == StageName.BUILD_REPORT_INPUT
    assert next_stage_name(StageName.BUILD_REPORT_INPUT) == StageName.WRITE_FINAL_REPORT
    assert next_stage_name(StageName.WRITE_FINAL_REPORT) is None


def test_initial_task_can_start_collection_only() -> None:
    statuses = initial_stage_statuses()
    allowed = assert_action_allowed(HarnessAction.START_COLLECTION, statuses)
    assert allowed.name == StageName.COLLECT_JOBS
    with pytest.raises(ValueError, match='previous stage must complete first'):
        assert_action_allowed(HarnessAction.START_STRUCTURING, statuses)


def test_next_runnable_stage_tracks_completed_work() -> None:
    statuses = initial_stage_statuses()
    assert next_runnable_stage(statuses) == StageName.COLLECT_JOBS
    statuses[StageName.COLLECT_JOBS.value] = StageStatus.COMPLETED.value
    assert next_runnable_stage(statuses) == StageName.SCORE_JOBS
    statuses[StageName.SCORE_JOBS.value] = StageStatus.COMPLETED.value
    statuses[StageName.CONFIRM_SAMPLE.value] = StageStatus.WAITING_FOR_USER.value
    assert next_runnable_stage(statuses) == StageName.CONFIRM_SAMPLE


def test_waiting_stage_rejects_duplicate_action() -> None:
    statuses = initial_stage_statuses()
    statuses[StageName.COLLECT_JOBS.value] = StageStatus.COMPLETED.value
    statuses[StageName.SCORE_JOBS.value] = StageStatus.COMPLETED.value
    statuses[StageName.CONFIRM_SAMPLE.value] = StageStatus.COMPLETED.value
    statuses[StageName.AI_STRUCTURING.value] = StageStatus.WAITING_FOR_USER.value
    with pytest.raises(ValueError, match='stage is waiting for user confirmation'):
        assert_action_allowed(HarnessAction.START_STRUCTURING, statuses)


def test_derive_task_status() -> None:
    statuses = initial_stage_statuses()
    assert derive_task_status(statuses) == TaskStatus.READY
    statuses[StageName.COLLECT_JOBS.value] = StageStatus.RUNNING.value
    assert derive_task_status(statuses) == TaskStatus.RUNNING
    statuses[StageName.COLLECT_JOBS.value] = StageStatus.COMPLETED.value
    statuses[StageName.SCORE_JOBS.value] = StageStatus.FAILED.value
    assert derive_task_status(statuses) == TaskStatus.FAILED
    for stage_name in list(statuses):
        statuses[stage_name] = StageStatus.COMPLETED.value
    assert derive_task_status(statuses) == TaskStatus.COMPLETED


def test_derive_task_status_prefers_canceled() -> None:
    statuses = initial_stage_statuses()
    statuses[StageName.COLLECT_JOBS.value] = StageStatus.CANCELED.value
    statuses[StageName.SCORE_JOBS.value] = StageStatus.FAILED.value

    assert derive_task_status(statuses) == TaskStatus.CANCELED

def test_harness_manifest_is_documentable() -> None:
    manifest = harness_manifest()
    assert 'collect_jobs' in [stage['name'] for stage in manifest['stages']]
    assert 'write_final_report' in [stage['name'] for stage in manifest['stages']]
    assert 'start_collection' in manifest['actions']
    assert 'waiting_for_sample' in manifest['task_statuses']
