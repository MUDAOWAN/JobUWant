# Web App TODO

Purpose: track the next development phase for replacing the Streamlit pilot
with a formal web application.

Status: created on 2026-07-28 after `WEB_APP_PRODUCT_SPEC.md` was accepted as
the product flow baseline.

## Current Baseline

- The Streamlit pilot has validated the end-to-end analysis chain.
- The Hangzhou Agent engineer intern 40-job run completed.
- The Guangzhou GIS any-job-type 30-job run completed.
- The next phase is productizing the flow into a future-public-site-style web
  application.

## Next Work Sequence

### 1. Frontend Research

Status: next.

- Check whether a suitable frontend Codex skill or project template is
  available.
- Review any frontend reference materials provided by the user.
- Frontend route decided: FastAPI + Next.js is the recommended baseline; React/Vite remains a fallback only.
- Decide the UI component direction, such as shadcn/ui, Ant Design, Mantine, or
  a custom Tailwind-based system.
- Decide the charting library, such as ECharts, Recharts, or Nivo.
- Record the decision and reasoning before implementation.

### 2. Technical Architecture Design

Status: next.

- Draft `docs/WEB_APP_TECH_DESIGN.md`.
- Plan a formal frontend/backend split while keeping the first version local.
- Proposed baseline to evaluate:
  - backend: FastAPI
  - frontend: Next.js + TypeScript
  - database: SQLite first, PostgreSQL-compatible model later
  - execution: local sequential task runner first, background worker later
- Keep existing Python modules as the service layer wherever practical.
- Avoid rewriting the validated analysis chain before it is wrapped by APIs.

### 3. Data Model Design

Status: after architecture draft.

- Add task-level records around the existing tables:
  - `analysis_tasks`
  - `task_stage_runs`
  - `analysis_samples`
  - `batch_runs`
- Preserve existing records:
  - `job_details`
  - `job_search_runs`
  - `job_search_run_items`
  - `job_extractions`
  - `job_report_inputs`
  - `job_reports`
  - `usage_events`
- Store selected and excluded job ids for every confirmed sample.
- Store per-stage and per-batch timing, status, model, token, and error data.

### 4. API Design

Status: after data model draft.

- Design endpoints for:
  - create task
  - list tasks
  - get task detail
  - start job collection
  - run local scoring
  - list collected jobs
  - save confirmed sample
  - start AI structuring
  - retry a failed structuring batch
  - generate report input
  - generate final report
  - read final report
  - read task logs
- Define request and response schemas before frontend implementation.
- Keep API status fields aligned with `WEB_APP_PRODUCT_SPEC.md`.

### 5. Frontend Prototype

Status: after architecture and API draft.

- Design the first page map:
  - task creation
  - task detail and stage timeline
  - collection progress
  - scoring and sample confirmation
  - AI structuring progress
  - report input preview
  - final report view
- Choose a balanced style: clear task operation plus polished report reading.
- Prioritize clean information density, readable tables, useful charts, and
  evidence traceability.

### 6. Implementation Plan

Status: after prototype.

- Build the backend API skeleton first, using fixture-first endpoints before live long-stage execution.
- Add task-level database tables and migrations.
- Wrap existing Python chain in service functions.
- Build frontend task creation and task detail pages after the core task/report API contracts are fixed.
- Build collection and scoring views.
- Build selectable job table.
- Build AI structuring batch progress view.
- Build report input preview.
- Build final report page.
- Use the two completed runs as regression fixtures.

## Confirmed Route Update - 2026-07-28

- The project has a future public-use direction, so the recommended frontend route is now Next.js rather than React/Vite.
- Backend remains FastAPI because the validated analysis chain is Python-based and should be wrapped, not rewritten.
- SQLite remains the first local database, with a schema shaped for later PostgreSQL migration.
- Formal Web App code should be created under webapp/.
- The first implementation should be fixture-first: show the validated Hangzhou and Guangzhou outputs through the new Web App before connecting live long-running execution.
- Skill usage is staged: design skill before visual prototype, React/Next implementation skill during component work, frontend review skill before acceptance, and webapp-testing skill during browser verification.
- Do not install skills until the user confirms the exact phase and command.
- Do not create a JobUWant-specific skill yet; wait until the Web App workflow is stable enough to encode as a reusable SOP.

## First Version Non-Goals

- Login and account system.
- Payment.
- Multi-user permissions.
- Public deployment.
- Historical comparison UI.
- Resume upload and personal fit scoring.
- Scheduled refresh.
- Complex workflow engine.
- Cloud database migration.

## Regression Fixtures

- Hangzhou + Agent engineer + intern, 40 jobs:
  - source type: `boss_hz_agent_intern_20260726_probe40`
  - valid search run: `search_run_id=7`
  - report input: `data/job_report_input_hz_agent_intern_probe40.json`
  - latest report: `data/job_report_hz_agent_intern_probe40_v2.json`
- Guangzhou + GIS + any job type, 30 jobs:
  - source type: `boss_gz_gis_any_20260727_probe30`
  - valid search run: `search_run_id=8`
  - report input: `data/job_report_input_gz_gis_any_probe30.json`
  - latest report: `data/job_report_gz_gis_any_probe30.json`
