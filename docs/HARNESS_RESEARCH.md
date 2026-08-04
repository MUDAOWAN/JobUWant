# Harness Research

Purpose: summarize current agent workflow, harness, and skill-based workflow research for JobUWant, and record why the current MVP should stay with a simple in-repo Python harness.

Status: created on 2026-06-30 after Phase 1 candidate-company discovery was validated.

## JobUWant Context

JobUWant is still validating the information pipeline, not scaling a mature production workflow. The current MVP stack is Streamlit for local input, review, and display; Python modules for provider calls, workflow control, parsing, and persistence; SQLite for local state, source evidence, job records, and usage logs; and OpenAI web search behind a provider boundary for candidate-company discovery.

Phase 1 has been validated with real Hangzhou / SLAM-related candidate companies. Phase 2 should collect concrete job details, preserve original job description text, parse structured fields, and save evidence.

## Current Recommendation

Continue with a simple in-repo Python harness during MVP Phase 2 and Phase 3.

Reasons:

- The workflow is still changing quickly.
- The project has one local user and one Streamlit UI.
- The main risk is data quality: source trust, original job text preservation, parsing accuracy, and human review.
- SQLite and synchronous execution are enough for 1-10 companies and 10-20 job records.
- Adding a formal workflow framework now would increase surface area before the stable stages and state model are known.

The harness should still borrow ideas from mature frameworks: typed stage inputs and outputs, explicit state transitions, persistence, cost guards, source quality labels, and human confirmation checkpoints.

## OpenAI Agents SDK

OpenAI Agents SDK is useful for agentic applications that need model-driven tool use, handoffs between agents, guardrails, sessions, streaming, and traces. It provides a higher-level runtime around model calls and tools.

Useful ideas for JobUWant:

- Treat each workflow stage as an observable run.
- Keep tool boundaries explicit.
- Add human confirmation before expensive or low-confidence stages.
- Preserve trace-like metadata: stage, model, tokens, cost, input summary, output shape, and errors.

Current MVP decision:

- Do not introduce Agents SDK yet.
- Keep direct provider calls and parser calls inside the Python harness.
- Reconsider after Phase 2 and Phase 3 reveal repeated multi-step patterns that need sessions, handoffs, or richer traces.

## LangGraph

LangGraph is designed for stateful, durable, long-running agent workflows. Its strengths include graph-shaped control flow, persistence, recovery, human-in-the-loop execution, and memory.

Useful ideas for JobUWant:

- Model workflow state explicitly.
- Separate nodes such as company discovery, job lead search, job text intake, parsing, review, save, and report generation.
- Store checkpoints so a partially completed run can continue later.
- Make human review a first-class node instead of an afterthought.

Current MVP decision:

- Do not introduce LangGraph yet.
- Represent states with simple Python functions, dataclasses, and SQLite rows.
- Keep future migration easy by avoiding Streamlit-owned business logic and by keeping provider, parser, persistence, and report generation separate.

Reconsider LangGraph when JobUWant needs resumable background runs, branching workflows, concurrent company processing, complex retry rules, or multiple human review points per run.

## LlamaIndex Workflows

LlamaIndex Workflows use event-driven steps with typed inputs and outputs. The workflow shape can be validated, and intermediate events can be streamed.

Useful ideas for JobUWant:

- Define simple stage payloads such as `CandidateCompany`, `JobLead`, `JobDetailInput`, `ParsedJobDetail`, and `ReviewedJobDetail`.
- Validate that each stage produces the fields the next stage expects.
- Keep parsing results separate from source evidence.

Current MVP decision:

- Do not introduce LlamaIndex Workflows yet.
- Borrow the typed event idea in local dataclasses or Pydantic models.

## PydanticAI

PydanticAI emphasizes typed dependencies, tool definitions, and validated structured outputs with Pydantic models.

Useful ideas for JobUWant:

- Use Pydantic or equivalent validation for parsed job detail fields.
- Validate required fields before saving: company name, job title, source type, source confidence, raw text, and parse confidence.
- Treat invalid structured extraction as a review item instead of final data.

Current MVP decision:

- Pydantic itself is worth considering for Phase 2 structured validation.
- PydanticAI as a framework is not necessary yet.

## AutoGen

AutoGen supports multi-agent conversations and event-driven agent systems. It is useful when multiple agent roles need to collaborate or when a team wants a more formal agent runtime.

Useful ideas for JobUWant:

- Split responsibilities conceptually: lead finder, text collector, parser, source quality reviewer, report writer.

Current MVP decision:

- Do not introduce AutoGen.
- JobUWant currently needs a deterministic small workflow, not a multi-agent conversation.

## CrewAI

CrewAI provides crews and flows for role-based collaboration and structured processes.

Useful ideas for JobUWant:

- Define role-like skills and keep their inputs and outputs clear.
- Use flows for deterministic business processes.

Current MVP decision:

- Do not introduce CrewAI.
- Current work is better served by normal Python modules and explicit review screens.

## DSPy

DSPy is useful when prompts and model pipelines need systematic optimization against examples and metrics.

Useful ideas for JobUWant:

- Later, optimize job-description parsing prompts using saved raw text and manually reviewed structured outputs.
- Build small evaluation sets from confirmed job records.

Current MVP decision:

- Do not introduce DSPy during Phase 2.
- Reconsider after 20-50 reviewed job descriptions exist.

## Prefect, Dagster, And Temporal

These are general workflow orchestration systems. Their shared lessons are:

- Stages should be explicit.
- Runs should be observable.
- State and retry behavior should be recorded.
- Long-running jobs need durable execution and recovery.
- Human approval can be modeled as a workflow pause.

Current MVP decision:

- Do not introduce these frameworks.
- Keep their ideas in mind for future background jobs, recurring updates, and larger data refresh runs.

Reconsider only when local synchronous execution becomes a bottleneck.

## Simple In-Repo Python Harness

Strengths:

- Minimal dependencies.
- Easy to inspect and change.
- Fits Streamlit and SQLite.
- Good enough for one user, small data volume, and synchronous MVP validation.
- Keeps business logic near the codebase while still separate from the UI.

Weaknesses:

- Resumability, tracing, retries, and branching must be implemented manually.
- The harness can become messy if stage boundaries are not documented.
- It needs discipline around validation and source evidence.

Required discipline:

- Keep Streamlit thin.
- Keep provider calls behind provider classes.
- Keep parsing behind parser functions or classes.
- Store raw evidence before trusting summaries.
- Save usage and cost by stage.
- Add human confirmation before deeper processing.

## JobUWant Design Implications

Current MVP should implement:

- `company_discovery`: already validated.
- `job_lead_search`: find possible job pages or leads for confirmed companies.
- `job_text_intake`: accept fetched text or user-pasted original job text.
- `job_detail_parse`: extract structured fields from raw text.
- `source_quality_score`: label official pages, recruitment platforms, search summaries, user-provided text, and model summaries.
- `human_review`: confirm relevance and parsed fields before final save.
- `usage_guard`: limit model calls, text length, companies per run, and repeated parsing.

Future framework migration should remain possible by keeping the following boundaries:

- Provider interface: search and source retrieval.
- Parser interface: raw text to structured fields.
- Persistence interface: SQLite writes and reads.
- Workflow state: explicit stage names and status fields.
- Review interface: pending, confirmed, rejected, needs_edit.
- Usage logging: stage, model, tokens, cost, duration, error.

## When To Reconsider A Larger Framework

Consider Agents SDK, LangGraph, or another framework when at least two of these signals appear:

- One run processes dozens of companies or hundreds of pages.
- Runs need to pause and resume across sessions.
- Multiple branches or retries make the Python harness hard to reason about.
- Human review appears in several stages and needs durable state.
- Background tasks become necessary.
- The project needs detailed traces for debugging cost or quality problems.
- There is a stable set of repeated skills worth encoding.
- Multiple users or public deployment becomes a real target.

Until then, the simple in-repo Python harness remains the right default.
