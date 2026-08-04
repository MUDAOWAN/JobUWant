# Web App Workflow

Status: active workflow record created on 2026-07-28.

## Purpose

This document records how the formal Web App work should proceed under the webapp directory.

It is the local operating checklist for the Web App phase. Higher-level product and architecture decisions remain in the root docs directory.

## Current Baseline

- Backend: FastAPI plus Pydantic.
- Frontend: Next.js plus TypeScript.
- Database: SQLite first.
- First implementation mode: fixture-first.
- Existing Python analysis chain remains under the root jobuwant package.

## Working Principles

- Keep all formal Web App code under webapp.
- Keep Streamlit as a pilot and debug surface until the Web App covers the validated flow.
- Do not rewrite the validated Python analysis modules before they are wrapped by stable services.
- Start from API contracts and task state before full UI behavior.
- Use existing Hangzhou and Guangzhou fixtures before live long-running execution.
- Install skills only when a concrete phase needs them.
- Record each phase result in this document or linked docs.

## Phase Order

### Phase 1: Project Boundary

Status: completed.

Completed outputs:

- webapp directory created.
- backend, frontend, and docs subdirectories created.
- webapp README created.
- project boundary document created.

### Phase 2: Backend Contracts And Fixture APIs

Status: completed.

Completed outputs:

- API contracts documented in webapp/docs/API_CONTRACTS.md.
- Data model documented in webapp/docs/DATA_MODEL.md.
- FastAPI-oriented backend skeleton created.
- Fixture registry created for search_run_id 7 and search_run_id 8.
- Read-only APIs created for task list, task detail, jobs, report input, report, and events.
- Backend tests passed after dependency installation.
- Local backend verified at http://localhost:8000.

### Phase 3: Frontend Skeleton

Status: completed for environment, skeleton verification, and local frontend startup; browser interaction verification remains in the next phase.

Goal:

- Create a minimal Next.js frontend under webapp/frontend.
- Connect it to the fixture-first backend.
- Show a basic task list and backend health state.

Acceptance:

- npm dependencies install successfully: completed.
- TypeScript typecheck succeeds: completed.
- Next.js build succeeds: completed with project-local Linux Node.js.
- Local frontend starts: completed at http://127.0.0.1:3000.
- The first page can read GET /api/tasks from the FastAPI backend: implemented in code, pending browser verification.

### Phase 4: Task Workspace Pages

Status: completed for fixture-first primary pages. Task list, task detail, sample confirmation, report input preview, and final report view are implemented; AI structure remains a reserved placeholder.

Planned pages:

- task list
- task detail
- job sample table
- report input preview
- final report view

Completed in this phase so far:

- / redirects to /tasks.
- /tasks route exists.
- /tasks/[taskId] route exists.
- /tasks/[taskId]/sample route exists.
- /tasks/[taskId]/structure route exists.
- /tasks/[taskId]/report-input route exists.
- /tasks/[taskId]/report route exists.
- Shared Chinese task workspace navigation exists.
- /tasks now uses a dedicated Chinese task list page.
- Task list supports backend health display, task summary metrics, keyword filtering, report status, and links to task detail.
- /tasks/[taskId] now shows task summary, stage progress, next actions, artifact entries, event records, task metadata, and match distribution.
- Task detail reads GET /api/tasks/{task_id} and GET /api/tasks/{task_id}/events.
- /tasks/[taskId]/sample now shows a read-only fixture-backed job table with filters, selected-only mode, local selection preview, and row details.
- Sample confirmation reads GET /api/tasks/{task_id}/jobs and does not write sample changes yet.
- /tasks/[taskId]/report-input now shows query boundary, sample metrics, evidence quality, salary summary, technical term charts, role distribution, and raw JSON preview.
- Report input preview reads GET /api/tasks/{task_id}/report-input and remains read-only.
- /tasks/[taskId]/report now shows the final report as an article-style reading page with summary metrics, charts, skill layers, learning route, project suggestions, resume keywords, advice, caveats, and evidence references.
- Final report view reads GET /api/tasks/{task_id}/report and remains read-only.

Working method:

- Use webapp/docs/UI_DESIGN_DIRECTION.md as the page design brief.
- Implement pages in small steps.
- Keep UI state derived from FastAPI task, stage, event, job, report-input, and report APIs.
- Run typecheck and build after each meaningful page milestone.

### Phase 4.5: Harness Baseline

Status: completed.

Completed outputs:

- Added lightweight in-repo Harness service in `webapp/backend/app/services/task_harness.py`.
- Added Harness tests in `webapp/backend/tests/test_task_harness.py`.
- Defined task statuses, stage statuses, action names, stage order, artifact types, next-stage calculation, and action availability checks.
- Added Harness design document in `webapp/docs/WEB_APP_HARNESS.md`.
- Added implementation and technical stack record in `webapp/docs/IMPLEMENTATION_RECORD.md`.

Verification:

- Backend tests passed: 9 passed.
### Phase 5: UI Design Skill Pass

Status: pending. Skill usage is staged and must be tied to a concrete UI milestone.

Use a design skill before polishing the main pages.

Candidate skills:

- ui-ux-pro-max
- frontend-design

Implementation and review skills:

- vercel-react-best-practices
- web-design-guidelines
- frontend-design-review
- webapp-testing

Reference catalog:

- ComposioHQ/awesome-claude-skills

Expected output:

- page layout direction
- component hierarchy
- visual style rules
- report reading layout

Current rule:

- Do not install all skills upfront.
- Use ui-ux-pro-max or frontend-design before visual polish.
- Use vercel-react-best-practices after route and component boundaries are stable.
- Use web-design-guidelines or frontend-design-review after visible page implementation.
- Use webapp-testing after frontend and backend are running for browser verification.

### Phase 6: Frontend Review And Browser Verification

Status: pending.

Candidate skills:

- vercel-react-best-practices
- web-design-guidelines
- frontend-design-review
- webapp-testing

Expected output:

- frontend code review
- browser screenshots
- API integration verification
- build and navigation checks

### Phase 7.1: Live Task Creation

Status: completed for backend API.

Completed outputs:

- Added `AnalysisTaskCreate` request schema.
- Added `webapp/backend/app/repositories/analysis_tasks.py` for live task persistence.
- Added `webapp/backend/app/services/task_service.py` as the unified task service over live tasks and fixture tasks.
- Added `POST /api/tasks`.
- Live task creation initializes all six Harness stages as pending and appends a `task_created` event.
- Existing fixture-first read pages remain compatible.

Verification:

- Backend tests passed: 12 passed.
- Backend health endpoint returned 200.
- OpenAPI shows `/api/tasks` supports `get` and `post`.
### Phase 7.2: Collection Action Boundary

Status: completed for Harness state transition.

Completed outputs:

- Added `POST /api/tasks/{task_id}/actions/start-collection`.
- Added repository helpers for stage running, completed, failed, and artifact records.
- Starting collection marks the live task as `running` and `collect_jobs` as `running`.
- Starting collection appends a `collect_jobs_started` event.
- Duplicate start requests are rejected with HTTP 409.
- The actual Python collection runner is not connected yet.

Verification:

- Backend tests passed: 14 passed.
### Phase 7: Live Task Execution

Status: pending.

Only start after the fixture-first frontend flow works.

Planned additions:

- live task creation
- sample confirmation writes
- staged runner for existing Python modules
- progress polling
- failed batch retry

## Current Local URLs

- Backend: http://localhost:8000
- Backend API docs: http://localhost:8000/docs
- Frontend: http://127.0.0.1:3000

## Update Rule

When a phase completes, update:

- this workflow document
- webapp README if commands change
- root docs/WORKLOG.md
- API or data model docs when contracts change



### Phase 7.3: Collection Runner Integration

Status: completed for backend runner boundary.

Completed outputs:

- Added `webapp/backend/app/runner/collection_runner.py`.
- `start_collection` now submits a local background runner instead of only marking state.
- Runner derives collection parameters from `analysis_tasks`.
- Runner writes progress events from list-page and detail processing output.
- Runner imports generated JSON through the existing BOSS adapter.
- Runner creates a `job_search_runs` row and records it as a `search_run` task artifact.
- Live task detail can expose `search_run_id` and `collected_count` after collection completion.
- Tests use fake runner functions and do not perform real collection.

Verification:

- Backend tests passed: 16 passed.

Next planned backend step:

- Connect `start-scoring` so live tasks can turn the collection `search_run` into scored `job_search_run_items` and a selectable sample table.

### Phase 7.4: Local Scoring Action

Status: completed for backend API.

Completed outputs:

- Added `POST /api/tasks/{task_id}/actions/start-scoring`.
- Added `webapp/backend/app/services/scoring_service.py`.
- Reused existing local scoring logic from `jobuwant.job_match_score`.
- Extended scoring to reuse the collection `job_search_runs.id` through `existing_run_id`.
- Recorded a `scored_jobs` task artifact.
- Live task detail now returns match and role-intent distributions after scoring.
- Live task jobs endpoint now returns scored job rows after scoring.
- Scoring before completed collection returns 409 and leaves state unchanged.

Verification:

- Backend tests passed: 18 passed.

Next planned backend step:

- Implement sample confirmation writes through `POST /api/tasks/{task_id}/sample`.

### Phase 7.5: Sample Confirmation Writes

Status: completed for backend API.

Completed outputs:

- Added `POST /api/tasks/{task_id}/sample`.
- Added `SampleConfirmRequest` request schema.
- Added `webapp/backend/app/services/sample_service.py`.
- Added sample persistence helpers in `analysis_tasks` repository.
- Confirmed samples now write `analysis_samples` and `analysis_sample_items`.
- Confirmed sample action records a `sample` task artifact.
- Live job rows now reflect the latest sample selection.
- Invalid sample ids are rejected before task state changes.

Verification:

- Backend tests passed: 20 passed.

Next planned backend step:

- Implement AI structuring batch execution. This next step requires explicit user approval before any real model call is made.

### Phase 7.6: Structuring Batch Plan

Status: completed for backend planning API.

Completed outputs:

- Added `POST /api/tasks/{task_id}/actions/start-structuring`.
- Added `GET /api/tasks/{task_id}/structure`.
- Added structuring status response schemas.
- Added `webapp/backend/app/services/structuring_service.py`.
- Added repository helpers for latest sample lookup and batch run creation/listing.
- Structuring start now creates pending `batch_runs` and records a `batch_runs` artifact.
- The `ai_structuring` stage is marked `waiting_for_user` after the plan is created.
- No model calls are made in this phase.

Verification:

- Backend tests passed: 24 passed.

Next planned backend step:

- Add actual structuring batch execution after explicit user approval for model calls.

### Phase 7.7: Structuring Batch Runner

Status: completed for backend execution boundary.

Completed outputs:

- Added `POST /api/tasks/{task_id}/actions/run-structuring-batches`.
- Added `webapp/backend/app/runner/structuring_runner.py`.
- Added repository helpers for waiting-stage resume and batch status updates.
- Structuring runner processes pending batches sequentially.
- Batch runs persist running/completed/failed state, model, token, cost, timing, and error fields.
- Successful completion records an `extractions` artifact and marks `ai_structuring` completed.
- Failed batch execution marks the batch and stage failed.
- Tests use fake batch execution and do not call a model.

Verification:

- Backend tests passed: 28 passed.

Next planned backend step:

- Implement report-input generation after real structuring output exists.

### Phase 7.8: Report Input Generation

Status: completed for backend API.

Completed outputs:

- Added `POST /api/tasks/{task_id}/actions/build-report-input`.
- Added `webapp/backend/app/services/report_input_service.py`.
- Reused existing `jobuwant.job_report` report-input builder and storage helper.
- Validates latest confirmed sample and matching `extractions` artifact before stage mutation.
- Stores report input in `job_report_inputs` and `data/task_artifacts/{task_id}/report_input.json`.
- Records a `report_input` task artifact.
- Live `GET /api/tasks/{task_id}/report-input` now reads generated live artifacts.
- Tests cover successful generation and rejection before structuring completion.

Verification:

- Backend tests passed: 30 passed.

Next planned backend step:

- Implement final report generation. This should require explicit approval before any real model work is run.
### Phase 7.9: Final Report Generation

Status: completed for backend API and runner boundary.

Completed outputs:

- Added `POST /api/tasks/{task_id}/actions/write-final-report`.
- Added `webapp/backend/app/services/final_report_service.py`.
- Added `webapp/backend/app/runner/final_report_runner.py`.
- Reused existing `jobuwant.ai_report_writer` settings, report writing, storage, and usage helpers.
- Stores final report in `job_reports` and `data/task_artifacts/{task_id}/final_report.json`.
- Records a `report` task artifact.
- Live `GET /api/tasks/{task_id}/report` now reads generated live artifacts.
- Tests cover fake successful final report generation and rejection before report input generation.

Verification:

- Backend tests passed: 32 passed.

Next planned step:

- Move to frontend live workflow wiring and browser verification before UI polish.
### Phase 8.1: Frontend Live Workflow Wiring

Status: completed for first browser-facing control flow.

Completed outputs:

- Added live task creation form on `/tasks`.
- Added stage-aware next action panel on `/tasks/{taskId}`.
- Added polling while a live task stage is running.
- Connected sample saving on `/tasks/{taskId}/sample`.
- Replaced the structure placeholder with a batch status table and action buttons.
- Kept fixture tasks read-only.

Verification:

- `npm run lint` passed.
- `npm run typecheck` passed.
- `npm run build` passed.
- Backend tests passed: 32 passed.
- Local preview available at `http://127.0.0.1:3001/tasks` for the latest build in this session.

Next planned step:

- Browser-test the live workflow with a deliberately small user-approved task. Do not start new collection or model-backed stages without explicit confirmation.