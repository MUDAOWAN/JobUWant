# Web App API Contracts

Status: live execution endpoints through final report generation are implemented as of 2026-08-02.

## Response Envelope

All API responses use the same envelope:

- `trace_id`: request trace id.
- `status`: `ok` or `error`.
- `message`: human-readable short message.
- `data`: endpoint payload.
- `error`: optional object with code, message, and detail.

## Implemented Endpoints

GET /api/health

- Purpose: service health check.
- Returns: service name and status.

GET /api/tasks

- Purpose: list analysis tasks.
- Returns: live SQLite tasks first, then fixture task records.
- Fixture records currently include search_run_id 7 and search_run_id 8.

POST /api/tasks

- Status: implemented on 2026-07-31.
- Purpose: create a user-facing analysis task without starting collection.
- Request body: `task_name`, `city`, `city_code`, `keyword`, `job_type`, `expected_job_count`, `batch_size`, `source_type`, `notes`.
- Harness role: initializes all six task stages from the Harness manifest as `pending`.
- Returns: task detail, initialized stages, empty counts, and empty artifact paths.
- Side effects: writes one `analysis_tasks` row, six `task_stage_runs` rows, and one `task_events` row.

GET /api/tasks/{task_id}

- Purpose: task detail.
- Fixture tasks return task summary, stage summaries, match status counts, role intent counts, and artifact paths.
- Live tasks return task summary, initialized stage rows, empty counts, and artifact paths recorded so far.

GET /api/tasks/{task_id}/jobs

- Purpose: job sample table data.
- Query params: `match_status`, `role_intent`, `company_keyword`, `title_keyword`, `selected_only`, `limit`, `offset`.
- Fixture tasks return rows from `job_details` joined with `job_search_run_items`.
- Live tasks return an empty list until collection and scoring are connected.

GET /api/tasks/{task_id}/report-input

- Purpose: read compact report input JSON for preview.
- Fixture tasks return query, sample, top technical terms, salary summary, evidence quality, estimated prompt tokens, and raw JSON.
- Live tasks return the generated report input after `POST /api/tasks/{task_id}/actions/build-report-input` completes.

GET /api/tasks/{task_id}/report

- Purpose: read final report JSON.
- Fixture tasks return report title, audience summary, sections, and raw JSON.
- Live tasks return the generated final report after `POST /api/tasks/{task_id}/actions/write-final-report` completes.

GET /api/tasks/{task_id}/events

- Purpose: task event list.
- Fixture tasks return synthetic events describing fixture binding and artifact availability.
- Live tasks return persisted rows from `task_events`.

## Fixture Task IDs

- `hz-agent-intern-40`: Hangzhou Agent engineer intern 40-job fixture, search_run_id 7.
- `gz-gis-any-30`: Guangzhou GIS any-type 30-job fixture, search_run_id 8.

## Live Task ID Format

Live tasks use public ids in this format:

- `task-{integer_id}`

Example:

- `task-1`

The integer id maps to `analysis_tasks.id` internally.

POST /api/tasks/{task_id}/actions/start-collection

- Status: implemented on 2026-07-31 as a Harness state boundary.
- Purpose: start the collection stage for a live task.
- Harness action: `start_collection`.
- Returns: updated task detail.
- Side effects: marks `collect_jobs` as `running`, marks the task as `running`, and appends a `collect_jobs_started` event.
- Current limitation: the existing Python collection runner is not connected yet, so this endpoint does not fetch new job data by itself.

## Live Execution Endpoint Status

The Harness write endpoints from task creation through final report generation are implemented. Long-running work is still started only by explicit action endpoints.

## Harness-Governed Live Endpoint Order

The live write endpoints should be governed by `webapp/backend/app/services/task_harness.py`:

1. `POST /api/tasks` - implemented
2. `POST /api/tasks/{task_id}/actions/start-collection` - implemented as Harness state boundary
3. `POST /api/tasks/{task_id}/actions/start-scoring`
4. `POST /api/tasks/{task_id}/sample`
5. `POST /api/tasks/{task_id}/actions/start-structuring`
6. `POST /api/tasks/{task_id}/actions/build-report-input`
7. `POST /api/tasks/{task_id}/actions/write-final-report`
## 2026-07-31 Collection Runner Update

`POST /api/tasks/{task_id}/actions/start-collection` now connects to a local background collection runner.

Updated behavior:

- live tasks only
- validates `city_code`, `keyword`, `job_type`, and `expected_job_count` before stage start
- marks `collect_jobs` as `running`
- marks the task as `running`
- appends `collect_jobs_started` with runner status `queued`
- submits the collection job to a one-worker in-process executor
- returns immediately; clients should poll task detail and events

Runner completion behavior:

- on success, imports the generated JSON into `job_details`
- creates a `job_search_runs` row for the collection result
- records a `search_run` task artifact with `related_table='job_search_runs'` and `related_id=<search_run_id>`
- marks `collect_jobs` as `completed`
- records `incomplete=true` in stage output when actual imported count is below target
- on failure, marks `collect_jobs` as `failed` and writes the error message into task events

Current limitation:

- `GET /api/tasks/{task_id}/jobs` for live tasks still returns an empty list until the scoring endpoint is connected.
- The runner is connected, but it only runs when this action endpoint is explicitly called.

## 2026-08-01 Scoring Action Update

`POST /api/tasks/{task_id}/actions/start-scoring` is now implemented.

Behavior:

- live tasks only
- requires `collect_jobs` to be completed by Harness order
- requires a `search_run` artifact that points to `job_search_runs`
- runs local scoring synchronously through the existing `jobuwant.job_match_score.score_jobs`
- reuses the collection `job_search_runs.id` instead of creating a separate scoring run
- writes `job_search_run_items` and `job_terms`
- records a `scored_jobs` task artifact with `related_table='job_search_runs'`
- marks `score_jobs` as `completed` on success
- returns HTTP 409 without mutating task state if collection has not completed

Live `GET /api/tasks/{task_id}/jobs` now reads rows from the task `search_run_id` after scoring completes. It supports the same filters as fixture tasks.

Job type scoring mapping:

- `intern`: expected intent `intern`, internship signals allowed
- `any`: expected intent `any`, internship signals allowed
- `full_time`: expected intent `engineering`, internship signals not relaxed

## 2026-08-01 Sample Confirmation Update

`POST /api/tasks/{task_id}/sample` is now implemented.

Request body:

- `selected_job_ids`: selected `job_details.id` values from the task scoring run.
- `excluded_job_ids`: optional excluded ids; the backend stores the full excluded set as all scored jobs not selected.
- `selection_note`: optional note.

Behavior:

- live tasks only
- requires `score_jobs` to be completed by Harness order
- requires a `scored_jobs` artifact that points to `job_search_runs`
- validates every submitted job id belongs to the task search run
- rejects empty selected samples
- writes `analysis_samples`
- writes `analysis_sample_items` for every scored job in the run
- records a `sample` task artifact with `related_table='analysis_samples'`
- marks `confirm_sample` as `completed`

Live `GET /api/tasks/{task_id}/jobs` now reflects the latest saved sample selection when one exists.

## 2026-08-01 Structuring Batch Plan Update

The first AI structuring API skeleton is now implemented without model execution.

Implemented endpoints:

- `POST /api/tasks/{task_id}/actions/start-structuring`
- `GET /api/tasks/{task_id}/structure`

`POST /api/tasks/{task_id}/actions/start-structuring` behavior:

- live tasks only
- requires `confirm_sample` to be completed by Harness order
- reads the latest confirmed sample
- creates `batch_runs` rows with status `pending`
- records a `batch_runs` task artifact
- marks `ai_structuring` as `waiting_for_user`
- does not call any model

`GET /api/tasks/{task_id}/structure` returns:

- task id
- sample id
- sample version
- selected count
- batch size
- total batch count
- batch rows with job ids, status, model name, token fields, timing, and error fields

Current limitation:

- Actual batch execution is intentionally deferred until the user explicitly approves model calls.

## 2026-08-01 Structuring Batch Execution Update

`POST /api/tasks/{task_id}/actions/run-structuring-batches` is now implemented as the explicit model-execution action.

Behavior:

- live tasks only
- requires `ai_structuring` to be in `waiting_for_user`
- requires pending `batch_runs`
- marks `ai_structuring` back to `running`
- submits a one-worker local background runner
- returns immediately; clients should poll `GET /api/tasks/{task_id}/structure` and task events

Runner behavior:

- loads the latest confirmed sample
- processes pending batches sequentially
- marks each batch `running`, then `completed` or `failed`
- writes model name, input tokens, output tokens, estimated CNY, timing, and error fields into `batch_runs`
- saves extraction rows through the existing `jobuwant.ai_job_extract` functions
- stores usage through the existing usage event helper
- marks `ai_structuring` completed and records an `extractions` artifact when all pending batches complete
- marks `ai_structuring` failed when a batch fails

Important boundary:

- `POST /api/tasks/{task_id}/actions/start-structuring` only creates pending batch plans and does not call a model.
- `POST /api/tasks/{task_id}/actions/run-structuring-batches` is the action that performs model work when explicitly called.
- Backend tests replace the real batch execution function and do not call a model.

## 2026-08-02 Report Input Generation Update

`POST /api/tasks/{task_id}/actions/build-report-input` is now implemented.

Behavior:

- live tasks only
- requires `ai_structuring` to be completed by Harness order
- requires the latest confirmed sample
- requires an `extractions` artifact for that sample
- builds compact report input through the existing `jobuwant.job_report.build_report_input`
- stores the payload through `jobuwant.job_report.store_report_input`
- writes a JSON copy at `data/task_artifacts/{task_id}/report_input.json`
- records a `report_input` artifact with `related_table='job_report_inputs'`
- marks `build_report_input` as `completed` on success and `failed` on runtime error

Live `GET /api/tasks/{task_id}/report-input` now reads the generated artifact. It first reads `job_report_inputs.input_json` through the artifact relation, then falls back to the stored JSON path.

All six Harness write endpoints are now implemented. Frontend wiring and visual polish remain separate work.
## 2026-08-02 Final Report Generation Update

`POST /api/tasks/{task_id}/actions/write-final-report` is now implemented.

Behavior:

- live tasks only
- requires `build_report_input` to be completed by Harness order
- requires a `report_input` artifact that points to `job_report_inputs`
- marks `write_final_report` as `running`
- submits a one-worker local background runner and returns immediately
- runner calls the existing `jobuwant.ai_report_writer` functions
- stores the report in `job_reports` and `data/task_artifacts/{task_id}/final_report.json`
- records a `report` artifact with `related_table='job_reports'`
- marks `write_final_report` as `completed` on success or `failed` on runtime error

Live `GET /api/tasks/{task_id}/report` now reads the generated report artifact. It first reads `job_reports.output_json` through the artifact relation, then falls back to the stored JSON path.

Testing note:

- Backend tests use a fake report writer and do not perform model work.