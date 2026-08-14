const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ApiResponse<T> = {
  trace_id: string;
  status: string;
  message: string;
  data: T;
  error?: {
    code: string;
    message: string;
    detail: Record<string, unknown>;
  } | null;
};

export type FixtureBinding = {
  fixture_id: string;
  source_type: string;
  search_run_id: number;
  report_input_path: string;
  report_path: string;
  timing_path: string;
};

export type SupportedCity = {
  name: string;
  province: string;
  city_code: string;
  tier: string;
  verified: boolean;
};

export type AnalysisTask = {
  id: string;
  task_name: string;
  city: string;
  city_code: string;
  keyword: string;
  job_type: string;
  expected_job_count: number;
  batch_size: number;
  status: string;
  source_type: string;
  search_run_id: number;
  collected_count: number;
  analysis_ready_count: number;
  created_at: string;
  updated_at: string;
  fixture: FixtureBinding;
};

export type AnalysisTaskCreate = {
  task_name?: string;
  city: string;
  city_code?: string;
  keyword: string;
  job_type?: string;
  expected_job_count?: number;
  batch_size?: number;
  source_type?: string;
  notes?: string;
};

export type TaskMetrics = {
  collection_seconds: number;
  scoring_seconds: number;
  analysis_seconds: number;
  total_elapsed_seconds: number;
  average_match_score: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cny: number;
  usage_recorded: boolean;
};

export type TaskStageRun = {
  stage_name: string;
  status: string;
  elapsed_seconds: number;
  message: string;
};

export type TaskDetail = {
  task: AnalysisTask;
  metrics: TaskMetrics;
  stages: TaskStageRun[];
  match_status_counts: Record<string, number>;
  role_intent_counts: Record<string, number>;
  artifact_paths: Record<string, string>;
};

export type JobRow = {
  job_id: number;
  company_name: string;
  job_title: string;
  city: string;
  original_url: string;
  match_score: number;
  match_status: string;
  role_intent: string;
  review_reasons: string[];
  match_reasons: string[];
  description_length: number;
  salary: string;
  experience: string;
  education: string;
  selected: boolean;
};

export type JobList = {
  task_id: string;
  total: number;
  limit: number;
  offset: number;
  rows: JobRow[];
};

export type JobListParams = {
  match_status?: string;
  role_intent?: string;
  company_keyword?: string;
  title_keyword?: string;
  selected_only?: boolean;
  limit?: number;
  offset?: number;
};

export type SampleConfirmRequest = {
  selected_job_ids: number[];
  excluded_job_ids?: number[];
  selection_note?: string;
};

export type TaskEvent = {
  id: number;
  level: string;
  event_type: string;
  message: string;
  created_at: string;
  payload: Record<string, unknown>;
};

export type StructuringBatch = {
  batch_id: number;
  sample_id: number;
  stage_run_id: number;
  batch_index: number;
  batch_size: number;
  job_ids: number[];
  status: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cny: number;
  elapsed_seconds: number;
  error_code: string;
  error_message: string;
  created_at: string;
  updated_at: string;
};

export type StructuringStatus = {
  task_id: string;
  sample_id: number;
  sample_version: number;
  selected_count: number;
  batch_size: number;
  total_batches: number;
  batches: StructuringBatch[];
};

export type TechnicalTermItem = {
  name?: string;
  key?: string;
  count?: number;
  ratio?: number;
  score?: number;
  exact_evidence_ratio?: number;
  job_ids?: number[];
  sources?: Record<string, number>;
  importance_distribution?: Record<string, number>;
  evidence?: Array<Record<string, unknown>>;
};

export type ReportInputPreview = {
  task_id: string;
  path: string;
  query: Record<string, unknown>;
  sample: Record<string, unknown>;
  technical_terms_top: TechnicalTermItem[];
  salary_summary: Record<string, unknown>;
  evidence_quality: Record<string, unknown>;
  estimated_prompt_tokens: number;
  raw: Record<string, unknown>;
};

export type FinalReportRead = {
  task_id: string;
  path: string;
  report_title: string;
  audience_summary: string;
  sections: Record<string, unknown>;
  raw: Record<string, unknown>;
};

export type Health = {
  service: string;
  status: string;
};

type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  const rawPayload = await response.json().catch(() => null) as ApiResponse<T> | { detail?: unknown } | null;
  if (!response.ok) {
    const detail = rawPayload && "detail" in rawPayload ? rawPayload.detail : undefined;
    throw new Error(typeof detail === "string" ? detail : `Request failed with ${response.status}`);
  }

  const payload = rawPayload as ApiResponse<T>;
  if (payload.status !== "ok") {
    throw new Error(payload.error?.message ?? payload.message ?? "Request failed");
  }

  return payload.data;
}

export function getHealth() {
  return request<Health>("/api/health");
}

export function listTasks() {
  return request<AnalysisTask[]>("/api/tasks");
}

export function listCities() {
  return request<SupportedCity[]>("/api/cities");
}

export function createTask(payload: AnalysisTaskCreate) {
  return request<TaskDetail>("/api/tasks", { method: "POST", body: payload });
}

export function getTaskDetail(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}`);
}

export function getTaskEvents(taskId: string) {
  return request<TaskEvent[]>(`/api/tasks/${taskId}/events`);
}

export function getStructuringStatus(taskId: string) {
  return request<StructuringStatus>(`/api/tasks/${taskId}/structure`);
}

export function getReportInput(taskId: string) {
  return request<ReportInputPreview>(`/api/tasks/${taskId}/report-input`);
}

export function getFinalReport(taskId: string) {
  return request<FinalReportRead>(`/api/tasks/${taskId}/report`);
}

export function listJobs(taskId: string, params: JobListParams = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return request<JobList>(`/api/tasks/${taskId}/jobs${suffix}`);
}

export function startCollection(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/start-collection`, { method: "POST" });
}

export function cancelTask(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/cancel`, { method: "POST" });
}
export function startScoring(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/start-scoring`, { method: "POST" });
}

export function saveSample(taskId: string, payload: SampleConfirmRequest) {
  return request<TaskDetail>(`/api/tasks/${taskId}/sample`, { method: "POST", body: payload });
}

export function startStructuring(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/start-structuring`, { method: "POST" });
}

export function runStructuringBatches(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/run-structuring-batches`, { method: "POST" });
}

export function buildReportInput(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/build-report-input`, { method: "POST" });
}

export function writeFinalReport(taskId: string) {
  return request<TaskDetail>(`/api/tasks/${taskId}/actions/write-final-report`, { method: "POST" });
}
