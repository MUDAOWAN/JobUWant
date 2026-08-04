# Agent Process

Purpose: record how Codex agents should collaborate on JobUWant, what has been
confirmed during planning, and how execution should be constrained.

Status: initial process record created on 2026-06-27.

## Collaboration Rules

- Read `docs/CODEX_CLI_HANDOFF.md` first in new Codex CLI conversations.
- Follow `docs/AGENT_RULES.md` for project collaboration rules.
- Explain planned file, Git, environment, dependency, or framework changes
  before making them.
- Do not write business code, install dependencies, initialize a framework,
  create a database, commit, or push without explicit approval.
- Keep meaningful decisions in `docs/DECISIONS.md`.
- Keep completed work and next steps in `docs/WORKLOG.md`.
- Keep `docs/SESSION_HANDOFF.md` current as the project state changes.

## Confirmed Planning State

- First MVP product shape: localhost web pilot tool.
- First MVP city: Hangzhou.
- First MVP role: SLAM engineer / SLAM algorithm engineer.
- First MVP hiring stage: campus autumn hiring, compatible with early hiring
  batches.
- First MVP target user: the project owner.
- First MVP login: not required.
- First MVP technical direction: Streamlit, Python, SQLite, synchronous
  execution.
- Later execution direction: task queue or background job flow when workflow
  length, resumability, or progress tracking requires it.
- JobUWant-specific Codex skill: defer until repeated development workflow is
  stable.

## Agent Execution Pattern

When implementing is approved, agents should work in small modules:

1. Read the current handoff and relevant planning documents.
2. State the intended change and affected files.
3. Make the smallest useful change.
4. Verify the result with an appropriate local check.
5. Summarize changed files and behavior.
6. Update decision, worklog, and handoff documents when the change affects
   project direction or next steps.

## Information Intake Guardrails

The information intake workflow should be controlled before model-heavy
processing starts:

- Set a source item limit.
- Set a new-or-changed item processing limit.
- Set a model call limit.
- Set input and output token limits.
- Set an estimated cost limit.
- Track cost by processing stage.
- Skip unchanged items through source metadata and content fingerprints.
- Pause or request confirmation before expanding beyond configured limits.
- Follow `docs/INFORMATION_INTAKE.md` for company discovery, job-description
  location, confidence labels, and incremental update behavior.
- Use the first-run target of 20 candidate sources, 10 new or changed records,
  10 model calls, and about CNY 5 estimated cost unless the user changes it.
- Verify exact OpenAI model identifiers before hard-coding any model name.

## Skill Usage Direction

Skills can later help with:

- Project-specific development workflow.
- Front-end page and component conventions.
- Back-end module boundaries and data field conventions.
- Model API usage limits, token budget rules, and cost reporting.
- Required documentation updates after implementation work.

Do not create a JobUWant-specific skill until the project has stable repeated
patterns worth encoding.

## Harness Direction

Use a simple in-repo Python harness for the first MVP. The harness should
coordinate workflow stages, persist intermediate state, enforce token and cost
limits, and expose progress to the Streamlit UI.

Do not introduce OpenAI Agents SDK, LangGraph, or another workflow framework
until the first synchronous MVP proves the actual information-intake flow.
## File Operation Troubleshooting

When file reads or documentation updates fail in Codex CLI, treat it as an
environment question first and avoid changing unrelated files.

Confirmed approach:

- Use WSL read-only commands for inspection when direct Windows UNC file access
  is unreliable.
- Keep updates narrow and name the exact documents before writing.
- If the normal patch path cannot access the workspace, use an approved
  constrained edit for documentation-only changes.
- After any fallback edit, verify the inserted heading or key lines with WSL
  read-only commands.
- Record recurring environment issues in `docs/WORKLOG.md` and quick-start
  guidance in `docs/SESSION_HANDOFF.md`.

## JobUWant Harness And Skill Workflow Design

Status: updated on 2026-06-30 after MVP Phase 1 candidate-company discovery was validated with the OpenAI web-search provider.

### Current MVP Architecture Decision

Continue with Streamlit, Python, SQLite, synchronous execution, and the simple in-repo Python harness.

Reasons:

- Phase 1 has validated candidate-company discovery, but Phase 2 still needs to validate job-detail collection and original job-description preservation.
- The current user is still the project owner running a local MVP.
- The main uncertainty is data quality and workflow shape, not frontend or orchestration scale.
- A local harness is easier to inspect and change while source strategy, parsing fields, review points, and cost controls are still changing.
- A formal framework such as OpenAI Agents SDK or LangGraph can be introduced later if state, branching, recovery, or multi-agent handoffs become real needs.

### Responsibility Boundaries

Streamlit UI:

- Collect role, city, hiring stage, and candidate status inputs.
- Show candidate companies, job leads, parsed job details, raw evidence, and usage counters.
- Provide user confirmation controls.
- Provide manual fallback inputs, especially pasted job-description text.
- Avoid owning provider calls, parsing logic, source scoring, or database details.

Python harness:

- Coordinate stages and enforce workflow order.
- Call providers and parsers.
- Persist intermediate and final state.
- Enforce source limits, model-call limits, text-length limits, and estimated cost limits.
- Record usage by stage.
- Return display-ready results to Streamlit without making Streamlit the workflow owner.

Providers:

- Search or retrieve external evidence.
- Return normalized source or lead objects.
- Report usage metadata when a provider calls a model or paid service.
- Avoid deciding final business truth. Provider summaries are leads, not final facts.

SQLite:

- Store candidate sources, candidate companies, job leads, job details, parsed fields, raw job text, source metadata, review status, and usage logs.
- Preserve evidence and timestamps so later analysis can be audited.
- Support incremental updates through source URLs, content fingerprints, and last-seen timestamps.

Model calls:

- Assist with search, job-detail parsing, keyword extraction, and later report generation.
- Produce structured outputs that are validated before saving.
- Never replace raw source evidence.
- Model summaries may guide review, but cannot be treated as final facts without original text, source, time, and confidence metadata.

Human review:

- Confirm which candidate companies enter Phase 2.
- Confirm whether a job lead is relevant.
- Provide pasted original job text when a page cannot be fetched reliably.
- Review parsed fields before final save.
- Correct source type or confidence when automatic scoring is wrong.

### MVP Phase Workflows

Phase 1: Candidate Company Discovery

- Input: role, city, hiring stage, candidate status, budget.
- Provider: sample data or OpenAI web search.
- Output: candidate sources and candidate companies.
- State: saved in `candidate_sources`, `candidate_companies`, and usage logs.
- Status: validated with real Hangzhou / SLAM-related companies.

Phase 2: Job Detail Collection

- Input: confirmed candidate companies from Phase 1.
- Generate job-search intent for each company.
- Search for candidate job leads.
- Let the user confirm relevant leads.
- Fetch public page text when practical, or accept pasted original job text as the first reliable fallback.
- Save full raw job-description text.
- Parse structured fields: company name, job title, city, recruitment stage, responsibilities, requirements, technical keywords, original URL, source type, source confidence, parse confidence, collected time, and updated time.
- Let the user confirm or correct parsed fields.
- Save reviewed job details to SQLite.

Phase 3: Multi-Job Analysis And Report

- Input: 10-20 reviewed job details with raw text and structured fields.
- Extract technical keyword frequency and priority.
- Cluster responsibilities and requirements.
- Compare city, company, and direction differences.
- Generate new-graduate preparation suggestions and resume improvement suggestions.
- Render an HTML report and save intermediate analysis results.

### Skill Ideas

Current MVP skills implemented as normal Python modules or functions:

- `company_discovery_skill`: role/city/stage to candidate companies.
- `job_detail_collection_skill`: company to job leads and raw text intake.
- `jd_parser_skill`: raw job text to structured fields.
- `source_quality_scoring_skill`: source type and confidence labels.
- `cost_guard_skill`: budget and usage checks.
- `human_review_skill`: Streamlit confirmation and correction controls.

Future skills:

- `salary_normalization_skill`: normalize compensation text when salary data is available.
- `skill_taxonomy_skill`: group technologies into robotics, SLAM, C++, ROS, mapping, localization, perception, and related categories.
- `report_generation_skill`: generate final report sections from reviewed job records.
- `session_handoff_skill`: summarize current project state for future agent sessions.
- `document_update_skill`: update worklog, decisions, roadmap, and handoff documents after approved changes.

### Future Framework Migration Boundaries

Keep these boundaries stable so the project can later migrate to OpenAI Agents SDK, LangGraph, or another workflow framework:

- Provider interface: search and source retrieval return normalized records.
- Parser interface: raw text in, validated structured fields out.
- Persistence interface: SQLite reads and writes are isolated from UI code.
- Workflow stages: use explicit stage names and status fields.
- Human review: represent review state as data, not only button state.
- Usage events: record stage, model, calls, tokens, estimated cost, timestamps, and errors.

Migration should be considered only after the simple harness becomes difficult to manage because of resumable runs, branching, background jobs, concurrent company processing, or multiple durable human confirmation points.
