# JobUWant Web Backend

Status: fixture-first backend skeleton created on 2026-07-28.

## Scope

This backend is the API boundary for the formal Web App. It currently exposes read-only fixture endpoints for the validated Hangzhou and Guangzhou runs.

It does not start new collection or model work yet.

## Implemented Files

- app/main.py: FastAPI app factory and health endpoint.
- app/api/tasks.py: fixture-first task, job, report-input, report, and event routes.
- app/repositories/database.py: task-level SQLite schema and connection helper.
- app/services/fixtures.py: fixture registry for search_run_id 7 and search_run_id 8.
- app/services/fixture_service.py: read-only service layer over SQLite and JSON artifacts.
- app/schemas/common.py: API response envelope.
- app/schemas/tasks.py: task, job, report, and event response schemas.
- tests/test_fixture_service.py: fixture service checks.

## Current Fixture Task IDs

- hz-agent-intern-40
- gz-gis-any-30

## Deferred

- Live task creation.
- Collection stage execution.
- Scoring stage write actions from API.
- Sample confirmation writes.
- AI structuring batch execution.
- Final report generation from API.

## Verification Used So Far

Latest verification after dependency installation:

- Dependency install completed in the existing project virtual environment.
- pytest passed: 4 tests passed.
- FastAPI app import passed.
- Local backend started at http://localhost:8000.
- HTTP checks passed for /api/health, /api/tasks, /api/tasks/gz-gis-any-30/jobs, /api/tasks/hz-agent-intern-40/report-input, and /api/tasks/gz-gis-any-30/report.
- Chinese report source JSON stores valid UTF-8; any mojibake seen in captured terminal output is from the terminal capture path.

Previous verification before dependency installation:

Syntax compile passed with the project virtual environment.

pytest was not run because pytest is not installed in the current virtual environment.

A direct service smoke check passed:

- hz-agent-intern-40: search_run_id 7, 40 collected jobs, 40 analysis-ready jobs.
- gz-gis-any-30: search_run_id 8, 30 collected jobs, 28 analysis-ready jobs.
- gz-gis-any-30 selected-only job list returned 28 rows.
- Hangzhou report input and Guangzhou final report JSON were readable.

## Start Command After Dependencies Are Installed

    cd /home/votally/projects/JobUWant/webapp/backend
    PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Collection Runner Status

`POST /api/tasks/{task_id}/actions/start-collection` is now connected to `app/runner/collection_runner.py`.

The route returns after queueing a one-worker local background runner. The runner derives collection parameters from the task row, executes the existing Python collection script, imports the resulting JSON, creates a `job_search_runs` row, records a `search_run` artifact, and then marks `collect_jobs` completed or failed.

Backend tests use fake runner functions and do not perform live collection.

## Scoring Action Status

`POST /api/tasks/{task_id}/actions/start-scoring` is now implemented.

It validates Harness order, reuses the collection `job_search_runs.id`, runs the existing local scoring module, records a `scored_jobs` artifact, and enables live task job rows through `GET /api/tasks/{task_id}/jobs`.

Backend tests cover success and pre-collection rejection without starting collection or model work.

## Sample Confirmation Status

`POST /api/tasks/{task_id}/sample` is now implemented.

It validates the task scoring run, writes a versioned sample, stores item-level selection state, records a `sample` artifact, and lets live job list responses reflect the latest saved selection.

## Structuring Batch Plan Status

`POST /api/tasks/{task_id}/actions/start-structuring` and `GET /api/tasks/{task_id}/structure` are now implemented for planning only.

The backend creates pending `batch_runs` from the confirmed sample and does not run model work. Actual batch execution remains deferred until explicit approval.

## Structuring Batch Runner Status

`POST /api/tasks/{task_id}/actions/run-structuring-batches` is now implemented.

It resumes the waiting AI structuring stage, queues a one-worker local runner, updates each `batch_runs` row, and records an `extractions` artifact after successful completion. Tests replace the real batch execution function and do not call a model.

## Report Input Generation Status

`POST /api/tasks/{task_id}/actions/build-report-input` is now implemented.

It requires completed structuring output, writes a `job_report_inputs` row, stores `data/task_artifacts/{task_id}/report_input.json`, records a `report_input` artifact, and enables live reads through `GET /api/tasks/{task_id}/report-input`.

Latest backend verification: 30 passed, 19 warnings.
## Final Report Generation Status

`POST /api/tasks/{task_id}/actions/write-final-report` is now implemented.

It requires a generated report input, queues `app/runner/final_report_runner.py`, writes a `job_reports` row, stores `data/task_artifacts/{task_id}/final_report.json`, records a `report` artifact, and enables live reads through `GET /api/tasks/{task_id}/report`.

Latest backend verification: 32 passed, 21 warnings.