# Skill Research

Purpose: record research about Codex skills, project-specific agent rules,
harness design, workflow support, and long-term agent collaboration patterns.

Status: initial skill and harness research recorded on 2026-06-27.

## Skill Direction

JobUWant should not create a project-specific Codex skill yet.

Reason:

- The product workflow is still changing.
- The technical stack is only just selected for planning.
- A skill is most useful after repeated development patterns are stable.
- Creating a skill too early could freeze assumptions that may change during
  the first MVP.

Possible later skill contents:

- Required project read order.
- Documentation update rules.
- Streamlit page conventions.
- SQLite schema and migration conventions.
- Information intake and cost-budget rules.
- Report generation and HTML export conventions.

## What Harness Means In This Project

In this project, a harness means a controlled execution layer around model and
tool usage. It is not just one library. It can include:

- Workflow orchestration.
- Search and source-intake steps.
- Tool calling.
- Budget and token accounting.
- Intermediate state persistence.
- Human confirmation checkpoints.
- Tracing and debug records.
- Evaluation cases for repeated workflows.

For JobUWant, the harness question is: should the MVP use a formal orchestration
framework, or should it begin with simple Python modules and add a framework
later?

## Harness Options

### Simple In-Repo Python Harness

Description: build a lightweight project-local workflow runner with plain
Python modules.

Potential responsibilities:

- Run fixed stages: search, candidate extraction, candidate confirmation,
  job-description lookup, structuring, analysis, report generation.
- Record per-stage status in SQLite.
- Enforce source count, model call, token, and cost limits.
- Store intermediate records for repeatability.
- Provide logs for debugging.

Pros:

- Lowest complexity for the first MVP.
- Works well with Streamlit and SQLite.
- Easy to adapt as the product changes.
- Avoids locking into a framework before the workflow is stable.

Cons:

- We must design stage state, retries, and tracing ourselves.
- Long-running task support will be limited until a later task queue is added.

Recommendation: use this for the first MVP.

### OpenAI Agents SDK

Description: OpenAI's agent framework for building workflows where models can
use tools, hand off work, apply guardrails, and produce traces.

Potential fit:

- Multi-step information-intake flows.
- Tool-based search and source processing.
- Later tracing and debugging of model decisions.
- Later migration from simple modules to more structured agent workflows.

Pros:

- Official OpenAI ecosystem.
- Built for model tool use and agent workflows.
- Tracing can help debug multi-step behavior.

Cons:

- More framework complexity than the first MVP requires.
- The first MVP may not need multi-agent handoffs.
- Adds architectural decisions before the core workflow is validated.

Recommendation: evaluate after the first synchronous MVP proves the workflow.

### LangGraph

Description: a graph-based orchestration framework for controllable, stateful
agent and workflow execution.

Potential fit:

- Explicit workflow graph.
- Human confirmation checkpoints.
- Persistent state and resumable flows.
- Later task-style execution with clearer state transitions.

Pros:

- Strong fit for multi-step workflows with checkpoints.
- Better for long-running and stateful pipelines than ad hoc function calls.

Cons:

- Adds another framework and learning curve.
- Overkill before the first information-intake flow is validated.

Recommendation: keep as the likely later option if the workflow becomes
complex.

### LlamaIndex Workflows / Haystack Pipelines / CrewAI Flows

Description: alternative orchestration and data-processing frameworks.

Potential fit:

- Search, extraction, and structured analysis pipelines.
- Knowledge-base or retrieval-heavy extensions.
- More formal workflow composition later.

Pros:

- Useful if JobUWant grows toward a larger information processing system.

Cons:

- Not necessary for the first local MVP.
- Adds dependency and design complexity before the core product is proven.

Recommendation: do not use in the first MVP.

### OpenAI Evals

Description: evaluation tooling for testing model outputs against expected
behavior.

Potential fit:

- Later check whether job-description structuring is accurate.
- Test whether confidence labels and skill extraction are consistent.
- Compare prompts or models on a fixed set of saved job descriptions.

Pros:

- Useful for quality control after the system has sample data.

Cons:

- Requires representative examples and expected outputs.
- Premature before the first dataset exists.

Recommendation: defer until the product has saved sample records.

## Recommended First MVP Harness Strategy

Use a simple in-repo Python harness first, not a formal external framework.

The first MVP harness should be a thin workflow layer with these stages:

1. Search candidate sources.
2. Extract candidate companies and roles.
3. Show candidate-company confirmation.
4. Locate job descriptions for confirmed companies.
5. Compute content fingerprints and skip unchanged records.
6. Structure new or changed records with the model.
7. Store records and cost usage in SQLite.
8. Generate the HTML report.

The harness must enforce:

- 20 candidate source records per first-run query.
- 10 new or changed records processed.
- 10 model calls.
- About CNY 5 estimated first-run cost target.
- Per-stage usage tracking.
- Stop or confirmation behavior when limits are reached.

## Later Harness Upgrade Signals

Consider OpenAI Agents SDK or LangGraph when one or more of these becomes true:

- The information-intake flow needs reliable resume and retry.
- Candidate confirmation becomes one of several human checkpoints.
- The product needs long-running background updates.
- The system needs stronger tracing of model tool use.
- Multiple specialized model workflows become necessary.
- The first MVP's plain Python harness becomes hard to maintain.

## References Checked

- OpenAI web search and Responses API documentation.
- OpenAI Agents SDK documentation.
- OpenAI Evals documentation.
- LangGraph documentation.
- Tavily, Exa, Brave Search, Google Programmable Search, and SerpAPI
  documentation for source discovery options.
