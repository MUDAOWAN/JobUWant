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


## Final Report Page Redesign TODO - 2026-08-14

Goal: redesign the final report page as a professional report dashboard with clear hierarchy, reusable sections, and chart-ready data slots.

Important generalization rule: the report page and backend data contracts must work for any user-entered role, not just one hard-coded role family. Section names, category labels, chart data, and AI-generated text should be shaped so they can cover software roles, operations roles, e-commerce roles, data roles, hardware roles, and other future search targets.

### 1. Top Report Summary

Purpose: keep the current 'job report' hero style, but replace weak generic summary text with a decision-oriented market summary.

Display:

- report title
- query scope: city, role keyword, job type, sample count
- market summary: role direction, market demand, salary/threshold signal, common talent profile, and preparation focus
- compact generation metadata such as model, token, estimated cost, and time
- optional small sample-quality label if it is already available from report input data

UI direction:

- keep the current top module style as the visual anchor
- use one strong title, one concise summary paragraph, and compact chips for query scope
- do not place large charts in this section

### 2. Core Metrics Bar

Purpose: give the user a quick numerical overview before the detailed charts.

Display:

- sample job count
- strong-match job count
- average match score
- top high-frequency skill or ability
- salary median or average range when enough salary data exists
- evidence quote hit ratio or sample quality indicator when already computed

Notes:

- Do not show bachelor-degree ratio as a top metric.
- Do not put 'intern friendliness' in the top metrics unless its definition is made explicit and reliable.
- Evidence quote hit ratio can come from evidence_quality.exact_quote_hit_ratio produced by report input generation; it should not require additional model work.

UI direction:

- compact horizontal metric cards
- each card uses label, value, and a short helper line
- keep the cards secondary to the report summary and later charts

### 3. Skill And Ability Distribution

Purpose: show what the market repeatedly asks for, without assuming every role is a pure technical role.

Display:

- top 15 high-frequency skills or abilities
- hit count and hit ratio per item, such as 18/30 - 60%
- category distribution for skills or abilities
- layered matrix: must-have, common, bonus, low-frequency signal

Charts:

- horizontal bar chart for top skills/abilities
- donut chart or stacked bar for category distribution
- layered matrix cards for priority groups

Generalization:

- Java roles may categorize backend frameworks, databases, middleware, engineering tools, and frontend collaboration.
- Operations roles may categorize content operations, growth, data analysis, platform tools, and campaign planning.
- E-commerce roles may categorize platform operations, product operations, paid traffic, data analysis, and supply-chain coordination.
- Categories should be derived from structured job outputs across the selected sample, not fixed in the frontend.

UI direction:

- preserve the useful feel of the current skill overview module
- show hit ratio as quiet supporting text, not as the dominant visual

### 4. Resume Adaptation Suggestions

Purpose: translate market requirements into resume wording and project presentation guidance.

Display:

- market keywords grouped by skill/ability type
- mapping from market requirement to resume expression
- project or experience highlights that should be emphasized
- role-specific wording suggestions that are concrete enough to use in a resume

Suggested layout:

- left column: market keyword groups
- right column: resume-expression table

Example table shape:

- market requirement
- resume expression direction
- related project or evidence angle

Generalization:

- For engineering roles, emphasize technology, architecture, project modules, and measurable delivery.
- For operations or e-commerce roles, emphasize platform experience, data metrics, campaign execution, user or product growth, and business outcomes.
- The prompt should avoid generic advice and produce role-adapted, resume-ready wording.

### 5. Job Structure Analysis

Purpose: help the user understand what kinds of jobs were found, which related roles are worth considering, and how much unrelated or weakly matched material exists.

Display:

- job type or role cluster distribution
- match status distribution: strong match, review, weak match
- representative job list
- adjacent role directions worth considering

Charts:

- donut chart for role cluster distribution
- stacked bar or grouped bar for match status distribution
- compact table for top 5-8 representative jobs

Representative job table fields:

- company
- job title
- match score
- key skills or abilities
- salary
- education or experience requirement
- source link

UI direction:

- this section explains market composition, not learning advice
- use charts first, then a compact evidence table

### 6. Salary And Threshold Analysis

Purpose: show compensation and entry requirements clearly.

Display:

- salary range distribution
- average salary range and median salary when enough data exists
- education requirement distribution
- experience requirement distribution for non-intern tasks
- short threshold summary

Charts:

- salary range bar chart
- education requirement pie or donut chart
- experience requirement bar chart, hidden for intern tasks

Rules:

- Internship tasks should prefer daily salary ranges.
- Full-time tasks should prefer monthly salary ranges.
- If both daily and monthly salary samples exist, use tabs or segmented controls.
- If salary samples are too sparse, show a clear insufficient-data state rather than a misleading chart.
- Experience buckets should be normalized, for example: no requirement, fresh graduate, under 1 year, 1-3 years, 3-5 years, 5+ years, unspecified.

### 7. Learning Route And Preparation Priority

Purpose: provide a clear technical or capability learning path and preparation priority, not a long essay.

Display:

- staged learning route
- skills or abilities to learn at each stage
- target outcome or deliverable for each stage
- preparation priority matrix
- concise application advice when helpful

Suggested route shape:

- entry foundation
- core skills
- project practice
- advanced bonus
- application expression

Charts / visuals:

- horizontal or vertical timeline
- priority matrix: must learn, fill soon, bonus, postpone
- grouped skill tags per stage

UI direction:

- make the route readable at a glance
- avoid overly detailed study plans in the first version
- keep application advice concise and tied to the role search result

### Deferred / Optional

Do not make a separate evidence and data-quality section in the first redesign. Sample count and evidence quote hit ratio can appear in the top summary or core metrics. If needed later, add a lightweight collapsed 'Sample notes' area with sample limits, quote rules, and data caveats. Do not show raw JSON in the user report page by default.

### Execution Plan - 2026-08-14

The redesign should proceed as a thin-slice implementation to control UI drift and token cost.

First implementation slice:

- Read both final report data and report-input data on the final report page.
- Build the new Top Report Summary.
- Build the Core Metrics Bar.
- Add lightweight skeleton sections for the remaining report modules so the user can review overall hierarchy, naming, spacing, and density before deeper work.
- Use existing report-input fields where they are already stable; show professional empty states where data is not available.
- Do not change backend schemas or AI prompts in this slice.

After the first slice is reviewed, continue module by module:

1. Skill And Ability Distribution
2. Job Structure Analysis
3. Salary And Threshold Analysis
4. Resume Adaptation Suggestions
5. Learning Route And Preparation Priority

For the data-heavy modules, implement one module per pass or at most two closely related modules per pass. Keep final report text as supporting material and report-input data as the primary source for charts and metrics until the frontend report shape is stable enough to justify backend schema changes.

