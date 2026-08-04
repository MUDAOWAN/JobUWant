# JobUWant Web App Harness

Status: live Harness flow through final report generation is implemented as of 2026-08-02.

## Purpose

The Web App Harness is the task execution control layer for the formal JobUWant Web App.

It defines how one analysis task moves from job collection to final report generation, and keeps API handlers, background execution, SQLite state, and frontend pages aligned around the same lifecycle.

The first implementation is intentionally lightweight and in-repo. It does not introduce a queue framework yet.

## Current Scope

Implemented in code:

- Backend module: `webapp/backend/app/services/task_harness.py`
- Tests: `webapp/backend/tests/test_task_harness.py`

This baseline defines:

- task statuses
- stage statuses
- stage names
- action names
- linear stage order
- artifact types per stage
- user-confirmation stage marker
- next-stage calculation
- action availability checks
- task status derivation from stage statuses
- documentable manifest output

It now governs collection, local scoring, sample confirmation, structuring batch planning, explicit structuring execution, report input generation, and final report generation.

## Technical Stack In This Phase

- Backend: FastAPI
- Backend schemas: Pydantic
- Backend language: Python
- Persistence target: SQLite
- Frontend: Next.js plus TypeScript
- UI: Tailwind-style utility classes
- Charts: Recharts
- Execution management: lightweight in-repo Harness service
- Current mode: fixture-first read-only pages plus Harness foundation

## Stage Flow

The Harness stage order is fixed for the first executable Web App version:

1. `collect_jobs` - 采集岗位
2. `score_jobs` - 本地评分
3. `confirm_sample` - 确认样本
4. `ai_structuring` - AI 结构�?5. `build_report_input` - 生成报告输入
6. `write_final_report` - 生成最终报�?
The frontend should display these stages in this order. The backend should only allow an action when its previous stage has completed.

## Task Statuses

- `draft`: task has been created but is not ready to run.
- `ready`: task has enough input to start or continue.
- `running`: one stage is currently running.
- `waiting_for_sample`: the task is waiting for user sample confirmation.
- `completed`: all stages completed.
- `failed`: one stage failed.
- `canceled`: task was manually stopped.

## Stage Statuses

- `pending`: stage has not started.
- `running`: stage is currently executing.
- `waiting_for_user`: stage needs user confirmation before continuing.
- `completed`: stage completed successfully.
- `failed`: stage failed and needs user attention.
- `skipped`: stage was intentionally skipped by a controlled rule.

## Actions

Each write endpoint should map to one Harness action:

- `start_collection` -> `collect_jobs`
- `start_scoring` -> `score_jobs`
- `save_sample` -> `confirm_sample`
- `start_structuring` -> `ai_structuring`
- `build_report_input` -> `build_report_input`
- `write_final_report` -> `write_final_report`

API handlers should validate the requested action through the Harness before they call any service that changes task state.

## Artifact Types

Stages should record their outputs as task artifacts:

- `search_run`
- `scored_jobs`
- `sample`
- `extractions`
- `batch_runs`
- `report_input`
- `report`

This gives the frontend stable places to find task outputs without knowing low-level implementation details.

## Repository Integration Plan

The next backend step should add repositories around the existing task tables:

- `analysis_tasks`
- `task_stage_runs`
- `task_events`
- `task_artifacts`
- `analysis_samples`
- `analysis_sample_items`
- `batch_runs`

The repository layer should be responsible for:

- creating a task
- initializing stage rows
- appending task events
- recording artifacts
- reading current stage statuses
- marking a stage running, completed, waiting, or failed

## API Integration Plan

The next API step should add live task endpoints around the Harness:

- `POST /api/tasks` - implemented
- `POST /api/tasks/{task_id}/actions/start-collection` - implemented as Harness state boundary
- `POST /api/tasks/{task_id}/actions/start-scoring`
- `POST /api/tasks/{task_id}/sample`
- `POST /api/tasks/{task_id}/actions/start-structuring`
- `POST /api/tasks/{task_id}/actions/build-report-input`
- `POST /api/tasks/{task_id}/actions/write-final-report`

The current fixture endpoints remain valid and should continue to work while live task endpoints are added.

## Frontend Integration Rule

The frontend should not invent hidden task state.

For each task page, read task status, stage status, events, and artifacts from the backend. Buttons should be enabled only when the Harness says the corresponding action is available.

## Verification

Baseline verification on 2026-07-31:

- `PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 9 passed.
## Implemented Action Boundary

`POST /api/tasks/{task_id}/actions/start-collection` is implemented as the first Harness action endpoint.

Current behavior:

- validates the task id is a live task id such as `task-1`
- validates the Harness order through `start_collection`
- marks `collect_jobs` as `running`
- marks the task as `running`
- appends a `collect_jobs_started` event
- rejects duplicate starts with HTTP 409 through the API layer

The actual Python collection runner is intentionally not connected in this step. The next step should connect the runner and call repository helpers to mark the stage completed or failed.
## 2026-07-31 Collection Runner Boundary

The first real runner boundary is now connected for `start_collection`.

Implementation files:

- `webapp/backend/app/runner/collection_runner.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/app/repositories/analysis_tasks.py`

Execution shape:

1. API validates the Harness action and collection inputs.
2. Repository marks `collect_jobs` as `running` and records `collect_jobs_started`.
3. Service submits work to a one-worker local executor and returns immediately.
4. Runner calls the existing slow BOSS collection script with task-derived arguments.
5. Runner imports the output JSON through the existing BOSS adapter.
6. Runner creates a `job_search_runs` row and records it as a `search_run` artifact.
7. Runner marks the collection stage `completed` or `failed`.

The tests use fake runner functions and do not perform real collection.

## 2026-08-01 Scoring Action Boundary

`POST /api/tasks/{task_id}/actions/start-scoring` is now connected to the existing local scoring chain.

Execution shape:

1. API calls `task_service.start_scoring`.
2. Service delegates to `webapp/backend/app/services/scoring_service.py`.
3. Scoring service validates that collection produced a `search_run` artifact.
4. Harness marks `score_jobs` as `running`.
5. Existing local scoring writes match rows and local terms into SQLite.
6. Harness marks `score_jobs` as `completed` and records a `scored_jobs` artifact.

A rejected scoring action before collection completion returns a conflict response and leaves task state unchanged.

## 2026-08-01 Sample Confirmation Boundary

`POST /api/tasks/{task_id}/sample` now implements the Harness `save_sample` action.

Execution shape:

1. API receives selected job ids and optional note.
2. Sample service validates the latest `scored_jobs` artifact.
3. Sample service validates job ids against the task `job_search_run_items`.
4. Harness marks `confirm_sample` as `running`.
5. Repository writes `analysis_samples` and `analysis_sample_items`.
6. Harness marks `confirm_sample` as `completed` and records a `sample` artifact.

Invalid input before the stage starts returns a conflict response and leaves task state unchanged.

## 2026-08-01 Structuring Batch Plan Boundary

`POST /api/tasks/{task_id}/actions/start-structuring` now implements the planning boundary for the Harness `start_structuring` action.

Current execution shape:

1. API validates Harness order.
2. Structuring service reads the latest confirmed sample.
3. Repository creates `batch_runs` rows with status `pending`.
4. Service records a `batch_runs` artifact.
5. Harness marks `ai_structuring` as `waiting_for_user`.

No model call is made in this phase. A repeated start request while the stage is waiting is rejected.

## 2026-08-01 Structuring Batch Execution Boundary

The AI structuring stage now has two explicit backend steps:

1. `start_structuring`: create pending batch plans and wait for user confirmation.
2. `run_structuring_batches`: resume the waiting stage and submit model execution to the local runner.

Runner file:

- `webapp/backend/app/runner/structuring_runner.py`

Execution behavior:

- One local worker processes pending batches sequentially.
- Batch state is persisted before and after each batch.
- Successful completion records an `extractions` artifact.
- A failed batch records its own error and marks the stage failed.

Tests use fake batch execution and do not call a model.

## 2026-08-02 Report Input Boundary

`POST /api/tasks/{task_id}/actions/build-report-input` now implements the Harness `build_report_input` action.

Execution shape:

1. API calls `task_service.build_report_input`.
2. Service delegates to `webapp/backend/app/services/report_input_service.py`.
3. The service validates Harness order, latest confirmed sample, and matching `extractions` artifact.
4. Harness marks `build_report_input` as `running`.
5. Existing `jobuwant.job_report` functions build and store the compact report input.
6. Harness marks `build_report_input` as `completed` and records a `report_input` artifact.

This action is local database and JSON assembly only. It does not perform model work.
## 2026-08-02 Final Report Boundary

`POST /api/tasks/{task_id}/actions/write-final-report` now implements the Harness `write_final_report` action.

Execution shape:

1. API calls `task_service.write_final_report`.
2. Service delegates to `webapp/backend/app/services/final_report_service.py`.
3. The service validates Harness order and the latest `report_input` artifact.
4. Harness marks `write_final_report` as `running`.
5. Service submits `webapp/backend/app/runner/final_report_runner.py` to the local one-worker executor.
6. Runner loads the report input and calls the existing `jobuwant.ai_report_writer` functions.
7. Runner stores `job_reports`, writes the JSON artifact, records usage, and marks the stage completed or failed.

Backend tests replace the real report writer and do not perform model work.