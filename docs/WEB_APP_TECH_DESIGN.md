# Web App Tech Design

Status: draft for user review on 2026-07-28.

Purpose: define the first formal Web App architecture after the Streamlit pilot validated the full job-analysis chain.

## 1. Context And Constraints

Current validated chain:

    job_details -> job_match_score.py -> ai_job_extract.py -> job_report.py -> ai_report_writer.py

Regression fixtures:

- Hangzhou + Agent engineer + intern, 40 jobs: source_type boss_hz_agent_intern_20260726_probe40, valid search_run_id 7, report input data/job_report_input_hz_agent_intern_probe40.json, latest report data/job_report_hz_agent_intern_probe40_v2.json.
- Guangzhou + GIS + any job type, 30 jobs: source_type boss_gz_gis_any_20260727_probe30, valid search_run_id 8, report input data/job_report_input_gz_gis_any_probe30.json, latest report data/job_report_gz_gis_any_probe30.json, timing record data/run_timing_gz_gis_any_probe30.json.

Hard constraints:

- Do not keep Streamlit as the formal UI.
- Do not replace the validated Python analysis modules.
- Do not re-run existing Hangzhou or Guangzhou samples unless explicitly asked.
- Keep the first formal Web App local-first.
- Do not add login, payment, multi-user permissions, public deployment, or historical comparison UI in the first Web MVP.
- Put the formal Web App code under one project subdirectory.

## 2. Skill And Template Research

Candidate skills:

- ui-ux-pro-max, from nextlevelbuilder/ui-ux-pro-max-skill. Fit: UI/UX system generation, style matching, dashboard/report page polish, React/Next/shadcn/Tailwind guidance.
- frontend-design, from anthropics/skills. Fit: lightweight frontend design guidance.
- vercel-react-best-practices, from vercel-labs/agent-skills. Fit: React and Next.js implementation guidance.
- web-design-guidelines, from vercel-labs/agent-skills. Fit: UI quality checks after pages exist.
- frontend-design-review, from microsoft/skills. Fit: structured frontend implementation review.
- webapp-testing, from anthropics/skills. Fit: browser-based local Web App testing with Playwright, screenshots, DOM inspection, and console-log capture.
- ComposioHQ/awesome-claude-skills. Fit: broad catalog for discovery, not a single JobUWant implementation skill.

Recommendation:

- Use ui-ux-pro-max or frontend-design during visual design.
- Use vercel-react-best-practices during React implementation.
- Use web-design-guidelines or frontend-design-review before accepting large UI changes.
- Use webapp-testing for browser verification.
- Use docs/coding*.md, WEB_APP_PRODUCT_SPEC.md, and this file as the project-specific guide.
- Create a JobUWant-specific skill only after the Web App workflow repeats enough to justify a reusable SOP.

Install no skill before user confirmation. Candidate commands to verify before running:

    npx skills add https://github.com/anthropics/skills --skill frontend-design
    npx skills add https://github.com/anthropics/skills --skill webapp-testing
    npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices
    npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines
    npx skills add https://github.com/microsoft/skills --skill frontend-design-review
    npx ui-ux-pro-max-cli init --ai codex

## 3. Frontend Route Evaluation

Option A: FastAPI + Next.js. Recommended for the first Web MVP.

Why it fits:

- The workflow is local, operational, and API-driven.
- The validated Python chain can be wrapped directly by FastAPI services.
- Next.js is a better long-term fit for a product that will later be opened to other users.
- Public pages, documentation pages, report sharing pages, route-level layouts, metadata, and SEO can be added without a later frontend migration.
- The first version can still run locally and avoid login, payment, and multi-user permissions.
- A later worker can replace the local runner without changing frontend route shape.

Tradeoffs:

- The frontend and backend run as two local services during development.
- FastAPI remains the real backend for Python workflow execution, so Next.js should not duplicate business workflow logic.
- API client types need to be generated or maintained.

Option B: FastAPI + React/Vite. Acceptable quick local option, not recommended now.

Why it may fit:

- Vite keeps local frontend development simple and fast.
- A React SPA is enough for the current task workflow.

Why not choose it after the latest product decision:

- The project now has a confirmed future public-use direction.
- Public pages, SEO, and shareable report routes would likely require a later migration or a second frontend surface.

Option C: official FastAPI full-stack template. Use as a reference only. It already combines FastAPI, React, TypeScript, Vite, SQLModel, PostgreSQL, Docker, generated frontend client, and Playwright, but the first JobUWant Web MVP should avoid login, PostgreSQL, Docker, and production deployment complexity.

## 3.1 Skill And Harness Usage Plan

Skill usage should be staged, not installed upfront. Use the project docs as the primary source of truth, then add specialized skills only when they improve a concrete phase.

- UI style phase: use ui-ux-pro-max or frontend-design before building the first report page and task workspace.
- Next.js implementation phase: use vercel-react-best-practices after the route map and component boundaries are fixed.
- Frontend acceptance phase: use web-design-guidelines or frontend-design-review after pages are visible.
- Browser verification phase: use webapp-testing when the local Next.js and FastAPI services are running.
- Project-specific process: do not create a JobUWant skill yet. First repeat the Web App workflow, then turn the stable SOP into a local skill.

Harness direction:

- Keep the validated Python harness as application service logic behind FastAPI.
- Add task, stage, event, sample, batch, and artifact records around that harness.
- Do not introduce a workflow framework in the first Web MVP.
- Use deterministic state transitions, Pydantic schema validation, local cache reuse, and explicit evidence checks as the first quality layer.
- A worker process, SSE, or external workflow system can be added after local task execution and progress tracking are stable.

Development order decision:

- Define backend API contracts and task data model before building full frontend behavior.
- Build a thin fixture-first backend before the main UI pages.
- Build frontend pages against those contracts and existing fixtures.
- Only after the fixture-first UI is stable, connect live long-running stage execution.
- Page style should be guided by the selected design skill, but the API and state model should not wait on visual polish.

## 4. Architecture Decision

Recommended baseline:

    webapp/
      backend/
        app/api/
        app/core/
        app/schemas/
        app/services/
        app/repositories/
        app/runner/
        app/main.py
        tests/
      frontend/
        src/app/
        src/pages/
        src/features/
        src/components/
        src/api/
        src/lib/
        src/styles/
        tests/
      README.md
      docs/

Stack:

- Backend: FastAPI, Pydantic, SQLite, existing jobuwant Python modules.
- Frontend: Next.js, TypeScript.
- UI: Tailwind CSS plus shadcn/ui-style components.
- Tables: TanStack Table.
- API state: TanStack Query.
- Charts: Recharts for the first version.
- Browser tests: Playwright.
- Local database: keep data/jobuwant.sqlite3 for the first migration step.

Layering:

    frontend pages/components -> frontend api client -> FastAPI routes -> application services -> existing jobuwant modules -> repositories / SQLite -> data artifacts

Backend rules:

- API layer validates request data and returns response schemas.
- Service layer controls stage ordering, task status, and calls existing modules.
- Repository layer owns SQL for new task-level tables.
- Existing analysis modules remain the source of detailed scoring, extraction, report-input, and final-report behavior.
- Model outputs continue to use Pydantic validation before persistence.

Frontend rules:

- Build task-first product screens, not a marketing landing page.
- Use dense but readable operational views for long-running stages.
- Make the final report page polished, with charts and evidence references.
- Keep UI state derived from backend task state.

## 5. Backend API Design

All responses should include trace_id, status, message, data, and optional error.

Tasks:

- POST /api/tasks creates AnalysisTask with task_name, city, city_code, keyword, job_type, expected_job_count, batch_size, and notes.
- GET /api/tasks lists tasks with status, limit, and offset filters.
- GET /api/tasks/{task_id} returns task detail, current stage, latest stage runs, sample summary, report pointers, and latest events.

Collection:

- POST /api/tasks/{task_id}/collect starts, continues, proceeds with current result, or reruns collection. First version may import a prepared local JSON file or call the existing staged collection script through a controlled runner.
- GET /api/tasks/{task_id}/collection returns counters, latest stage event, stopping reason, and collected job preview.

Scoring and sample:

- POST /api/tasks/{task_id}/score calls local scoring and returns search_run_id, match distribution, role-intent distribution, and top matches.
- GET /api/tasks/{task_id}/jobs returns rows combining job_details and job_search_run_items, with filters for match_status, role_intent, city, company_keyword, title_keyword, selected_only, limit, and offset.
- POST /api/tasks/{task_id}/sample saves selected_job_ids and excluded_job_ids as an AnalysisSample.

AI structuring:

- POST /api/tasks/{task_id}/structure creates batch_runs for a sample and returns immediately.
- GET /api/tasks/{task_id}/structure returns batch progress, token usage, elapsed time, model, and error messages.
- POST /api/tasks/{task_id}/structure/batches/{batch_id}/retry retries only one failed batch.

Report input and report:

- POST /api/tasks/{task_id}/report-input builds and stores a compact report input.
- GET /api/tasks/{task_id}/report-input returns preview sections and raw JSON.
- POST /api/tasks/{task_id}/report starts final report generation.
- GET /api/tasks/{task_id}/report returns final report JSON plus frontend-ready sections and evidence links.

Events:

- GET /api/tasks/{task_id}/events returns append-only task events.
- GET /api/tasks/{task_id}/events/stream can be added later for SSE. Polling is enough for the first version.

## 6. Data Model Design

Keep existing detailed tables:

- job_details
- job_search_runs
- job_search_run_items
- job_extractions
- job_terms
- job_report_inputs
- job_reports
- usage_events

Add task-level tables:

analysis_tasks:

- id, task_name, city, city_code, keyword, job_type, expected_job_count, batch_size, source_type, status, notes, created_at, updated_at, started_at, finished_at.
- Indexes: status plus updated_at, city plus keyword plus job_type, source_type.

task_stage_runs:

- id, task_id, stage_name, status, started_at, finished_at, elapsed_seconds, input_json, output_json, error_code, error_message, created_at, updated_at.
- Indexes: task_id plus stage_name plus status, task_id plus updated_at.

task_events:

- id, task_id, stage_run_id, level, event_type, message, payload_json, created_at.
- Indexes: task_id plus id, task_id plus event_type.

analysis_samples:

- id, task_id, search_run_id, sample_version, selected_count, excluded_count, selected_job_ids_json, excluded_job_ids_json, selection_note, created_at, updated_at.
- Indexes: task_id plus sample_version, search_run_id.

analysis_sample_items:

- id, sample_id, job_detail_id, selected, match_score, match_status, role_intent, created_at.
- Indexes: sample_id plus selected, sample_id plus job_detail_id.

batch_runs:

- id, task_id, sample_id, stage_run_id, batch_index, batch_size, job_ids_json, status, model_name, input_tokens, output_tokens, estimated_cny, started_at, finished_at, elapsed_seconds, error_code, error_message, created_at, updated_at.
- Indexes: task_id plus sample_id plus batch_index, task_id plus status.

task_artifacts:

- id, task_id, artifact_type, path, related_table, related_id, summary_json, created_at.
- Indexes: task_id plus artifact_type, related_table plus related_id.

## 7. Status Model

Task statuses:

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

Stage and batch statuses:

- pending
- running
- completed
- failed
- skipped, only for stage runs

Allowed stage order:

    create_task -> collect_jobs -> score_jobs -> confirm_sample -> ai_structuring -> build_report_input -> write_final_report

State rules:

- A task record must exist before long work starts.
- Every stage run must write started_at, finished_at, elapsed_seconds, and final status.
- Any model stage must write model name, tokens, estimated cost, and validation result.
- Failed stages keep input and partial output for local diagnosis.
- Regenerating a sample or report creates a new sample, run, or artifact instead of silently overwriting prior state.

## 8. Long Task Execution

First version:

- Use a local single-process runner inside the FastAPI backend.
- Use a small task executor with one active task at a time by default.
- Persist stage and batch state in SQLite before and after every meaningful step.
- Frontend polls task detail and stage endpoints every 1-2 seconds while a stage is running.
- Write append-only task_events for progress messages shown in the UI log panel.

Implementation shape:

    POST /api/tasks/{id}/structure
    -> create task_stage_runs row
    -> create batch_runs rows
    -> enqueue local runner callable
    -> return immediately

    runner callable
    -> load selected job ids
    -> run one batch through existing ai_job_extract functions
    -> save job_extractions and usage_events
    -> update batch_runs
    -> append task_events
    -> update task status

Why not add a full task queue now:

- Current use case is local single-user.
- Existing validated runs are sequential.
- The immediate product need is visible status and recovery, not horizontal scaling.

Later upgrade path:

- Replace the in-process runner with a worker process.
- Keep the same task/state tables.
- Add SSE only after polling proves insufficient.

## 9. Frontend Page Structure

Recommended routes:

- / redirects to /tasks or shows the task list.
- /tasks shows task list, latest status, city, keyword, sample count, and report status.
- /tasks/new shows task creation form.
- /tasks/:taskId shows task overview, stage timeline, and next action.
- /tasks/:taskId/collect shows collection progress and imported job preview.
- /tasks/:taskId/sample shows scoring result, filters, selectable job table, and expandable original text.
- /tasks/:taskId/structure shows batch progress, token usage, elapsed time, and failed batch retry.
- /tasks/:taskId/report-input shows compact report input preview, charts, evidence quality, and JSON viewer.
- /tasks/:taskId/report shows final report reading experience.

Key UI components:

- TaskShell
- StageTimeline
- TaskStatusBadge
- MetricStrip
- ProgressLog
- JobSelectionTable
- OriginalTextDrawer
- BatchRunList
- ReportInputPreview
- EvidenceQuote
- FinalReportSections
- TopTermsChart
- DistributionChart

Design direction:

- Operational pages should be calm, dense, and easy to scan.
- The report page should feel more refined, with stronger section hierarchy, charts, and evidence reveal interactions.
- Avoid nested cards and decorative layout.
- Use icons for repeated actions such as retry, download, expand, collapse, and refresh.

## 10. Service Wrapping Plan

- TaskService: create/update tasks, enforce stage transitions, append events.
- CollectionService: import existing local JSON output, later call controlled collection runner.
- ScoringService: call jobuwant.job_match_score.score_jobs and map result to task summaries.
- SampleService: save selected/excluded job ids and build analysis_sample_items.
- StructuringService: call jobuwant.ai_job_extract functions and update batch_runs.
- ReportInputService: call jobuwant.job_report functions.
- ReportService: call jobuwant.ai_report_writer functions.

No service should call Streamlit code.

## 11. Error Handling

- Collection shortfall: record actual count, target count, and stopping reason; set collection_incomplete; allow continue or proceed with current results.
- Scoring failure: keep collected jobs unchanged, mark score_jobs failed, allow retry scoring.
- Sample issues: reject empty selected sample; reject job ids outside the task search run; create a new sample version after downstream outputs exist.
- AI structuring failure: mark only the current batch as failed; keep completed batches; allow retry for that batch only; do not mark task structured until all selected batches complete.
- Report input failure: show missing extraction count and job ids; allow returning to structuring stage.
- Final report failure: preserve report input; allow retry final report without rerunning earlier stages.

## 12. Development Phases

Phase 0: Approval.

- Review and confirm this technical design.
- Decide whether to install any project-scoped skills.
- Decide final frontend route, confirmed recommendation FastAPI + Next.js.

Phase 1: Project skeleton.

- Create webapp/.
- Add webapp/backend FastAPI skeleton.
- Add webapp/frontend Next.js TypeScript skeleton.
- Add local README and dev commands.
- Do not move existing jobuwant modules.

Phase 2: Backend foundation.

- Add task-level SQLite tables.
- Add Pydantic schemas.
- Add task CRUD APIs.
- Add task events and stage-run helpers.
- Add tests for task creation and status transitions.

Phase 3: Fixture-first Web flow.

- Use existing Hangzhou and Guangzhou artifacts as read-only fixtures.
- Build task detail, scoring summary, sample table, report input preview, and final report read APIs.
- Avoid new external calls in this phase.

Phase 4: Frontend core pages.

- Build task list and create task page.
- Build task overview and stage timeline.
- Build sample confirmation table.
- Build report input preview.
- Build final report page with charts and evidence references.

Phase 5: Live stage execution.

- Add local runner for import, scoring, structuring batches, report input, and final report.
- Add polling-driven progress UI.
- Add retry for failed structuring batches.

Phase 6: Verification.

- Backend: run schema and API tests.
- Frontend: run type check, build, and browser tests.
- End-to-end: verify both existing fixtures reach final report view without changing their source data.

Phase 7: Streamlit retirement decision.

- Keep Streamlit as a debug surface until the Web App covers the same validated workflow.
- Remove or freeze Streamlit only after user approval.

## 13. Verification Plan

Required before accepting the first Web MVP:

- POST /api/tasks creates persistent task rows.
- The app can bind to search_run_id 7 and search_run_id 8.
- The sample confirmation page can show selected and excluded jobs.
- Report input preview reads the existing JSON artifacts correctly.
- Final report page renders both existing reports.
- AI structuring batch state can be represented without starting a real model call during fixture tests.
- Browser test covers task creation, sample filtering, report input preview, and report view.

Recommended commands after implementation exists:

    cd /home/votally/projects/JobUWant/webapp/backend
    pytest

    cd /home/votally/projects/JobUWant/webapp/frontend
    npm run typecheck
    npm run build
    npm run test:e2e

## 14. References

- Vite guide: https://vite.dev/guide/
- Next.js App Router docs: https://nextjs.org/docs/app
- Next.js installation docs: https://nextjs.org/docs/app/getting-started/installation
- FastAPI features: https://fastapi.tiangolo.com/features/
- shadcn/ui installation: https://ui.shadcn.com/docs/installation
- Recharts: https://recharts.github.io/en-US/
- TanStack Query docs: https://tanstack.dev/query/latest/docs/framework
- FastAPI full-stack template: https://github.com/fastapi/full-stack-fastapi-template
- Vercel skills CLI: https://github.com/vercel-labs/skills
- skills.sh docs: https://www.skills.sh/docs
- Design and UI skill topic: https://www.skills.sh/topic/design
- ui-ux-pro-max skill: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- Awesome Claude Skills catalog: https://github.com/ComposioHQ/awesome-claude-skills
- webapp-testing skill: https://officialskills.sh/anthropics/skills/webapp-testing
- Vercel React best practices skill: https://www.skills.sh/vercel-labs/agent-skills/react-best-practices
- Microsoft frontend design review skill: https://officialskills.sh/microsoft/skills/frontend-design-review
