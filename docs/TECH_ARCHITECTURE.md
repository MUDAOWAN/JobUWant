# Technical Architecture

Purpose: record technical stack choices, system architecture, runtime
environment, data flow, storage choices, model/API usage, cost controls, and
testing strategy.

Status: first MVP technical direction selected for planning. No business code,
dependency installation, framework initialization, database creation, or Git
operation has been approved yet.

## First MVP Technical Direction

- UI: Streamlit.
- Main language: Python.
- Application shape: local localhost web pilot tool.
- Initial backend shape: Python modules called by the Streamlit app; do not
  split a separate API service in the first version unless the implementation
  proves it is needed.
- Database: SQLite.
- Execution mode: synchronous execution in the first version.
- Later execution mode: task queue or background job flow when long-running
  updates, resumable tasks, or multi-step progress management become necessary.

This stack is selected for fast local validation. It should test whether the
JobUWant product idea can produce useful Hangzhou SLAM campus-hiring analysis
before investing in a more complete public-web architecture.

## Why SQLite For The First MVP

SQLite is the first MVP storage choice because the product is local,
single-user, and needs low-maintenance persistence for:

- Company pool records
- Structured job records
- Query history
- Source metadata and update timestamps
- Incremental update fingerprints
- Token usage and estimated cost records

PostgreSQL remains a future option for public website deployment, multi-user
usage, stronger operational controls, or cloud hosting. DuckDB may be added
later as an analysis layer if reporting queries become more analytical.

## Confirmed Product Constraints For Technical Planning

- First product shape: localhost web pilot tool.
- First city: Hangzhou.
- First role: SLAM engineer / SLAM algorithm engineer.
- First hiring stage: campus autumn hiring, compatible with early hiring
  batches.
- First user: the project owner.
- Login is not required in the first version.
- Data storage for the first MVP is SQLite; future cloud database options can
  be evaluated if the product moves toward public website deployment.
- Cost and token visibility should be treated as a first-class product
  requirement.
- Incremental updates should avoid repeated processing of unchanged
  information.

## First MVP Module Plan

The first MVP should be implemented as small modules instead of one large app:

- Query configuration: fixed first-scope query parameters plus editable
  controls when needed.
- Company pool: maintain known and candidate Hangzhou SLAM-related companies.
- Source intake: record source metadata and discovered job/company items.
- Change detection: compute and compare content fingerprints to skip unchanged
  items.
- Structuring: extract company, role, city, hiring season, requirements,
  technical stack, source, timestamp, and confidence fields.
- Analysis: compute technical stack frequency, company-category differences,
  new-graduate requirements, and preparation suggestions.
- Report view: show opportunity overview, company categories, technical stack
  heatmap, comparisons, recommendations, and cost panel.
- Cost tracking: record model calls, input tokens, output tokens, estimated
  cost, cache hit rate, and saved tokens by processing stage.
- Export: support first-version report export, preferably Markdown or HTML
  before PDF.

## First MVP Harness Direction

Use a simple in-repo Python harness for the first MVP rather than a formal
external orchestration framework.

The harness should coordinate the workflow stages, persist intermediate state
in SQLite, enforce budget limits, and make the synchronous flow observable from
the Streamlit UI. It should not introduce a task queue, agent framework, or
workflow framework until the first MVP proves the flow.

Detailed harness research is recorded in `docs/SKILL_RESEARCH.md`.

## Information Intake Strategy

The first version should design a repeatable, budget-controlled information
intake process. It should not rely on unlimited ad hoc searching.

Detailed source discovery and job-description location rules live in
`docs/INFORMATION_INTAKE.md`.

Recommended process:

1. Build or update a candidate company pool for Hangzhou SLAM-related roles.
2. Discover public job or company information for the fixed query scope.
3. Save source metadata and a content fingerprint before model processing.
4. Skip items that were processed before and have not changed.
5. Process only new or changed items under the current query budget.
6. Extract structured fields and short summaries.
7. Assign confidence labels based on source clarity, recency, and field
   completeness.
8. Generate analysis and report views from structured records.

The user does not need to provide the initial company list. The system should
support a candidate pool that can be gradually built from public information
and later reviewed or corrected.

## Budget And Safety Constraints

The first MVP should include explicit query limits before any model-heavy
workflow runs:

- Maximum source items per query.
- Maximum new or changed items processed per query.
- Maximum model calls per query.
- Maximum input tokens and output tokens per query.
- Maximum estimated cost per query.
- Per-stage counters for intake, structuring, analysis, and report generation.
- Stop or pause behavior when the configured budget is reached.

Initial first-run target:

- Up to 20 candidate source records.
- Up to 10 new or changed records processed.
- Up to 10 model calls.
- About CNY 5 estimated cost for the first small-scale run.

The first run should measure actual token usage and estimated cost, then use
the result to refine later default limits.

## Model Usage Direction

The user expects to call the model through an API and mentioned `gpt-5.5` as the
desired model. Before implementation, verify the exact model identifier and
availability from official OpenAI API documentation or the user's API account.

Do not hard-code a model name until the implementation step confirms it.

## Technical Questions To Resolve Next

- Exact default query budget values.
- Specific public information intake methods and allowed source types.
- Whether a local vector store is needed in the first version.
- How to track model calls, token usage, estimated cost, cache hit rate, and
  saved tokens.
- Exact first-version report export format.
- When to introduce a task queue or background job layer.
- When repeated development patterns are stable enough to create a JobUWant
  Codex skill.
- When to upgrade from the simple Python harness to OpenAI Agents SDK,
  LangGraph, or another orchestration framework.

## To Be Decided

- Model/API usage
- Local development commands
- Test strategy
- Deployment target
