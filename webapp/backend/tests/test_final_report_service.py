from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.task_harness import StageName, StageStatus
from tests.test_report_input_service import seed_structured_task
from tests.test_scoring_service import temp_connect


@dataclass(frozen=True)
class FakeSettings:
    model: str = 'fake-report-model'


def seed_report_input_task(tmp_path, db_path, monkeypatch) -> str:
    task_id = seed_structured_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import report_input_service, task_service

    monkeypatch.setattr(report_input_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(report_input_service, 'DATA_DIR', tmp_path)
    task_service.build_report_input(task_id)
    return task_id


def test_final_report_runner_completes_fake_report(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_report_input_task(tmp_path, db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.runner import final_report_runner
    from app.services import final_report_service, report_input_service, task_service

    monkeypatch.setattr(final_report_service, 'connect', connect_temp)
    monkeypatch.setattr(report_input_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(final_report_runner, 'connect', connect_temp)
    monkeypatch.setattr(final_report_runner, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(final_report_service.final_report_runner, 'submit_final_report', lambda task_id: True)
    monkeypatch.setattr(final_report_runner, 'load_settings', lambda **kwargs: FakeSettings())
    monkeypatch.setattr(final_report_runner, 'write_report_with_openai', fake_write_report)

    updated = task_service.write_final_report(task_id)

    stage = next(stage for stage in updated.stages if stage.stage_name == StageName.WRITE_FINAL_REPORT.value)
    assert stage.status == StageStatus.RUNNING.value

    final_report_runner.run_final_report_for_task(task_id)

    detail = task_service.get_task_detail(task_id)
    stage = next(stage for stage in detail.stages if stage.stage_name == StageName.WRITE_FINAL_REPORT.value)
    assert stage.status == StageStatus.COMPLETED.value
    assert detail.artifact_paths['report'].endswith('final_report.json')

    report = task_service.get_final_report(task_id)
    assert report.report_title == '测试岗位报告'
    assert report.raw['audience_summary'] == '面向测试任务的报告摘要。'


def test_write_final_report_api_rejects_before_report_input(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_structured_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import final_report_service, task_service

    monkeypatch.setattr(final_report_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    client = TestClient(create_app())

    response = client.post(f'/api/tasks/{task_id}/actions/write-final-report')

    assert response.status_code == 409


def fake_write_report(report_input, settings, request_timeout, max_output_tokens):
    from jobuwant.ai_report_writer import AIJobReport, collect_allowed_evidence_items

    evidence_items = collect_allowed_evidence_items(report_input)
    first = evidence_items[0]
    ref = {'topic': 'Python', 'job_id': int(first['job_id']), 'quote': str(first['quote'])}
    priority = {'name': 'Python', 'priority': 'high', 'reason': 'Python 是高频技能。', 'evidence_refs': [ref]}
    section = {'title': '岗位画像', 'summary': '测试任务显示 GIS 平台开发能力重要。', 'evidence_refs': [ref]}
    payload = {
        'report_title': '测试岗位报告',
        'audience_summary': '面向测试任务的报告摘要。',
        'role_profile': section,
        'technical_top15_interpretation': [priority],
        'skill_layers': {'core': [priority], 'common': [], 'nice_to_have': []},
        'core_skills': [priority],
        'ability_requirements': [priority],
        'salary_and_threshold': {'title': '薪资与门槛', 'summary': '样本薪资信息有限。', 'evidence_refs': [ref]},
        'experience_and_education': {'title': '经验与学历', 'summary': '样本要求以基础开发能力为主。', 'evidence_refs': [ref]},
        'graduate_friendliness': {'title': '求职友好度', 'summary': '样本对基础能力较友好。', 'evidence_refs': [ref]},
        'learning_route': [{'stage': '基础阶段', 'focus': ['Python'], 'suggestion': '完成一个数据处理练习。'}],
        'project_suggestions': [
            {
                'project_name': 'GIS 数据处理 Demo',
                'stack': ['Python'],
                'data_or_input': '岗位样本中的空间数据处理需求',
                'deliverable': '可运行的数据处理应用',
                'resume_value': '展示 GIS 平台开发能力',
                'evidence_refs': [ref],
            }
        ],
        'resume_keywords': ['Python'],
        'job_search_advice': ['优先投递 GIS 平台开发相关岗位。'],
        'caveats': ['测试样本数量有限。'],
    }
    usage = {'model_calls': 1, 'input_tokens': 100, 'output_tokens': 50, 'estimated_cny': 0.01}
    return AIJobReport.model_validate(payload), usage, '{}'