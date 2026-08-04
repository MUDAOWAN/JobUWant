from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class TaskStatus(StrEnum):
    DRAFT = 'draft'
    READY = 'ready'
    RUNNING = 'running'
    WAITING_FOR_SAMPLE = 'waiting_for_sample'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'


class StageStatus(StrEnum):
    PENDING = 'pending'
    RUNNING = 'running'
    WAITING_FOR_USER = 'waiting_for_user'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class StageName(StrEnum):
    COLLECT_JOBS = 'collect_jobs'
    SCORE_JOBS = 'score_jobs'
    CONFIRM_SAMPLE = 'confirm_sample'
    AI_STRUCTURING = 'ai_structuring'
    BUILD_REPORT_INPUT = 'build_report_input'
    WRITE_FINAL_REPORT = 'write_final_report'


class HarnessAction(StrEnum):
    START_COLLECTION = 'start_collection'
    START_SCORING = 'start_scoring'
    SAVE_SAMPLE = 'save_sample'
    START_STRUCTURING = 'start_structuring'
    BUILD_REPORT_INPUT = 'build_report_input'
    WRITE_FINAL_REPORT = 'write_final_report'


@dataclass(frozen=True)
class StageSpec:
    name: StageName
    order: int
    label: str
    action: HarnessAction | None
    description: str
    requires_user_confirmation: bool = False
    artifact_types: tuple[str, ...] = ()


STAGE_SPECS: tuple[StageSpec, ...] = (
    StageSpec(
        name=StageName.COLLECT_JOBS,
        order=10,
        label='采集岗位',
        action=HarnessAction.START_COLLECTION,
        description='根据城市、关键词和求职类型获取岗位原始数据，并记录 search_run_id。',
        artifact_types=('search_run',),
    ),
    StageSpec(
        name=StageName.SCORE_JOBS,
        order=20,
        label='本地评分',
        action=HarnessAction.START_SCORING,
        description='对岗位做本地匹配评分，生成强匹配、待复核、弱匹配等样本候选。',
        artifact_types=('scored_jobs',),
    ),
    StageSpec(
        name=StageName.CONFIRM_SAMPLE,
        order=30,
        label='确认样本',
        action=HarnessAction.SAVE_SAMPLE,
        description='由用户确认进入 AI 结构化的岗位样本，保存样本版本和选择记录。',
        requires_user_confirmation=True,
        artifact_types=('sample',),
    ),
    StageSpec(
        name=StageName.AI_STRUCTURING,
        order=40,
        label='AI 结构化',
        action=HarnessAction.START_STRUCTURING,
        description='按批次提取岗位结构化字段，记录批次状态、耗时和用量。',
        artifact_types=('extractions', 'batch_runs'),
    ),
    StageSpec(
        name=StageName.BUILD_REPORT_INPUT,
        order=50,
        label='生成报告输入',
        action=HarnessAction.BUILD_REPORT_INPUT,
        description='汇总样本、技术词、薪资、证据质量和预算信息，生成报告输入 JSON。',
        artifact_types=('report_input',),
    ),
    StageSpec(
        name=StageName.WRITE_FINAL_REPORT,
        order=60,
        label='生成最终报告',
        action=HarnessAction.WRITE_FINAL_REPORT,
        description='基于报告输入生成最终报告 JSON，供前端阅读页展示。',
        artifact_types=('report',),
    ),
)

_STAGE_BY_NAME = {spec.name: spec for spec in STAGE_SPECS}
_STAGE_BY_ACTION = {spec.action: spec for spec in STAGE_SPECS if spec.action is not None}


def list_stage_specs() -> list[StageSpec]:
    return list(STAGE_SPECS)


def get_stage_spec(stage_name: str | StageName) -> StageSpec:
    name = StageName(stage_name)
    return _STAGE_BY_NAME[name]


def get_stage_for_action(action: str | HarnessAction) -> StageSpec:
    name = HarnessAction(action)
    return _STAGE_BY_ACTION[name]


def next_stage_name(stage_name: str | StageName) -> StageName | None:
    current = get_stage_spec(stage_name)
    ordered = list_stage_specs()
    index = ordered.index(current)
    if index + 1 >= len(ordered):
        return None
    return ordered[index + 1].name


def previous_stage_name(stage_name: str | StageName) -> StageName | None:
    current = get_stage_spec(stage_name)
    ordered = list_stage_specs()
    index = ordered.index(current)
    if index == 0:
        return None
    return ordered[index - 1].name


def initial_stage_statuses() -> dict[str, str]:
    return {spec.name.value: StageStatus.PENDING.value for spec in STAGE_SPECS}


def can_start_stage(stage_name: str | StageName, completed_stage_names: set[str]) -> bool:
    previous = previous_stage_name(stage_name)
    if previous is None:
        return True
    return previous.value in completed_stage_names


def next_runnable_stage(stage_statuses: dict[str, str]) -> StageName | None:
    completed = {name for name, status in stage_statuses.items() if status == StageStatus.COMPLETED.value}
    for spec in STAGE_SPECS:
        status = stage_statuses.get(spec.name.value, StageStatus.PENDING.value)
        if status in {StageStatus.RUNNING.value, StageStatus.WAITING_FOR_USER.value}:
            return spec.name
        if status == StageStatus.PENDING.value and can_start_stage(spec.name, completed):
            return spec.name
    return None


def derive_task_status(stage_statuses: dict[str, str]) -> TaskStatus:
    values = set(stage_statuses.values())
    if StageStatus.FAILED.value in values:
        return TaskStatus.FAILED
    if StageStatus.RUNNING.value in values:
        return TaskStatus.RUNNING
    if stage_statuses.get(StageName.CONFIRM_SAMPLE.value) == StageStatus.WAITING_FOR_USER.value:
        return TaskStatus.WAITING_FOR_SAMPLE
    if all(stage_statuses.get(spec.name.value) == StageStatus.COMPLETED.value for spec in STAGE_SPECS):
        return TaskStatus.COMPLETED
    return TaskStatus.READY


def assert_action_allowed(action: str | HarnessAction, stage_statuses: dict[str, str]) -> StageSpec:
    spec = get_stage_for_action(action)
    current_status = stage_statuses.get(spec.name.value, StageStatus.PENDING.value)
    if current_status == StageStatus.COMPLETED.value:
        raise ValueError(f'stage already completed: {spec.name.value}')
    if current_status == StageStatus.RUNNING.value:
        raise ValueError(f'stage already running: {spec.name.value}')
    if current_status == StageStatus.WAITING_FOR_USER.value:
        raise ValueError(f'stage is waiting for user confirmation: {spec.name.value}')
    completed = {name for name, status in stage_statuses.items() if status == StageStatus.COMPLETED.value}
    if not can_start_stage(spec.name, completed):
        previous = previous_stage_name(spec.name)
        raise ValueError(f'previous stage must complete first: {previous.value if previous else "none"}')
    return spec


def harness_manifest() -> dict[str, object]:
    return {
        'task_statuses': [status.value for status in TaskStatus],
        'stage_statuses': [status.value for status in StageStatus],
        'actions': [action.value for action in HarnessAction],
        'stages': [
            {
                **asdict(spec),
                'name': spec.name.value,
                'action': spec.action.value if spec.action else None,
                'artifact_types': list(spec.artifact_types),
            }
            for spec in STAGE_SPECS
        ],
    }
