# JobUWant Web App Implementation Record

Status: active record created on 2026-07-31.

## Purpose

This document records the Web App implementation process, technical stack, and engineering decisions in a form that can later be reused for project summaries and resume material.

## Current Technical Stack

- Backend: FastAPI
- Backend data validation: Pydantic
- Backend runtime language: Python
- Database: SQLite first
- Frontend: Next.js
- Frontend language: TypeScript
- UI styling: Tailwind-style utility classes
- Icons: lucide-react
- Charts: Recharts
- Local preview mode: Next.js production server with project-local Linux Node.js
- Execution management: lightweight in-repo Harness

## Current Product Scope

The first Web App version focuses on the job collection to analysis chain:

1. Create an analysis task.
2. Collect jobs.
3. Run local scoring.
4. Confirm the job sample.
5. Run AI structuring by batch.
6. Build report input.
7. Generate final report.
8. Display report pages in the browser.

Out of scope for the current phase:

- user login
- payment
- multi-user permissions
- public deployment
- historical task comparison

## Completed Web App Milestones

- Created `webapp/` as the formal Web App folder.
- Built fixture-first FastAPI read endpoints.
- Built fixture-first Next.js task list, task detail, sample confirmation preview, report input preview, and final report view pages.
- Added a lightweight Harness baseline to define task stages, statuses, actions, and stage ordering.

## Harness Baseline

The Harness is implemented as a small Python service module instead of an external workflow framework.

Current benefits:

- one source of truth for the stage order
- consistent action names for future API endpoints
- predictable task status derivation
- explicit user confirmation point for sample selection
- clear artifact expectations for every stage
- easier frontend button-state and page-state rules

## Resume-Friendly Project Description Draft

JobUWant is a local-first job market analysis Web App. The system wraps an existing Python analysis pipeline with a FastAPI service layer and a Next.js TypeScript frontend. It uses SQLite for task, stage, event, sample, batch, and artifact records. A lightweight in-repo Harness controls the long-running analysis lifecycle from job collection, local scoring, sample confirmation, AI structuring, report input generation, and final report rendering. The frontend provides task workbench pages and report reading pages backed by typed API contracts.

## Next Implementation Focus

Next step: connect the collection runner behind the existing `start-collection` action and record the resulting `search_run` artifact.

Expected outputs:

- action endpoint for starting collection
- stage status updates for collection running/completed/failed
- `search_run` artifact recording
- frontend create-task entry and collection trigger after backend action contract is stable

## 2026-07-31 Task Creation API

Implemented the first live write boundary for the Web App:

- Added `POST /api/tasks`.
- Added SQLite repository functions for task creation, task listing, task detail, stage listing, event listing, and artifact path listing.
- Initialized six Harness stages for each new task.
- Wrote a `task_created` event for each new task.
- Kept existing fixture tasks available in the same task list.

Engineering value:

- The Web App now has a real task lifecycle entry point.
- Later collection, scoring, sample saving, AI structuring, and report generation can attach to the same task id and stage rows.
- Tests verify task creation through both repository and API layers.
## 2026-07-31 Collection Action Boundary

Implemented the first Harness action endpoint:

- Added `POST /api/tasks/{task_id}/actions/start-collection`.
- Added repository helpers for starting, completing, and failing stages.
- Added artifact recording helper for future stage outputs.
- Added service logic that only allows this action on live tasks.
- Added tests for stage transition and duplicate-start rejection.

Current behavior:

- Starting collection moves the live task to `running`.
- The `collect_jobs` stage moves to `running`.
- A `collect_jobs_started` event is recorded.
- Duplicate start requests return a conflict response.

Engineering value:

- The API now has the same action shape that later real execution will use.
- The frontend can later enable a real “开始采集�?button against this stable endpoint.
- The actual collection runner can be connected without changing the external API contract.
## 2026-07-31 Collection Runner Integration

Implemented the first real execution bridge behind the collection action.

Changed behavior:

- `POST /api/tasks/{task_id}/actions/start-collection` now validates collection inputs and submits a background runner.
- The API returns immediately after the task enters `running` state.
- The runner derives city, city code, keyword, job type, expected count, source type, and output path from `analysis_tasks`.
- The runner calls the existing slow BOSS collection script instead of rewriting collection logic.
- The runner imports generated JSON through `jobuwant.boss_adapter.import_boss_json`.
- The runner creates a `job_search_runs` row and records a `search_run` artifact.
- Live task details can now expose `search_run_id` and `collected_count` after collection completes.

Engineering notes:

- The local executor is intentionally single-worker for the first local Web App version.
- Tests replace the real runner with fake functions, so backend tests do not start external collection.
- `intern` maps to platform job type `1902`; `any` and `full_time` currently run without a platform-side job type filter, leaving role filtering to the scoring stage.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 16 passed, 7 warnings.

## 2026-08-01 Scoring Action Integration

Implemented the local scoring action for live Web App tasks.

Changed behavior:

- Added `POST /api/tasks/{task_id}/actions/start-scoring`.
- Added `webapp/backend/app/services/scoring_service.py`.
- Extended `jobuwant.job_match_score.score_jobs` with an optional `existing_run_id` so Web App tasks can reuse the collection `job_search_runs` row.
- Live task job listing now reads scored rows after scoring completes.
- Scoring records a `scored_jobs` artifact and updates task distributions.
- Attempting scoring before collection completion returns HTTP 409 without changing task state.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 18 passed, 9 warnings.

## 2026-08-01 Sample Confirmation Integration

Implemented sample confirmation writes for live Web App tasks.

Changed behavior:

- Added `POST /api/tasks/{task_id}/sample`.
- Added `SampleConfirmRequest` schema.
- Added `webapp/backend/app/services/sample_service.py`.
- Added repository helpers for scored job id validation, sample creation, and latest sample selection lookup.
- Live job list now reflects the latest confirmed sample selection.
- Sample confirmation writes `analysis_samples`, `analysis_sample_items`, and a `sample` artifact.
- Unknown job ids and empty selected samples are rejected before task state changes.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 20 passed, 11 warnings.

## 2026-08-01 Structuring Batch Plan Integration

Implemented the AI structuring batch plan skeleton.

Changed behavior:

- Added `POST /api/tasks/{task_id}/actions/start-structuring`.
- Added `GET /api/tasks/{task_id}/structure`.
- Added `StructuringBatchRead` and `StructuringStatusRead` schemas.
- Added `webapp/backend/app/services/structuring_service.py`.
- Added repository helpers for latest sample lookup, selected sample job ids, batch creation, and batch listing.
- Added Harness duplicate-action protection for stages waiting for user confirmation.
- The stage now stops at `waiting_for_user` and does not call any model.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 24 passed, 15 warnings.

## 2026-08-01 Structuring Batch Runner Integration

Implemented the real execution boundary for AI structuring batches.

Changed behavior:

- Added `POST /api/tasks/{task_id}/actions/run-structuring-batches`.
- Added `webapp/backend/app/runner/structuring_runner.py`.
- Added repository helpers for resuming a waiting stage and updating batch states.
- Runner processes pending batches sequentially and persists per-batch status, model, token, cost, timing, and errors.
- Runner calls the existing `jobuwant.ai_job_extract` functions when the execution endpoint is explicitly called.
- Successful execution records an `extractions` artifact and marks `ai_structuring` completed.
- Failed batch execution marks the batch and stage failed.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 28 passed, 17 warnings.

Testing note:

- Tests use fake batch execution and do not call a model.

## 2026-08-02 Report Input Generation Integration

Implemented report input generation for live Web App tasks.

Changed behavior:

- Added `POST /api/tasks/{task_id}/actions/build-report-input`.
- Added `webapp/backend/app/services/report_input_service.py`.
- Added repository helper `get_task_row` for task-derived report parameters.
- Live `GET /api/tasks/{task_id}/report-input` now reads generated task artifacts.
- The service reuses `jobuwant.job_report.build_report_input` and `store_report_input`.
- Report input output is stored in `job_report_inputs` and `data/task_artifacts/{task_id}/report_input.json`.
- Tests seed fake extraction data and do not perform model work.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 30 passed, 19 warnings.

Next implementation focus:

- Implement final report generation behind `POST /api/tasks/{task_id}/actions/write-final-report`. This next step should require explicit approval before any real model work is run.
## 2026-08-02 Final Report Generation Integration

Implemented final report generation for live Web App tasks.

Changed behavior:

- Added `POST /api/tasks/{task_id}/actions/write-final-report`.
- Added `webapp/backend/app/services/final_report_service.py`.
- Added `webapp/backend/app/runner/final_report_runner.py`.
- Live `GET /api/tasks/{task_id}/report` now reads generated report artifacts.
- The runner reuses `jobuwant.ai_report_writer.load_settings`, `write_report_with_openai`, `save_report`, and `store_usage`.
- Final report output is stored in `job_reports` and `data/task_artifacts/{task_id}/final_report.json`.
- Tests use a fake report writer and do not perform model work.

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 32 passed, 21 warnings.

Next implementation focus:

- Wire the frontend controls for the live task flow in order: create task, start collection, start scoring, confirm sample, plan structuring, run structuring, build report input, and write final report.
## 2026-08-02 Frontend Live Workflow Wiring

Connected the frontend to the live backend workflow.

Changed behavior:

- Task list can create a live task through `POST /api/tasks`.
- Task detail shows Harness-driven next action buttons for the live flow.
- Task detail polls while a stage is running.
- Sample page can save selected job ids through `POST /api/tasks/{task_id}/sample`.
- Structure page now reads `GET /api/tasks/{task_id}/structure` and shows batch status, usage fields, and errors.
- Structure page can call batch planning and batch execution actions.
- Report input and final report actions are available from the task detail next-action panel.
- Fixture tasks remain read-only.

Verification:

- Frontend lint passed.
- Frontend typecheck passed.
- Frontend production build passed.
- Backend tests passed: 32 passed, 21 warnings.
- Backend health returned 200 at `http://127.0.0.1:8000/api/health`.
- Latest frontend preview returned 200 at `http://127.0.0.1:3001/tasks`.
## 2026-08-03 Web App UI Foundation Pass

Completed:

- Installed and used `web-design-guidelines` as the first UI review checklist.
- Added shared frontend UI foundation helpers in `webapp/frontend/src/components/ui/shell.tsx` for page shell, panels, status pill, metric block, empty state, error banner, and shared button styles.
- Rewrote the report input preview component to restore readable Chinese UI copy and reuse the shared panel/button primitives.
- Rewrote the final report viewer component to restore readable Chinese UI copy and reuse the shared panel/button primitives.
- Did not start new collection and did not call model-backed stages.

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.

Next:

- Apply the shared page shell to `/tasks` and `/tasks/{taskId}`.
- Continue layout refinement in workflow order: task list, task detail, sample confirmation, structure, report input, final report.

## 2026-08-04 Web App Task Pages Shell Pass

Completed:

- Applied the shared `AppShell`, `PageBody`, status pill, error, empty-state, panel, metric, and button primitives to `/tasks` and the task workspace shell.
- Refactored task workspace summary, stage timeline, artifact, chart, event, metadata, and readonly placeholder panels to use the shared UI foundation where low-risk.
- Kept workflow calls, polling behavior, routes, API contracts, and task action ordering unchanged.
- Started local backend and frontend services only for readonly smoke verification.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/task-list-page.tsx`
- `webapp/frontend/src/features/tasks/task-workspace.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report-input` returned 200.

Next:

- Continue the interface review order with `/tasks/{taskId}/sample`, then `/tasks/{taskId}/structure`, then report input/final report display refinements.

## 2026-08-04 Web App Sample Page Layout Pass

Completed:

- Applied shared `Panel`, `MetricBlock`, `ErrorBanner`, and shared button styles to `/tasks/{taskId}/sample`.
- Removed the local sample-page metric helper in favor of the shared UI primitive.
- Added clearer button icon treatment for refresh and save actions.
- Added accessible labels to the sample filters, row selection checkboxes, and row expand control.
- Kept job loading, filters, selection state, sample save payload, and callback behavior unchanged.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/sample-confirmation-panel.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/sample` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/sample` returned 200.

Next:

- Continue the interface review order with `/tasks/{taskId}/structure`, then revisit report input and final report display refinements.

## 2026-08-04 Web App Structure Page Layout Pass

Completed:

- Applied shared `Panel`, `PanelHeader`, `MetricBlock`, `ErrorBanner`, and shared button styles to `/tasks/{taskId}/structure`.
- Reworked the structure status panel and batch list panel for consistent spacing, heading hierarchy, and shadow treatment with the rest of the task workspace.
- Added a reusable batch table message row and table accessibility attributes.
- Improved long job-id and error-message wrapping inside the batch table.
- Kept status loading, batch planning action, batch execution action, refresh behavior, and parent task refresh callback unchanged.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/task-workspace.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/structure` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/structure` returned 200.

Next:

- Continue with report input and final report display refinements, then do a consolidated visual review across all task routes.

## 2026-08-04 Web App Report Pages Layout Pass

Completed:

- Refined `/tasks/{taskId}/report-input` with shared `PanelHeader`, `ErrorBanner`, metric icons, and consistent chart/card spacing.
- Refined `/tasks/{taskId}/report` with shared `PanelHeader`, `ErrorBanner`, metric icons, and consistent section headers for report-heavy content.
- Kept report input loading, final report loading, refresh behavior, and navigation to report input unchanged.
- Preserved the existing report data parsing helpers and display sections.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/report-input-preview-panel.tsx`
- `webapp/frontend/src/features/tasks/final-report-viewer.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report-input` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/report` returned 200.

Next:

- Run a consolidated visual review across all task routes and identify remaining layout polish items before moving into a broader visual redesign pass.

## 2026-08-04 Web App Consolidated UI Review Pass

Completed:

- Ran a consolidated UI consistency review across task list, task detail, sample confirmation, structure, report input, and final report routes using the `web-design-guidelines` checklist.
- Added accessible labels to task search and task/sample tables.
- Added table column scopes to task list and sample confirmation tables.
- Unified the task list detail link with the shared primary button style.
- Replaced the remaining old task detail action panel styling with the shared `Panel` and `ErrorBanner` primitives.
- Added current/selected state semantics to task workspace navigation and task selector controls.
- Kept all API calls, task routing, polling, filtering, sample selection, and workflow action behavior unchanged.
- Did not start a new collection and did not call model-backed stages.

Review findings addressed:

- Table semantics were inconsistent across task list and sample confirmation pages.
- The task detail next-action panel still used the older shadow and local error treatment.
- Current navigation state was visual-only in the task workspace sidebar.

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/sample` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/structure` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report-input` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/sample` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/structure` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/report-input` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/report` returned 200.

Next:

- Move from shared-component cleanup into a broader visual redesign pass, starting with a concrete visual direction for task workspace density, sidebar behavior, and final report reading layout.
