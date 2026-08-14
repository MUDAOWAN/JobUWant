# Web App Data Model

Status: task-level schema and live artifact mapping through final report are current as of 2026-08-02.

## Existing Tables Kept As Detail Sources

- job_details
- job_search_runs
- job_search_run_items
- job_extractions
- job_terms
- job_report_inputs
- job_reports
- usage_events

The Web App must wrap these tables instead of replacing the validated analysis chain.

## New Task-Level Tables

The SQL lives in webapp/backend/app/repositories/database.py.

analysis_tasks:

- Purpose: one user-facing analysis task.
- Key fields: task_name, city, city_code, keyword, job_type, expected_job_count, batch_size, source_type, status, notes, timestamps.

 task_stage_runs:

- Purpose: one run of a workflow stage.
- Key fields: task_id, stage_name, status, started_at, finished_at, elapsed_seconds, input_json, output_json, error_code, error_message.

 task_events:

- Purpose: append-only progress and diagnosis events.
- Key fields: task_id, stage_run_id, level, event_type, message, payload_json, created_at.

analysis_samples:

- Purpose: confirmed job sample for downstream AI structuring and report generation.
- Key fields: task_id, search_run_id, sample_version, selected_count, excluded_count, selected_job_ids_json, excluded_job_ids_json, selection_note.

analysis_sample_items:

- Purpose: row-level sample membership and selection state.
- Key fields: sample_id, job_detail_id, selected, match_score, match_status, role_intent.

batch_runs:

- Purpose: AI structuring batch status and model usage.
- Key fields: task_id, sample_id, stage_run_id, batch_index, batch_size, job_ids_json, status, model_name, input_tokens, output_tokens, estimated_cny, timestamps, error fields.

task_artifacts:

- Purpose: connect task state to files or low-level table records.
- Key fields: task_id, artifact_type, path, related_table, related_id, summary_json.

## First Persistence Rule

Fixture-first endpoints read existing artifacts and do not create task rows yet. The schema is ready for live task creation, but live writes should start after API contracts are reviewed.

## Harness Mapping

The Harness baseline is implemented in `webapp/backend/app/services/task_harness.py`.

Table mapping:

- `analysis_tasks` stores the user-facing task and task status.
- `task_stage_runs` stores one row per Harness stage and records status, input, output, timing, and error fields.
- `task_events` stores user-visible progress and technical diagnosis messages.
- `task_artifacts` stores outputs produced by stages, such as `search_run`, `sample`, `report_input`, and `report`.
- `analysis_samples` and `analysis_sample_items` store the sample confirmation result.
- `batch_runs` stores AI structuring batches, token usage, cost estimate, timing, and error fields.

Live task creation now initializes `analysis_tasks`, all `task_stage_runs`, and a `task_events` row in one transaction through `webapp/backend/app/repositories/analysis_tasks.py`.
## Stage Action Persistence

Stage action helpers now update `task_stage_runs`, `analysis_tasks`, `task_events`, and `task_artifacts` through `webapp/backend/app/repositories/analysis_tasks.py`.

Implemented helpers:

- start an action and mark its stage as `running`
- mark a stage as `completed`
- mark a stage as `failed`
- record a task artifact
- derive task status from current stage statuses

These helpers are the persistence boundary for later collection, scoring, AI structuring, and report generation runners.
## 2026-07-31 Collection Artifact Mapping

The collection runner now uses `task_artifacts` to connect a live task to the low-level collection run.

For `artifact_type='search_run'`:

- `path` stores the generated collection JSON path, such as `data/task_artifacts/task-1/collection.json`.
- `related_table` stores `job_search_runs`.
- `related_id` stores the created `job_search_runs.id`.
- `summary_json` stores target count, imported count, stop reason, incomplete marker, and import summary.

Live task summary fields now read collection metrics from the latest `search_run` artifact when present:

- `search_run_id`
- `collected_count`
- `analysis_ready_count`

## 2026-08-01 Scoring Artifact Mapping

The scoring action reuses the collection `job_search_runs.id` so one live task keeps a stable `search_run_id` across collection and local scoring.

For `artifact_type='scored_jobs'`:

- `related_table` stores `job_search_runs`.
- `related_id` stores the same run id used by the `search_run` artifact.
- `summary_json` stores evaluated count, match-status distribution, role-intent distribution, average score, query terms, and top matches.

After scoring, live task detail can expose:

- `match_status_counts`
- `role_intent_counts`
- `analysis_ready_count`

Live job list reads `job_search_run_items` joined with `job_details`, matching the fixture-backed table shape.

## 2026-08-01 Sample Persistence Mapping

Sample confirmation now writes the task-level sample tables.

`analysis_samples` stores:

- task id
- search run id
- sample version
- selected count
- excluded count
- selected job ids JSON
- excluded job ids JSON
- optional selection note

`analysis_sample_items` stores one row for every scored job in the confirmed run:

- sample id
- job detail id
- selected flag
- match score
- match status
- role intent

For `artifact_type='sample'`:

- `related_table` stores `analysis_samples`.
- `related_id` stores the created sample id.
- `summary_json` stores sample id, version, selected count, excluded count, and job id lists.

## 2026-08-01 Structuring Batch Plan Mapping

AI structuring planning now writes `batch_runs` without model execution.

Each planned `batch_runs` row stores:

- task id
- sample id
- stage run id
- batch index
- batch size
- selected job ids JSON
- status `pending`
- empty model and token fields

For `artifact_type='batch_runs'`:

- `related_table` stores `analysis_samples`.
- `related_id` stores the sample id.
- `summary_json` stores selected count, batch size, total batches, and `model_call_started=false`.

## 2026-08-01 Structuring Batch Execution Mapping

Structuring execution now updates existing `batch_runs` rows instead of creating a separate execution table.

Batch status flow:

- `pending`
- `running`
- `completed` or `failed`

Execution writes these fields on completion:

- `model_name`
- `input_tokens`
- `output_tokens`
- `estimated_cny`
- `started_at`
- `finished_at`
- `elapsed_seconds`
- `error_code`
- `error_message`

For `artifact_type='extractions'`:

- `related_table` stores `analysis_samples`.
- `related_id` stores the sample id.
- `summary_json` stores completed batch count, failed batch count, and batch status counts.

## 2026-08-02 Report Input Artifact Mapping

Report input generation now writes both the existing low-level report input table and a task artifact.

For `artifact_type='report_input'`:

- `path` stores `data/task_artifacts/{task_id}/report_input.json`.
- `related_table` stores `job_report_inputs`.
- `related_id` stores the created `job_report_inputs.id`.
- `summary_json` stores report input id, sample id, search run id, output path, total jobs, estimated prompt tokens, token budget, and evidence quality.

Live report input preview reads the artifact relation first and falls back to the JSON file path when needed.
## 2026-08-02 Final Report Artifact Mapping

Final report generation now writes the existing `job_reports` table and a task artifact.

For `artifact_type='report'`:

- `path` stores `data/task_artifacts/{task_id}/final_report.json`.
- `related_table` stores `job_reports`.
- `related_id` stores the created `job_reports.id`.
- `summary_json` stores report id, report input id, search run id, output path, title, model name, and usage fields.

Live final report preview reads the artifact relation first and falls back to the JSON file path when needed.
## 2026-08-05 Supported City Catalog

The Web App now has a supported city catalog in `webapp/backend/app/core/city_catalog.py`.

Rules:

- The `/tasks` creation form shows city names only.
- The backend resolves the selected city to the internal `analysis_tasks.city_code` value.
- `analysis_tasks.city_code` is still persisted because the collection runner needs it.
- Unknown city names are rejected before task creation.
- Mismatched city and city_code pairs are rejected.
- The first catalog covers first-tier, new-first-tier, and common second-tier cities.
- Hangzhou, Guangzhou, and Shenzhen are marked as locally verified because prior local runs used those city codes successfully.

## 2026-08-06 Cancellation State Mapping

Task cancellation now has explicit task and stage state.

Rules:

- `analysis_tasks.status` can be `canceled` for a user-stopped live task.
- The active `task_stage_runs` row is marked `canceled`.
- Downstream `pending` stage rows are marked `skipped`.
- A `task_canceled` event records the visible reason and runner cancellation flag.
- For collection cancellation, the runner removes the generated collection output file and does not record a `search_run` artifact.