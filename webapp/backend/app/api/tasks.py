from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import ApiResponse, ok
from app.schemas.tasks import AnalysisTaskCreate, AnalysisTaskRead, FinalReportRead, JobListRead, ReportInputPreview, SampleConfirmRequest, StructuringStatusRead, TaskDetailRead, TaskEventRead
from app.services import task_service

router = APIRouter(prefix='/api/tasks', tags=['tasks'])


@router.get('', response_model=ApiResponse[list[AnalysisTaskRead]])
def list_tasks() -> ApiResponse[list[AnalysisTaskRead]]:
    return ok(task_service.list_tasks())


@router.post('', response_model=ApiResponse[TaskDetailRead])
def create_task(payload: AnalysisTaskCreate) -> ApiResponse[TaskDetailRead]:
    return ok(task_service.create_task(payload), message='task created')


@router.post('/{task_id}/actions/start-collection', response_model=ApiResponse[TaskDetailRead])
def start_collection(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.start_collection(task_id), message='collection started')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post('/{task_id}/actions/start-scoring', response_model=ApiResponse[TaskDetailRead])
def start_scoring(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.start_scoring(task_id), message='scoring completed')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{task_id}/sample', response_model=ApiResponse[TaskDetailRead])
def save_sample(task_id: str, payload: SampleConfirmRequest) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.save_sample(task_id, payload), message='sample saved')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.post('/{task_id}/actions/start-structuring', response_model=ApiResponse[TaskDetailRead])
def start_structuring(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.start_structuring(task_id), message='structuring batches prepared')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{task_id}/actions/run-structuring-batches', response_model=ApiResponse[TaskDetailRead])
def run_structuring_batches(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.run_structuring_batches(task_id), message='structuring batches queued')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get('/{task_id}/structure', response_model=ApiResponse[StructuringStatusRead])
def get_structuring_status(task_id: str) -> ApiResponse[StructuringStatusRead]:
    try:
        return ok(task_service.get_structuring_status(task_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc

@router.get('/{task_id}', response_model=ApiResponse[TaskDetailRead])
def get_task(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.get_task_detail(task_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc


@router.get('/{task_id}/jobs', response_model=ApiResponse[JobListRead])
def get_jobs(
    task_id: str,
    match_status: str | None = None,
    role_intent: str | None = None,
    company_keyword: str | None = None,
    title_keyword: str | None = None,
    selected_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[JobListRead]:
    try:
        payload = task_service.list_jobs(
            task_id=task_id,
            match_status=match_status,
            role_intent=role_intent,
            company_keyword=company_keyword,
            title_keyword=title_keyword,
            selected_only=selected_only,
            limit=limit,
            offset=offset,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    return ok(payload)


@router.post('/{task_id}/actions/build-report-input', response_model=ApiResponse[TaskDetailRead])
def build_report_input(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.build_report_input(task_id), message='report input built')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get('/{task_id}/report-input', response_model=ApiResponse[ReportInputPreview])
def get_report_input(task_id: str) -> ApiResponse[ReportInputPreview]:
    try:
        return ok(task_service.get_report_input(task_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{task_id}/actions/write-final-report', response_model=ApiResponse[TaskDetailRead])
def write_final_report(task_id: str) -> ApiResponse[TaskDetailRead]:
    try:
        return ok(task_service.write_final_report(task_id), message='final report queued')
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get('/{task_id}/report', response_model=ApiResponse[FinalReportRead])
def get_report(task_id: str) -> ApiResponse[FinalReportRead]:
    try:
        return ok(task_service.get_final_report(task_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get('/{task_id}/events', response_model=ApiResponse[list[TaskEventRead]])
def get_events(task_id: str) -> ApiResponse[list[TaskEventRead]]:
    try:
        return ok(task_service.list_events(task_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'task not found: {task_id}') from exc





