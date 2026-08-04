# JobUWant Web App UI Design Direction

Status: draft for user review on 2026-07-29.

Purpose: define the first formal UI direction before expanding the fixture-first Next.js pages.

## 1. Design Goal

JobUWant should feel like a clear workbench during task execution and a refined report reader at the end.

The first UI pass should optimize for:

- visible task progress
- clear stage ownership
- confident sample confirmation
- readable report input preview
- polished final report reading
- traceable data and artifacts

The product should not look like a landing page in the first screen. The first screen should be the actual task workspace.

## 2. Working Method From coding范式.md

The UI work follows these rules:

- Make system knowledge explicit before coding.
- Define page boundaries before adding components.
- Map each page to backend APIs and task state.
- Keep UI state derived from backend data.
- Implement in small steps.
- Verify each step with typecheck, build, API checks, and browser checks.
- Update docs when routes, contracts, page states, or workflow rules change.

For this phase, the required output before large UI implementation is this document plus the updated workflow record.

## 3. Skill Usage Plan

Skills should be used as phase tools, not as a replacement for project docs.

### 3.1 UI Direction Skill

Candidate names:

- ui-ux-pro-max
- frontend-design

Use when:

- refining the visual language
- deciding dashboard density
- designing the final report reading layout
- checking whether page hierarchy matches the product goal

Expected output:

- page layout principles
- component hierarchy
- spacing and information-density guidance
- report page reading pattern

Current decision:

- Do not install yet.
- First use this UI direction document as the project-specific design brief.
- Install one UI direction skill only before visual polish or if the next page design becomes unclear.

### 3.2 Next.js Implementation Skill

Candidate name:

- vercel-react-best-practices

Use when:

- route map is stable
- page components are split into reusable modules
- data loading pattern needs review
- frontend type organization needs review

Expected output:

- App Router implementation guidance
- React component boundary checks
- API client and state handling recommendations

Current decision:

- Use after the first set of task pages is implemented, not before.

### 3.3 UI Quality Review Skill

Candidate names:

- web-design-guidelines
- frontend-design-review

Use when:

- pages are visible in browser
- layout and content states exist
- responsive behavior needs checking

Expected output:

- UI quality checklist
- spacing, hierarchy, contrast, and responsive feedback
- page-level improvement notes

Current decision:

- Use after task detail, sample, report input, and final report pages exist.

### 3.4 Browser Testing Skill

Candidate name:

- webapp-testing

Use when:

- frontend and backend are both running locally
- major pages have been implemented
- browser screenshots and console checks are needed

Expected output:

- browser navigation checks
- page rendering verification
- API integration verification
- console error capture

Current decision:

- Use after the route set exists.
- Current manual smoke check is enough for the skeleton.

### 3.5 Catalog Reference

Reference catalog:

- ComposioHQ/awesome-claude-skills

Use when:

- looking for additional specialized skills later
- comparing available design, frontend, testing, and documentation workflows

Current decision:

- Treat as a discovery index only.
- Do not add it as a project dependency.

## 4. Harness Usage In This UI Phase

The UI should be driven by the task execution harness rather than hardcoded page assumptions.

In JobUWant, the harness means:

- task state
- stage state
- events
- selected sample state
- batch state
- artifact records
- validation results

The first fixture-first UI should display the same shape even before live long-running execution is connected.

UI rule:

- If a backend stage exists, show its status, timestamp, message, and artifact pointer.
- If a stage is pending, show the next expected action.
- If a stage has no fixture data, show an explicit empty state.
- If data loading fails, show a recoverable error state with a retry action.
- Do not let the frontend invent hidden task state.

## 5. Product Layout Direction

Overall style:

- professional SaaS workbench
- white content areas on a light neutral background
- restrained blue as primary action and navigation color
- green for completed state
- amber for incomplete or needs-review state
- red only for failed states
- compact text scale for operational pages
- more open reading layout for the final report

Avoid:

- marketing hero screen as the product entry
- decorative gradients as the main visual system
- nested cards
- oversized headings inside operational panels
- page text that explains obvious UI behavior
- layout that depends on long text fitting in one line

## 6. Route Structure

Recommended first routes:

- / redirects to /tasks or renders the task list workspace.
- /tasks shows all tasks and their latest status.
- /tasks/new creates a new analysis task.
- /tasks/[taskId] shows task overview and stage timeline.
- /tasks/[taskId]/sample shows scoring and sample confirmation.
- /tasks/[taskId]/structure shows AI structuring progress.
- /tasks/[taskId]/report-input shows report input preview.
- /tasks/[taskId]/report shows final report.

Fixture-first implementation can keep / as the task workspace temporarily, but the route structure above should guide the next page split.

## 7. Page Design

### 7.1 Task List

Goal:

- Let the user see existing analysis tasks and create a new one.

Primary data:

- GET /api/tasks

Core components:

- TaskShell
- TaskListTable
- TaskStatusBadge
- MetricStrip
- EmptyState

Display:

- task name
- city
- keyword
- job type
- status
- collected count
- selected sample count
- updated time
- report availability

Acceptance:

- both validated fixtures are visible
- task status is readable without opening detail
- empty state exists
- loading and failed states exist

### 7.2 Create Task

Goal:

- Create a persistent task record before running long stages.

Primary future API:

- POST /api/tasks

Core components:

- TaskCreateForm
- EstimatePanel
- FieldValidationMessage

Display:

- city
- job keyword
- job-seeking type
- expected job count
- AI structuring batch size
- notes
- estimated runtime placeholder

Acceptance:

- invalid input is blocked before submit
- backend validation errors are shown near the form
- created task navigates to task detail

### 7.3 Task Detail

Goal:

- Show where the task is in the analysis flow and what action is next.

Primary data:

- GET /api/tasks/[taskId]
- GET /api/tasks/[taskId]/events

Core components:

- StageTimeline
- NextActionPanel
- ProgressLog
- ArtifactList
- MetricStrip

Display:

- task summary
- stage timeline
- current status
- latest events
- artifact paths
- next action

Acceptance:

- every stage has a visible state
- completed fixture tasks show all produced artifacts
- refresh does not lose selected task context

### 7.4 Sample Confirmation

Goal:

- Let the user review scored jobs and confirm the analysis sample.

Primary data:

- GET /api/tasks/[taskId]
- GET /api/tasks/[taskId]/jobs

Future write API:

- POST /api/tasks/[taskId]/sample

Core components:

- JobSelectionTable
- JobFilterBar
- MatchStatusBadge
- OriginalTextDrawer
- SelectionSummary

Display:

- selected checkbox
- match status
- match score
- role intent
- company
- title
- city
- salary
- experience
- education
- description length
- reasons

Acceptance:

- table supports selected-only view
- long text opens outside the table row
- selection summary is always visible
- empty filter result is clear

### 7.5 AI Structuring Progress

Goal:

- Make long-running structured extraction visible and recoverable.

Primary future APIs:

- POST /api/tasks/[taskId]/structure
- GET /api/tasks/[taskId]/structure
- POST /api/tasks/[taskId]/structure/batches/[batchId]/retry

Core components:

- BatchRunList
- TokenUsageSummary
- StageProgressBar
- ProgressLog
- RetryButton

Display:

- selected job count
- batch size
- total batch count
- current batch
- per-batch status
- model name
- token usage
- elapsed time
- error message

Acceptance:

- running status is visible without page reload
- failed batch can be identified
- retry action is scoped to one batch
- completed batches remain visible

### 7.6 Report Input Preview

Goal:

- Let the user inspect the compact report input before final report generation.

Primary data:

- GET /api/tasks/[taskId]/report-input

Future write API:

- POST /api/tasks/[taskId]/report

Core components:

- ReportInputPreview
- TopTermsChart
- DistributionChart
- JsonViewer
- EvidenceQualityPanel

Display:

- query summary
- sample summary
- technical terms top 15
- salary summary
- evidence quality
- estimated prompt tokens
- raw JSON viewer

Acceptance:

- JSON is readable without overwhelming the page
- charts are useful but not decorative
- user can return to sample confirmation
- final report action is clearly separated from preview

### 7.7 Final Report

Goal:

- Present final job-market conclusions and action advice in a refined reading layout.

Primary data:

- GET /api/tasks/[taskId]/report

Core components:

- FinalReportHeader
- ReportSectionNav
- MarketProfileSection
- TechnicalStackSection
- SalarySection
- RequirementSection
- ActionPlanSection
- EvidenceReference
- ExportButton

Display:

- report title
- audience summary
- market profile
- role clusters
- technical stack
- salary
- experience and education requirements
- job-search action plan
- caveats
- evidence references

Acceptance:

- report is readable without opening raw JSON
- sections have a stable order
- evidence references are visible
- export action exists
- mobile layout preserves reading order

## 8. Component Boundaries

Recommended directory shape:

```text
webapp/frontend/src/
  app/
    tasks/
    tasks/[taskId]/
    tasks/[taskId]/sample/
    tasks/[taskId]/structure/
    tasks/[taskId]/report-input/
    tasks/[taskId]/report/
  features/
    tasks/
    jobs/
    reports/
  components/
    ui/
    charts/
    layout/
  lib/
    api.ts
    format.ts
```

Rules:

- app routes should compose feature components.
- feature components own page-specific behavior.
- shared UI components should stay small and presentational.
- API functions should stay in lib/api.ts until the client grows enough to split.
- Do not duplicate backend status rules in multiple components.

## 9. State And Error Design

Every page should define these states:

- loading
- loaded
- empty
- failed
- pending stage
- running stage
- completed stage

Error display:

- show a short user-facing message
- include retry for read requests
- keep the page shell visible if possible
- do not hide already loaded task context

## 10. Development Order

Recommended next implementation order:

1. Split the current home page into /tasks and /tasks/[taskId].
2. Add task detail route with stage timeline and events.
3. Add sample confirmation route using GET /api/tasks/[taskId]/jobs.
4. Add report input preview route.
5. Add final report route.
6. Run UI quality review with web-design-guidelines or frontend-design-review.
7. Run browser verification with webapp-testing.
8. Only then connect live task execution APIs.

## 11. Verification Checklist

Before accepting the UI foundation:

- npm run typecheck passes.
- npm run build passes.
- backend health returns HTTP 200.
- frontend root returns HTTP 200.
- both fixture tasks are visible.
- task switching works.
- task detail data matches backend response.
- sample table can show selected-only rows.
- report input preview opens for both fixtures.
- final report opens for both fixtures.
- no console errors during normal navigation.

## 12. User Decisions

Confirmed on 2026-07-29:

- The first visible route should redirect from / to /tasks.
- The final report should prioritize article-like reading with supporting visualization charts.
- The sample confirmation page should allow selecting and deselecting jobs in the first Web App workflow.
- UI labels should be fully Chinese, while internal API values can remain normalized English values.