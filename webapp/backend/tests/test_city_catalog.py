from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.city_catalog import resolve_city
from app.main import create_app
from app.repositories import analysis_tasks
from app.repositories.database import initialize_task_tables
from app.schemas.tasks import AnalysisTaskCreate


def memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    initialize_task_tables(conn)
    return conn


def test_resolve_city_normalizes_supported_city() -> None:
    city = resolve_city('杭州市')

    assert city.name == '杭州'
    assert city.city_code == '101210100'
    assert city.verified is True


def test_resolve_city_rejects_unknown_city() -> None:
    with pytest.raises(ValueError, match='unsupported city'):
        resolve_city('A市')


def test_resolve_city_rejects_mismatched_code() -> None:
    with pytest.raises(ValueError, match='city_code does not match city'):
        resolve_city('杭州', '101280100')


def test_create_task_infers_city_code() -> None:
    conn = memory_conn()
    detail = analysis_tasks.create_task(conn, AnalysisTaskCreate(city='成都', keyword='后端工程师'))

    assert detail.task.city == '成都'
    assert detail.task.city_code == '101270100'


def test_cities_api_returns_supported_city_list() -> None:
    client = TestClient(create_app())
    response = client.get('/api/cities')

    assert response.status_code == 200
    data = response.json()['data']
    assert any(city['name'] == '杭州' and city['city_code'] == '101210100' for city in data)
