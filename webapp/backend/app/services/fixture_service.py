from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from app.repositories.database import connect
from app.schemas.tasks import (
    AnalysisTaskRead,
    FinalReportRead,
    FixtureBinding,
    JobListRead,
    JobRowRead,
    ReportInputPreview,
    TaskDetailRead,
    TaskEventRead,
    TaskStageRunRead,
)
from app.services.fixtures import FixtureTask, get_fixture, list_fixtures


ANALYSIS_READY_STATUSES = {'strong_match', 'review'}


def list_tasks(conn: sqlite3.Connection | None = None) -> list[AnalysisTaskRead]:
    own_conn = conn is None
    conn = conn or connect()
    try:
        return [build_task_read(conn, fixture) for fixture in list_fixtures()]
    finally:
        if own_conn:
            conn.close()


def get_task_detail(task_id: str, conn: sqlite3.Connection | None = None) -> TaskDetailRead:
    fixture = get_fixture(task_id)
    own_conn = conn is None
    conn = conn or connect()
    try:
        task = build_task_read(conn, fixture)
        return TaskDetailRead(
            task=task,
            stages=build_fixture_stages(conn, fixture),
            match_status_counts=count_field(conn, fixture.search_run_id, 'match_status'),
            role_intent_counts=count_field(conn, fixture.search_run_id, 'role_intent'),
            artifact_paths={
                'report_input': relative_path(fixture.report_input_path),
                'report': relative_path(fixture.report_path),
                'timing': relative_path(fixture.timing_path) if fixture.timing_path else '',
            },
        )
    finally:
        if own_conn:
            conn.close()


def list_jobs(
    task_id: str,
    match_status: str | None = None,
    role_intent: str | None = None,
    company_keyword: str | None = None,
    title_keyword: str | None = None,
    selected_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> JobListRead:
    fixture = get_fixture(task_id)
    own_conn = conn is None
    conn = conn or connect()
    try:
        rows = load_job_rows(conn, fixture.search_run_id)
        rows = filter_jobs(
            rows,
            match_status=match_status,
            role_intent=role_intent,
            company_keyword=company_keyword,
            title_keyword=title_keyword,
            selected_only=selected_only,
        )
        total = len(rows)
        safe_limit = min(max(limit, 1), 200)
        safe_offset = max(offset, 0)
        return JobListRead(
            task_id=task_id,
            total=total,
            limit=safe_limit,
            offset=safe_offset,
            rows=rows[safe_offset:safe_offset + safe_limit],
        )
    finally:
        if own_conn:
            conn.close()


def get_report_input(task_id: str) -> ReportInputPreview:
    fixture = get_fixture(task_id)
    payload = read_json(fixture.report_input_path)
    return ReportInputPreview(
        task_id=task_id,
        path=relative_path(fixture.report_input_path),
        query=dict_value(payload.get('query')),
        sample=dict_value(payload.get('sample')),
        technical_terms_top=list_value(payload.get('technical_terms_top'))[:15],
        salary_summary=dict_value(payload.get('salary_summary')),
        evidence_quality=dict_value(payload.get('evidence_quality')),
        estimated_prompt_tokens=int(payload.get('estimated_prompt_tokens') or 0),
        raw=payload,
    )


def get_final_report(task_id: str) -> FinalReportRead:
    fixture = get_fixture(task_id)
    payload = read_json(fixture.report_path)
    sections = {
        key: value
        for key, value in payload.items()
        if key not in {'report_title', 'audience_summary'}
    }
    return FinalReportRead(
        task_id=task_id,
        path=relative_path(fixture.report_path),
        report_title=str(payload.get('report_title') or ''),
        audience_summary=str(payload.get('audience_summary') or ''),
        sections=sections,
        raw=payload,
    )


def list_events(task_id: str) -> list[TaskEventRead]:
    fixture = get_fixture(task_id)
    events = [
        TaskEventRead(id=1, event_type='fixture_bound', message=f'Fixture is bound to search_run_id {fixture.search_run_id}.'),
        TaskEventRead(id=2, event_type='report_input_ready', message=f'Report input: {relative_path(fixture.report_input_path)}'),
        TaskEventRead(id=3, event_type='report_ready', message=f'Final report: {relative_path(fixture.report_path)}'),
    ]
    if fixture.timing_path and fixture.timing_path.exists():
        events.append(TaskEventRead(id=4, event_type='timing_ready', message=f'Timing: {relative_path(fixture.timing_path)}'))
    return events


def build_task_read(conn: sqlite3.Connection, fixture: FixtureTask) -> AnalysisTaskRead:
    run = conn.execute(
        '''
        SELECT id, source_type, collected_count, analysis_ready_count, status, created_at, updated_at
        FROM job_search_runs
        WHERE id = ?
        ''',
        (fixture.search_run_id,),
    ).fetchone()
    if run is None:
        collected_count = 0
        analysis_ready_count = 0
        status = 'missing_fixture'
        created_at = ''
        updated_at = ''
    else:
        collected_count = int(run['collected_count'] or 0)
        analysis_ready_count = int(run['analysis_ready_count'] or 0)
        status = 'completed' if str(run['status']) == 'completed' else str(run['status'])
        created_at = str(run['created_at'] or '')
        updated_at = str(run['updated_at'] or '')
    return AnalysisTaskRead(
        id=fixture.id,
        task_name=fixture.task_name,
        city=fixture.city,
        city_code=fixture.city_code,
        keyword=fixture.keyword,
        job_type=fixture.job_type,
        expected_job_count=fixture.expected_job_count,
        batch_size=fixture.batch_size,
        status=status,
        source_type=fixture.source_type,
        search_run_id=fixture.search_run_id,
        collected_count=collected_count,
        analysis_ready_count=analysis_ready_count,
        created_at=created_at,
        updated_at=updated_at,
        fixture=FixtureBinding(
            fixture_id=fixture.id,
            source_type=fixture.source_type,
            search_run_id=fixture.search_run_id,
            report_input_path=relative_path(fixture.report_input_path),
            report_path=relative_path(fixture.report_path),
            timing_path=relative_path(fixture.timing_path) if fixture.timing_path else '',
        ),
    )


def build_fixture_stages(conn: sqlite3.Connection, fixture: FixtureTask) -> list[TaskStageRunRead]:
    jobs = count_total_jobs(conn, fixture.search_run_id)
    extracted = count_extractions(conn, fixture.search_run_id)
    report_input_exists = fixture.report_input_path.exists()
    report_exists = fixture.report_path.exists()
    return [
        TaskStageRunRead(stage_name='collect_jobs', status='completed', message=f'{jobs} jobs available in SQLite.'),
        TaskStageRunRead(stage_name='score_jobs', status='completed', message=f'search_run_id {fixture.search_run_id} is available.'),
        TaskStageRunRead(stage_name='confirm_sample', status='completed', message='Fixture defaults to strong_match plus review jobs.'),
        TaskStageRunRead(stage_name='ai_structuring', status='completed', message=f'{extracted} extracted jobs found.'),
        TaskStageRunRead(stage_name='build_report_input', status='completed' if report_input_exists else 'failed', message=relative_path(fixture.report_input_path)),
        TaskStageRunRead(stage_name='write_final_report', status='completed' if report_exists else 'failed', message=relative_path(fixture.report_path)),
    ]


def load_job_rows(conn: sqlite3.Connection, search_run_id: int) -> list[JobRowRead]:
    rows = conn.execute(
        '''
        SELECT
            jd.id AS job_id,
            jd.company_name,
            jd.job_title,
            jd.city,
            jd.original_url,
            jd.raw_job_text,
            jd.source_metadata_json,
            sri.match_score,
            sri.match_status,
            sri.role_intent,
            sri.match_reasons_json,
            sri.review_reasons_json
        FROM job_search_run_items sri
        JOIN job_details jd ON jd.id = sri.job_detail_id
        WHERE sri.search_run_id = ?
        ORDER BY sri.match_score DESC, jd.id
        ''',
        (search_run_id,),
    ).fetchall()
    output: list[JobRowRead] = []
    for row in rows:
        metadata = parse_json_object(row['source_metadata_json'])
        match_reasons_payload = parse_json_object(row['match_reasons_json'])
        output.append(
            JobRowRead(
                job_id=int(row['job_id']),
                company_name=str(row['company_name'] or ''),
                job_title=str(row['job_title'] or ''),
                city=str(row['city'] or ''),
                original_url=str(row['original_url'] or ''),
                match_score=float(row['match_score'] or 0),
                match_status=str(row['match_status'] or ''),
                role_intent=str(row['role_intent'] or ''),
                review_reasons=parse_json_list(row['review_reasons_json']),
                match_reasons=parse_json_list(match_reasons_payload.get('reasons')),
                description_length=len(str(row['raw_job_text'] or '')),
                salary=str(metadata.get('salary') or ''),
                experience=str(metadata.get('experience') or ''),
                education=str(metadata.get('education') or ''),
                selected=str(row['match_status'] or '') in ANALYSIS_READY_STATUSES,
            )
        )
    return output


def filter_jobs(
    rows: list[JobRowRead],
    match_status: str | None,
    role_intent: str | None,
    company_keyword: str | None,
    title_keyword: str | None,
    selected_only: bool,
) -> list[JobRowRead]:
    result = rows
    if match_status:
        result = [row for row in result if row.match_status == match_status]
    if role_intent:
        result = [row for row in result if row.role_intent == role_intent]
    if company_keyword:
        needle = company_keyword.lower()
        result = [row for row in result if needle in row.company_name.lower()]
    if title_keyword:
        needle = title_keyword.lower()
        result = [row for row in result if needle in row.job_title.lower()]
    if selected_only:
        result = [row for row in result if row.selected]
    return result


def count_field(conn: sqlite3.Connection, search_run_id: int, field_name: str) -> dict[str, int]:
    if field_name not in {'match_status', 'role_intent'}:
        raise ValueError('unsupported count field')
    rows = conn.execute(
        f'''
        SELECT {field_name} AS name, COUNT(*) AS count
        FROM job_search_run_items
        WHERE search_run_id = ?
        GROUP BY {field_name}
        ORDER BY {field_name}
        ''',
        (search_run_id,),
    ).fetchall()
    return {str(row['name']): int(row['count']) for row in rows}


def count_total_jobs(conn: sqlite3.Connection, search_run_id: int) -> int:
    row = conn.execute('SELECT COUNT(*) AS count FROM job_search_run_items WHERE search_run_id = ?', (search_run_id,)).fetchone()
    return int(row['count'] or 0)


def count_extractions(conn: sqlite3.Connection, search_run_id: int) -> int:
    row = conn.execute(
        '''
        SELECT COUNT(DISTINCT sri.job_detail_id) AS count
        FROM job_search_run_items sri
        JOIN job_extractions je ON je.job_detail_id = sri.job_detail_id AND je.status = 'completed'
        WHERE sri.search_run_id = ?
        ''',
        (search_run_id,),
    ).fetchone()
    return int(row['count'] or 0)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'expected object JSON in {path}')
    return payload


def parse_json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value or '{}'))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_json_list(value: object) -> list[str]:
    if isinstance(value, list):
        source = value
    else:
        try:
            source = json.loads(str(value or '[]'))
        except json.JSONDecodeError:
            return []
    if not isinstance(source, list):
        return []
    return [str(item) for item in source if str(item).strip()]


def dict_value(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def relative_path(path: Path | None) -> str:
    if path is None:
        return ''
    try:
        return str(path.relative_to(Path('/home/votally/projects/JobUWant')))
    except ValueError:
        return str(path)
