from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.paths import DATA_DIR


@dataclass(frozen=True)
class FixtureTask:
    id: str
    task_name: str
    city: str
    city_code: str
    keyword: str
    job_type: str
    expected_job_count: int
    batch_size: int
    source_type: str
    search_run_id: int
    report_input_path: Path
    report_path: Path
    timing_path: Path | None = None


FIXTURE_TASKS: tuple[FixtureTask, ...] = (
    FixtureTask(
        id='hz-agent-intern-40',
        task_name='Hangzhou Agent engineer intern 40-job fixture',
        city='Hangzhou',
        city_code='101210100',
        keyword='Agent engineer',
        job_type='intern',
        expected_job_count=40,
        batch_size=10,
        source_type='boss_hz_agent_intern_20260726_probe40',
        search_run_id=7,
        report_input_path=DATA_DIR / 'job_report_input_hz_agent_intern_probe40.json',
        report_path=DATA_DIR / 'job_report_hz_agent_intern_probe40_v2.json',
    ),
    FixtureTask(
        id='gz-gis-any-30',
        task_name='Guangzhou GIS any-type 30-job fixture',
        city='Guangzhou',
        city_code='101280100',
        keyword='GIS',
        job_type='any',
        expected_job_count=30,
        batch_size=10,
        source_type='boss_gz_gis_any_20260727_probe30',
        search_run_id=8,
        report_input_path=DATA_DIR / 'job_report_input_gz_gis_any_probe30.json',
        report_path=DATA_DIR / 'job_report_gz_gis_any_probe30.json',
        timing_path=DATA_DIR / 'run_timing_gz_gis_any_probe30.json',
    ),
)


def list_fixtures() -> list[FixtureTask]:
    return list(FIXTURE_TASKS)


def get_fixture(task_id: str) -> FixtureTask:
    for fixture in FIXTURE_TASKS:
        if fixture.id == task_id:
            return fixture
    raise KeyError(task_id)
