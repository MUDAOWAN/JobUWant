from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisTaskCreate(BaseModel):
    task_name: str = Field(default='', max_length=120)
    city: str = Field(min_length=1, max_length=40)
    city_code: str = Field(default='', max_length=40)
    keyword: str = Field(min_length=1, max_length=80)
    job_type: str = Field(default='any', max_length=40)
    expected_job_count: int = Field(default=30, ge=1, le=200)
    batch_size: int = Field(default=10, ge=1, le=100)
    source_type: str = Field(default='', max_length=160)
    notes: str = Field(default='', max_length=1000)


class FixtureBinding(BaseModel):
    fixture_id: str
    source_type: str
    search_run_id: int
    report_input_path: str
    report_path: str
    timing_path: str = ''


class AnalysisTaskRead(BaseModel):
    id: str
    task_name: str
    city: str
    city_code: str = ''
    keyword: str
    job_type: str
    expected_job_count: int
    batch_size: int
    status: str
    source_type: str
    search_run_id: int
    collected_count: int = 0
    analysis_ready_count: int = 0
    created_at: str = ''
    updated_at: str = ''
    fixture: FixtureBinding


class TaskStageRunRead(BaseModel):
    stage_name: str
    status: str
    elapsed_seconds: float = 0
    message: str = ''




class TaskMetricsRead(BaseModel):
    collection_seconds: float = 0
    scoring_seconds: float = 0
    analysis_seconds: float = 0
    total_elapsed_seconds: float = 0
    average_match_score: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cny: float = 0
    usage_recorded: bool = False

class TaskDetailRead(BaseModel):
    task: AnalysisTaskRead
    metrics: TaskMetricsRead = Field(default_factory=TaskMetricsRead)
    stages: list[TaskStageRunRead] = Field(default_factory=list)
    match_status_counts: dict[str, int] = Field(default_factory=dict)
    role_intent_counts: dict[str, int] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)


class JobRowRead(BaseModel):
    job_id: int
    company_name: str
    job_title: str
    city: str
    original_url: str = ''
    match_score: float
    match_status: str
    role_intent: str
    review_reasons: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    description_length: int
    salary: str = ''
    experience: str = ''
    education: str = ''
    selected: bool = True


class JobListRead(BaseModel):
    task_id: str
    total: int
    limit: int
    offset: int
    rows: list[JobRowRead]

class SampleConfirmRequest(BaseModel):
    selected_job_ids: list[int] = Field(default_factory=list)
    excluded_job_ids: list[int] = Field(default_factory=list)
    selection_note: str = Field(default='', max_length=1000)


class StructuringBatchRead(BaseModel):
    batch_id: int
    sample_id: int
    stage_run_id: int = 0
    batch_index: int
    batch_size: int
    job_ids: list[int] = Field(default_factory=list)
    status: str
    model_name: str = ''
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cny: float = 0
    elapsed_seconds: float = 0
    error_code: str = ''
    error_message: str = ''
    created_at: str = ''
    updated_at: str = ''


class StructuringStatusRead(BaseModel):
    task_id: str
    sample_id: int = 0
    sample_version: int = 0
    selected_count: int = 0
    batch_size: int = 0
    total_batches: int = 0
    batches: list[StructuringBatchRead] = Field(default_factory=list)

class ReportInputPreview(BaseModel):
    task_id: str
    path: str
    query: dict[str, object] = Field(default_factory=dict)
    sample: dict[str, object] = Field(default_factory=dict)
    technical_terms_top: list[dict[str, object]] = Field(default_factory=list)
    salary_summary: dict[str, object] = Field(default_factory=dict)
    evidence_quality: dict[str, object] = Field(default_factory=dict)
    estimated_prompt_tokens: int = 0
    raw: dict[str, object] = Field(default_factory=dict)


class FinalReportRead(BaseModel):
    task_id: str
    path: str
    report_title: str = ''
    audience_summary: str = ''
    sections: dict[str, object] = Field(default_factory=dict)
    raw: dict[str, object] = Field(default_factory=dict)


class TaskEventRead(BaseModel):
    id: int
    level: str = 'info'
    event_type: str
    message: str
    created_at: str = ''
    payload: dict[str, object] = Field(default_factory=dict)



