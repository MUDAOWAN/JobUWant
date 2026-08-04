from __future__ import annotations

import hashlib
import json
import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories import analysis_tasks
from app.services.task_harness import StageName
from tests.test_scoring_service import temp_connect
from tests.test_structuring_runner import seed_sampled_task


def seed_structured_task(db_path, monkeypatch) -> str:
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)
    from app.services import report_input_service, structuring_service, task_service

    monkeypatch.setattr(structuring_service, 'connect', connect_temp)
    monkeypatch.setattr(report_input_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    task_service.start_structuring(task_id)
    conn = connect_temp()
    try:
        row_id = analysis_tasks.parse_public_task_id(task_id)
        sample = analysis_tasks.get_latest_sample(conn, row_id)
        selected_ids = analysis_tasks.list_selected_sample_job_ids(conn, int(sample['sample_id']))
        for job_id in selected_ids:
            raw_hash = conn.execute('SELECT raw_text_hash FROM job_details WHERE id = ?', (job_id,)).fetchone()['raw_text_hash']
            payload = extracted_payload(job_id)
            input_hash = hashlib.sha256(f'{job_id}:{raw_hash}'.encode()).hexdigest()
            conn.execute(
                '''
                INSERT INTO job_extractions (
                    job_detail_id, extractor_name, schema_version, input_hash,
                    output_json, evidence_json, status, validation_errors
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    job_id,
                    'test_extractor',
                    'test_schema',
                    input_hash,
                    json.dumps(payload, ensure_ascii=True),
                    json.dumps(payload['evidence'], ensure_ascii=True),
                    'completed',
                    '',
                ),
            )
        analysis_tasks.mark_stage_completed(
            conn,
            task_id=task_id,
            stage_name=StageName.AI_STRUCTURING,
            output_payload={'completed_batches': 1, 'failed_batches': 0},
            artifact_type='extractions',
            artifact_path='',
            related_table='analysis_samples',
            related_id=int(sample['sample_id']),
            artifact_summary={'completed_batches': 1, 'failed_batches': 0},
        )
        conn.commit()
    finally:
        conn.close()
    return task_id


def extracted_payload(job_id: int) -> dict[str, object]:
    return {
        'job_id': job_id,
        'role_intent': 'engineering',
        'normalized_role': 'GIS开发工程师',
        'role_family': 'GIS工程',
        'technical_stack': [
            {
                'name': 'Python',
                'category': 'language',
                'importance': 'core',
                'evidence': [{'field': 'raw_job_text', 'quote': '使用 Python', 'interpretation': '核心开发语言'}],
            },
            {
                'name': 'PostGIS',
                'category': 'database',
                'importance': 'common',
                'evidence': [{'field': 'raw_job_text', 'quote': 'PostGIS', 'interpretation': '空间数据库'}],
            },
        ],
        'tools_platforms': [],
        'business_domains': [
            {
                'name': '空间数据处理',
                'category': 'domain',
                'importance': 'core',
                'evidence': [{'field': 'raw_job_text', 'quote': '空间数据处理', 'interpretation': '业务方向'}],
            }
        ],
        'ability_requirements': [
            {
                'name': '平台开发',
                'category': 'engineering',
                'importance': 'core',
                'evidence': [{'field': 'raw_job_text', 'quote': 'GIS 平台开发', 'interpretation': '岗位职责'}],
            }
        ],
        'experience_requirements': {'level': 'junior', 'summary': '不限经验', 'evidence': []},
        'education_requirements': {'level': '本科', 'summary': '本科', 'evidence': []},
        'graduate_friendliness': {
            'level': 'medium',
            'reason': '要求相对基础',
            'evidence': [{'field': 'raw_job_text', 'quote': '负责 GIS 平台开发', 'interpretation': '适合基础开发能力'}],
        },
        'evidence': [{'field': 'raw_job_text', 'quote': '负责 GIS 平台开发', 'interpretation': '岗位核心'}],
    }


def test_build_report_input_for_live_task(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_structured_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import report_input_service, task_service

    monkeypatch.setattr(report_input_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    monkeypatch.setattr(report_input_service, 'DATA_DIR', tmp_path)

    updated = task_service.build_report_input(task_id)

    stage = next(stage for stage in updated.stages if stage.stage_name == StageName.BUILD_REPORT_INPUT.value)
    assert stage.status == 'completed'
    assert updated.artifact_paths['report_input'].endswith('report_input.json')

    preview = task_service.get_report_input(task_id)
    assert preview.sample['total_jobs'] == 1
    assert preview.technical_terms_top
    assert preview.estimated_prompt_tokens > 0


def test_build_report_input_api_rejects_before_structuring(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / 'jobuwant-test.sqlite3'
    task_id = seed_sampled_task(db_path, monkeypatch)
    connect_temp = temp_connect(db_path)

    from app.services import report_input_service, task_service

    monkeypatch.setattr(report_input_service, 'connect', connect_temp)
    monkeypatch.setattr(task_service, 'connect', connect_temp)
    client = TestClient(create_app())

    response = client.post(f'/api/tasks/{task_id}/actions/build-report-input')

    assert response.status_code == 409
