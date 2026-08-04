from __future__ import annotations

from app.services import fixture_service


def test_list_fixture_tasks() -> None:
    tasks = fixture_service.list_tasks()
    ids = {task.id for task in tasks}
    assert 'hz-agent-intern-40' in ids
    assert 'gz-gis-any-30' in ids
    assert all(task.status == 'completed' for task in tasks)


def test_fixture_task_detail_counts() -> None:
    hz = fixture_service.get_task_detail('hz-agent-intern-40')
    gz = fixture_service.get_task_detail('gz-gis-any-30')
    assert hz.task.search_run_id == 7
    assert hz.task.collected_count == 40
    assert hz.match_status_counts == {'review': 14, 'strong_match': 26}
    assert gz.task.search_run_id == 8
    assert gz.task.collected_count == 30
    assert gz.match_status_counts == {'review': 20, 'strong_match': 8, 'weak_match': 2}


def test_fixture_jobs_selected_filter() -> None:
    jobs = fixture_service.list_jobs('gz-gis-any-30', selected_only=True, limit=100)
    assert jobs.total == 28
    assert len(jobs.rows) == 28
    assert {row.match_status for row in jobs.rows} <= {'strong_match', 'review'}


def test_fixture_report_artifacts() -> None:
    report_input = fixture_service.get_report_input('hz-agent-intern-40')
    report = fixture_service.get_final_report('gz-gis-any-30')
    assert report_input.sample.get('total_jobs') == 40
    assert report_input.estimated_prompt_tokens > 0
    assert report.report_title
    assert report.raw
