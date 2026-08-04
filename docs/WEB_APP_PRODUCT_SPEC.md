# Web App Product Spec

Purpose: define the first real web-application version after the Streamlit
pilot validated the end-to-end job-analysis chain.

Status: drafted on 2026-07-27 after the Hangzhou Agent intern 40-job run and
the Guangzhou GIS 30-job run both completed.

## Product Direction

JobUWant should evolve from a local Streamlit pilot into a structured web
application for creating, monitoring, reviewing, and reading job-market
analysis tasks.

The product should be designed with a future public website in mind, while the
first implementation can still run locally and avoid login, payment, multi-user
permissions, and production deployment complexity.

The desired first-version style is a balanced experience:

- clear task execution and progress visibility for the analysis workflow
- polished report reading with charts, summaries, and evidence traceability
- enough operational detail to diagnose long-running model and collection steps

## First Web MVP Scope

The first web MVP should support one complete analysis task flow:

1. create an analysis task
2. collect job postings
3. score and confirm the sample
4. run AI structuring in visible batches
5. generate and preview report input
6. generate and view the final report

Historical cross-task comparison is intentionally out of scope for this first
web version. The system should still store task history so comparison can be
added later.

## Confirmed Task Inputs

The task creation form should support:

- task name
- city
- job keyword
- job-seeking type: intern, full_time, or any
- expected job count
- AI structuring batch size, default 10
- notes, optional

The UI should present these labels in Chinese:

- 城市
- 岗位关键词
- 求职类型：实习 / 全职 / 不限
- 预期搜索岗位数
- AI 结构化批大小
- 备注

The backend should preserve normalized internal values, for example:

- intern
- full_time
- any

## Workflow Overview

### 1. Create Analysis Task

The first page should let the user create a new task and understand the likely
runtime before starting.

Recommended display:

- task input form
- estimated runtime range based on expected job count
- expected number of model calls based on batch size
- estimated token/cost placeholder based on previous runs
- submit button: 创建任务

The system should create a persistent task record before any long-running work
starts.

### 2. Collect Jobs

The collection page should make long-running progress visible.

Show:

- current task status
- start time
- end time
- elapsed time
- target job count
- list jobs collected
- detail jobs attempted
- detail jobs succeeded
- detail jobs failed
- latest stage message
- live log panel

If the collector stops before reaching the expected job count, the UI should
show a clear interrupted/incomplete state and offer:

- 继续尝试
- 用当前结果继续
- 重新运行

The first web version may still call the existing slow collection script behind
an API boundary. It should not block the browser page without status updates.

### 3. Score And Confirm Sample

Local scoring must run before the user confirms the analysis sample.

This page combines scoring results and sample review.

Show summary cards:

- total collected jobs
- strong match count
- review count
- weak match count
- role-intent distribution
- average score
- low-quality or short-description count

Show a job table with default all selected.

Table columns should include:

- selected checkbox
- match status
- match score
- role intent
- company
- job title
- city
- salary
- experience
- education
- description length
- review reasons

Filters should include:

- match status
- role intent
- city
- salary availability
- company keyword
- title keyword
- selected only

Each row should allow expanding the original job text and source metadata.

The user can deselect jobs that are clearly unrelated. The confirmed sample is
then saved as the analysis sample for the next stages.

For traceability, the system should store:

- collected job ids
- selected job ids
- excluded job ids
- exclusion timestamp
- optional exclusion reason in a later version

If the user later changes the selection and regenerates outputs, the backend
should create a new analysis run or sample record rather than overwriting the
previous sample silently.

### 4. AI Structuring

This is the most important progress experience. The user must know that the
system is running and where time/tokens are being spent.

Show:

- total selected jobs
- batch size
- total batch count
- current batch
- overall progress bar
- per-batch status: pending, running, completed, failed
- per-batch job ids and titles
- input tokens
- output tokens
- elapsed time
- model name
- error message if failed
- retry button for failed batch

The current script already supports stable 10-job batches. The first web MVP
should use batch size 10 as the default and allow the user to adjust it at task
creation.

The structuring output should remain validated by schema before being saved.
Failed validation should be displayed as a batch failure with a retry option.

### 5. Report Input Preview

After AI structuring completes, the system generates a compact report input.
This page should help the user decide whether the sample is good enough before
asking the model to write the final report.

Show:

- selected sample count
- match status distribution
- role-intent distribution
- technical terms Top 15
- skill layers
- salary summary
- experience summary
- education summary
- intern/new-graduate friendliness distribution
- evidence quality
- report input JSON viewer

The page should include a primary action:

- 生成最终报告

The user should still be able to return to sample confirmation and adjust the
selected jobs before generating the final report.

### 6. Final Report View

The report page should combine market statistics and job-search action advice.
It should not be a plain long-text JSON viewer.

Recommended layout:

- top overview: city, keyword, job-seeking type, sample count, model, time,
  token usage, evidence quality
- market profile: role portrait, role clusters, role-intent distribution
- technical stack: Top 15 chart, skill layers, tools/platforms
- salary: monthly/daily ranges, median midpoint, parsed/unparsed counts
- requirements: experience and education summary
- friendliness: intern/new-graduate friendliness distribution and explanation
- action plan: learning route, project suggestions, resume keywords, job-search
  advice
- caveats: sample limits and evidence quality notes
- evidence traceability: clicking an evidence reference shows the source job and
  original quote

The first version should support JSON export. Markdown or HTML export can be
added after the report UI stabilizes.

## Data Objects

The web app should introduce explicit task-level records instead of relying only
on low-level job and report tables.

Suggested objects:

### AnalysisTask

- id
- task_name
- city
- city_code
- keyword
- job_type
- expected_job_count
- batch_size
- notes
- status
- created_at
- updated_at
- started_at
- finished_at

### TaskStageRun

- id
- task_id
- stage_name
- status
- started_at
- finished_at
- elapsed_seconds
- input_json
- output_json
- error_message

Stage names:

- collect_jobs
- score_jobs
- confirm_sample
- ai_structuring
- build_report_input
- write_final_report

### AnalysisSample

- id
- task_id
- search_run_id
- selected_job_ids_json
- excluded_job_ids_json
- created_at
- updated_at

### BatchRun

- id
- task_id
- sample_id
- batch_index
- batch_size
- job_ids_json
- status
- model_name
- input_tokens
- output_tokens
- estimated_cny
- started_at
- finished_at
- elapsed_seconds
- error_message

Existing tables such as job_details, job_search_runs, job_search_run_items,
job_extractions, job_report_inputs, job_reports, and usage_events should
remain the source of detailed records during the migration.

## API Draft

The first formal web app should expose API endpoints rather than letting the UI
call Python modules directly.

Suggested endpoints:

- POST /api/tasks
- GET /api/tasks
- GET /api/tasks/{task_id}
- POST /api/tasks/{task_id}/collect
- POST /api/tasks/{task_id}/score
- GET /api/tasks/{task_id}/jobs
- POST /api/tasks/{task_id}/sample
- POST /api/tasks/{task_id}/structure
- POST /api/tasks/{task_id}/structure/batches/{batch_id}/retry
- POST /api/tasks/{task_id}/report-input
- POST /api/tasks/{task_id}/report
- GET /api/tasks/{task_id}/report
- GET /api/tasks/{task_id}/logs

The first implementation can run tasks sequentially in the local backend. The
API should still be shaped so a background worker can be introduced later.

## Status Model

Task status values:

- draft
- collecting
- collection_incomplete
- collected
- scoring
- sample_review
- structuring
- structured
- report_input_ready
- report_generating
- completed
- failed

Stage status values:

- pending
- running
- completed
- failed
- skipped

The UI should always show the current stage and the next available action.

## Error Handling

Collection shortfall:

- show target count and actual count
- show stopping reason
- allow continue, proceed with current result, or rerun

AI batch failure:

- show failed batch index
- show model name
- show elapsed time before failure
- show error message
- allow retry only for that batch

Report generation failure:

- preserve report input
- show error message
- allow retry final report without rerunning structuring

Validation failure:

- show which schema failed
- keep raw model output if available for local debugging
- do not mark the stage completed

## Frontend Direction

The first web version should not use Streamlit as the final UI. Streamlit can
remain available as a pilot/debug surface until the new web app replaces it.

Preferred direction to evaluate next:

- backend: FastAPI wrapping existing Python modules
- frontend: React with Vite or Next.js
- database: SQLite for local first version, designed so PostgreSQL can be added
  later
- execution: local sequential task runner first, background worker later

The final choice should be made after frontend references, available skills,
and implementation constraints are reviewed.

## First Version Non-Goals

Do not build these in the first web MVP:

- login and account system
- payment
- multi-user permissions
- public deployment
- historical task comparison UI
- resume upload and personal fit scoring
- automatic scheduled refresh
- complex workflow engine
- cloud database migration

The code and data model should avoid blocking these future additions.

## Validation Plan

Use the two completed runs as regression fixtures:

- Hangzhou + Agent engineer + intern, 40 jobs
- Guangzhou + GIS + any job type, 30 jobs

The first web version is acceptable when it can:

- create a new task with the confirmed inputs
- display collection progress and results
- show scoring distribution and selectable job rows
- run AI structuring in visible batches
- generate report input from selected jobs
- generate a final report
- display report sections, charts, and evidence references
- preserve enough timing/token information to reproduce the run summary
