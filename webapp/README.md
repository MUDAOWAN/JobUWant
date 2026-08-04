# JobUWant Web App

Status: fixture-first pages and Harness baseline are implemented.

This directory will contain the formal Web App version of JobUWant.

## Confirmed Baseline

- Backend: FastAPI plus Pydantic.
- Frontend: Next.js plus TypeScript.
- Database: SQLite first, with a PostgreSQL-compatible model direction later.
- UI direction: Tailwind CSS plus shadcn-ui-style components.
- Tables: TanStack Table.
- API state: TanStack Query.
- Charts: Recharts.
- Browser verification: Playwright when implementation starts.

## Boundary

The existing Streamlit pilot and validated Python analysis modules stay at the repository root and under the jobuwant package.

The Web App should wrap the existing chain through APIs instead of rewriting it:

    job_details -> job_match_score.py -> ai_job_extract.py -> job_report.py -> ai_report_writer.py

## First Implementation Rule

The first Web App implementation should be fixture-first:

- Read existing Hangzhou and Guangzhou artifacts.
- Display task, sample, report-input, and final-report views.
- Do not run new collection or model stages until the fixture-first UI path works.

## Planned Structure

    webapp/
      backend/
      frontend/
      docs/


## Frontend Status

The Next.js frontend skeleton now exists under webapp/frontend.

Current frontend features:

- Reads GET /api/health.
- Reads GET /api/tasks.
- Reads GET /api/tasks/{task_id} for the selected fixture task.
- Shows task list, selected task metrics, stage timeline, match distribution, and artifact paths.

Frontend commands:

    export PATH=/home/votally/projects/JobUWant/webapp/.tools/node/bin:$PATH
    cd /home/votally/projects/JobUWant/webapp/frontend
    npm run typecheck
    npm run build
    npm run dev

Environment note:

- Project-local Linux Node.js is installed at webapp/.tools/node.
- Use PATH=/home/votally/projects/JobUWant/webapp/.tools/node/bin:$PATH before frontend npm commands in WSL.
- Typecheck and production build pass with the project-local Linux Node.js.


## Stable Local Frontend Preview

For stable local viewing, build first and run the production preview server:

    export PATH=/home/votally/projects/JobUWant/webapp/.tools/node/bin:$PATH
    cd /home/votally/projects/JobUWant/webapp/frontend
    npm run build
    /home/votally/projects/JobUWant/webapp/scripts/start-frontend.sh

Current stable frontend URL:

    http://127.0.0.1:3000

## Stable Local Backend

For stable local backend serving, use:

    /home/votally/projects/JobUWant/webapp/scripts/start-backend.sh

Current backend URL:

    http://127.0.0.1:8000
## Harness Baseline

The Web App now has a lightweight in-repo Harness at:

    webapp/backend/app/services/task_harness.py

The Harness defines the executable task lifecycle:

    collect_jobs -> score_jobs -> confirm_sample -> ai_structuring -> build_report_input -> write_final_report

Related docs:

    webapp/docs/WEB_APP_HARNESS.md
    webapp/docs/IMPLEMENTATION_RECORD.md

Current backend verification:

    cd /home/votally/projects/JobUWant/webapp/backend
    PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q
## Live Task Creation

The backend now supports creating a live analysis task without starting collection:

    POST /api/tasks

Creation initializes:

- one `analysis_tasks` row
- six `task_stage_runs` rows from the Harness stage manifest
- one `task_created` event

The public API id format for live tasks is `task-{id}`, for example `task-1`.
## Collection Action Boundary

The backend now supports the first Harness action endpoint:

    POST /api/tasks/{task_id}/actions/start-collection

Current behavior:

- live tasks only
- validates Harness order
- marks `collect_jobs` as `running`
- marks the task as `running`
- records a `collect_jobs_started` event

The actual collection runner will be connected in a later step.
## Collection Runner

The backend now connects `POST /api/tasks/{task_id}/actions/start-collection` to a local one-worker collection runner.

Behavior:

- The endpoint validates live task inputs and returns immediately after queueing the runner.
- The runner calls the existing Python collection script and writes progress into `task_events`.
- Completion imports the JSON output into `job_details`, creates a `job_search_runs` row, and records a `search_run` task artifact.
- Tests replace the real runner and do not perform live collection.

Important local-use note:

- Do not call the collection action for a new task unless you intentionally want to start a real collection run.

## Scoring Action

The backend now supports `POST /api/tasks/{task_id}/actions/start-scoring` for live tasks.

Behavior:

- Requires completed collection.
- Reuses the task collection `search_run_id`.
- Runs local scoring only; no model call is involved.
- Records `scored_jobs` as a task artifact.
- Enables live `GET /api/tasks/{task_id}/jobs` after scoring.

## Sample Confirmation

The backend now supports `POST /api/tasks/{task_id}/sample` for live tasks.

Behavior:

- Requires completed local scoring.
- Saves selected and excluded job ids as a versioned sample.
- Writes `analysis_samples` and `analysis_sample_items`.
- Records a `sample` task artifact.
- Updates live job rows so selected-only views use the latest saved sample.

## Structuring Batch Plan

The backend now supports AI structuring batch planning without running model work.

Endpoints:

- `POST /api/tasks/{task_id}/actions/start-structuring`
- `GET /api/tasks/{task_id}/structure`

The start action creates pending `batch_runs`, records a `batch_runs` artifact, and leaves the `ai_structuring` stage in `waiting_for_user` until model execution is explicitly approved.

## Structuring Batch Execution

The backend now supports explicit structuring batch execution through:

- `POST /api/tasks/{task_id}/actions/run-structuring-batches`

This action resumes an `ai_structuring` stage that is waiting for user confirmation and queues the local runner. It is the endpoint that performs model work when explicitly called. Tests use fake batch execution and do not call a model.

## Report Input Generation

The backend now supports live report input generation through:

- `POST /api/tasks/{task_id}/actions/build-report-input`
- `GET /api/tasks/{task_id}/report-input`

The action requires completed structuring output, builds the compact report input with the existing Python report module, stores it in SQLite and JSON, and records a `report_input` artifact. It does not perform model work.
## Final Report Generation

The backend now supports live final report generation through:

- `POST /api/tasks/{task_id}/actions/write-final-report`
- `GET /api/tasks/{task_id}/report`

The action requires a generated report input, queues the local final report runner, stores the output in SQLite and JSON, and records a `report` artifact. This action is the model-backed report step when explicitly called.
## Frontend Live Workflow Controls

The frontend now exposes the first live workflow controls:

- create a live task on `/tasks`
- use the task detail next-action panel to call live backend actions in Harness order
- save sample selection on `/tasks/{taskId}/sample`
- inspect and run structuring batches on `/tasks/{taskId}/structure`
- open generated report input and final report pages after artifacts exist

Fixture tasks remain read-only. In this session, the latest preview build is available at:

    http://127.0.0.1:3001/tasks