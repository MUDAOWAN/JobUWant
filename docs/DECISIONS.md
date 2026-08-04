# Decision Log

This file records important project decisions and the reason behind them.

## 2026-06-27: Project Name

Decision: Use `JobUWant` as the project name.

Reason: The user selected this name.

## 2026-06-27: Development Environment

Decision: Use WSL2 Ubuntu for formal development.

Reason: The project may later become a web application, and WSL2 is closer to a
typical Linux deployment environment than native Windows development.

## 2026-06-27: Project Path

Decision: Use `/home/votally/projects/JobUWant` as the formal project path.

Reason: Keeping the project inside the WSL filesystem should provide better
behavior for dependencies, file watching, Git, and local services.

## 2026-06-27: Git Repository

Decision: Initialize Git with branch `main` and set remote to
`git@github.com:MUDAOWAN/JobUWant.git`.

Reason: The user wants to maintain the project with Git and GitHub.

## 2026-06-27: Codex CLI Access Pattern

Decision: The user can use Windows Codex CLI with the WSL project through the
UNC path `\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant`.

Reason: Windows Codex CLI cannot use the Linux path
`/home/votally/projects/JobUWant` directly, but Windows can access WSL files
through `\\wsl.localhost\Ubuntu\...`. Project commands should still prefer WSL
execution where possible.

## 2026-06-27: Documentation Expansion

Decision: Add a Codex CLI handoff document and create placeholders for product,
technical, roadmap, data, and skill research documents.

Reason: New Codex CLI conversations need a fast, reliable way to understand the
project state, document roles, current constraints, and next recommended work.

## 2026-06-27: First MVP Positioning

Decision: The first MVP is a personal localhost web pilot tool for Hangzhou
SLAM engineer / SLAM algorithm engineer opportunities in campus autumn hiring,
compatible with early hiring batches.

Reason: A narrow first scope can validate the product report, data strategy,
technical approach, and cost controls before expanding to other roles, cities,
or a public website.

## 2026-06-27: First MVP User And Login Scope

Decision: The first MVP target user is the project owner, and the first version
does not need user login.

Reason: The project is starting as a personal local tool. Login and account
management would add complexity before the core analysis workflow is validated.

## 2026-06-27: First MVP Product Priorities

Decision: Prioritize technical stack analysis, company-category requirement
comparison, Hangzhou company opportunity mapping, new-graduate capability
summary, incremental updates, and cost/token visibility.

Reason: These capabilities directly support the first target use case and help
control repeated model-call cost during iterative queries.

## 2026-06-27: First MVP Technical Stack Direction

Decision: Plan the first MVP with Streamlit, Python, SQLite, and synchronous
execution.

Reason: This stack is suitable for a personal localhost pilot and should allow
fast validation of the product idea with low operational complexity. SQLite is
appropriate for local records such as company pool data, structured job
records, query history, source metadata, and token/cost records.

## 2026-06-27: Later Task Execution Direction

Decision: Start with synchronous execution in the first version, but keep task
queue or background job execution as a later improvement.

Reason: Synchronous execution is simpler for the first MVP. A task queue becomes
more valuable when the workflow has long-running updates, resumable tasks,
progress tracking, or concurrent jobs.

## 2026-06-27: Skill Timing

Decision: Do not create a JobUWant-specific Codex skill yet. Reconsider after
the technical stack and repeated development workflow become stable.

Reason: Creating a skill too early could freeze unstable process assumptions.
Skills can later help enforce project workflow, front-end conventions, module
boundaries, token budget rules, and documentation updates.

## 2026-06-27: Company Pool Source

Decision: The first MVP should not require the user to provide the initial
company list. The product should support a candidate company pool that can be
gradually built from public information and later reviewed or corrected.

Reason: This keeps the product useful without requiring manual upfront data
collection from the user.

## 2026-06-27: Information Intake Direction

Decision: Use a layered information intake design for the first MVP: recruitment
platforms and public pages provide leads, company official hiring pages are
preferred for high-confidence job descriptions, and every record must keep
source evidence, confidence labels, and update metadata.

Reason: The product needs to know which Hangzhou SLAM companies exist and where
their relevant job descriptions are without requiring the user to provide an
initial company list. Official company pages provide stronger evidence when
platform pages lack detailed skill requirements.

## 2026-06-27: Automated Intake And Candidate Confirmation

Decision: Prefer a fully automated first-version information intake chain, but
include a candidate-company confirmation step before spending the larger
job-description processing budget.

Reason: The product should discover companies without requiring user-provided
lists, while still giving the user control over whether the discovered
candidate set is worth deeper processing.

## 2026-06-27: First Search Entry Candidates

Decision: Compare OpenAI web search and Tavily first as candidate source
discovery methods. Keep manual URL entry as a fallback, not the preferred first
workflow.

Reason: The product needs programmable search results for automated discovery.
The first comparison should focus on which method better finds Chinese hiring
platform pages and official company hiring pages for Hangzhou SLAM roles.

## 2026-06-27: First Query Budget Target

Decision: Use an initial first-run budget target of about CNY 5, with 20
candidate source records, 10 new or changed records processed, and 10 model
calls.

Reason: The first run should be small enough to avoid unexpected cost while
still producing enough data to measure real token usage and refine future
limits.

## 2026-06-27: First MVP Harness Direction

Decision: Use a simple in-repo Python harness for the first MVP instead of a
formal external orchestration framework.

Reason: The first MVP needs a controllable workflow layer for search,
candidate confirmation, job-description processing, SQLite persistence, HTML
report generation, and token/cost limits. A lightweight project-local harness
is enough for this stage and avoids adding framework complexity before the
workflow is validated.


## 2026-06-28: Continue Streamlit Through MVP Validation

Decision: Continue building JobUWant's MVP in Streamlit, Python, SQLite,
synchronous execution, and the in-repo Python harness instead of switching now
to a full frontend/backend stack.

Reason: Candidate-company discovery has been validated, but the larger
uncertainty is still the information pipeline: whether the app can collect full
job-description text, preserve source evidence, and generate useful multi-job
analysis. A larger web stack would add complexity before those workflow risks
are resolved.

## 2026-06-28: MVP Phase 2 And Phase 3 Direction

Decision: Treat the validated OpenAI web-search candidate-company discovery as
MVP Phase 1. Next implement Phase 2 job-detail collection, then Phase 3
multi-job analysis.

Reason: The current app can find real candidate companies such as Hikvision and
Unitree, but it does not yet preserve full job descriptions exactly as shown on
hiring pages. The target product needs company-specific role records with
original job text before it can reliably summarize common technical stacks and
skill priorities across 10-20 companies.

## 2026-06-30: Keep Simple Harness For Phase 2

Decision: Continue using Streamlit, Python, SQLite, synchronous execution, and the simple in-repo Python harness for MVP Phase 2. Do not introduce OpenAI Agents SDK, LangGraph, AutoGen, CrewAI, or another multi-agent/workflow framework at this stage.

Reason: Phase 1 has validated real candidate-company discovery, but Phase 2 is still validating the information pipeline: job lead discovery, original job-description preservation, structured parsing, source confidence, human review, and SQLite persistence. A larger workflow framework would add complexity before the stable stage boundaries are known.

## 2026-06-30: Phase 2 Semi-Manual Job Detail Flow

Decision: Implement Phase 2 first as a semi-manual workflow: candidate job leads, user confirmation, user-pasted original job text as fallback, structured parsing, human review, and SQLite save.

Reason: Job detail pages can vary by official site, campus site, recruitment platform, and search result. Preserving the original job text is more important than early full automation. Starting with 1-2 companies gives the project a small, verifiable path before expanding to about 10 companies.

## 2026-06-30: Evidence Before Summary

Decision: Model summaries are auxiliary only. Job records must preserve raw job description text, original URL or source note, source type, source confidence, parse confidence, collection time, and update time.

Reason: Phase 3 analysis depends on auditable job evidence. Search snippets and model summaries can help find leads, but they are not sufficient final facts.

## 2026-07-01: Phase 2 Automation-First MVP

Decision: Phase 2 should be automation-first. The first implementation should automatically search job leads for a small company batch, try to read public job-detail page text, parse structured fields with model assistance and validation, save raw evidence and parsed fields to SQLite, and display results in Streamlit.

Reason: The user prefers an automated workflow. To keep the first run controllable, the initial UI limits Phase 2 to 1-2 companies and up to 3 job leads per company. Human text input remains a fallback path for pages whose full text cannot be read automatically, but it is not the primary flow.

Decision: Add Pydantic as the structured validation dependency for Phase 2.

Reason: Job-detail extraction requires predictable fields and validation before persistence. Pydantic is lightweight enough for the current Streamlit/Python MVP and keeps a future migration boundary clear.

## 2026-07-01: Official Hiring Pages Only

Decision: Phase 1 candidate-company discovery and Phase 2 job-detail collection should only accept official company hiring pages, official campus hiring pages, or clearly official company hiring systems. Third-party recruitment platforms, school employment boards, copied job posts, content aggregators, and generic search result pages should be filtered out.

Reason: The target product should analyze authoritative job evidence from company-owned or company-operated hiring sources. Third-party pages can be useful leads later, but they should not be treated as final evidence in the current MVP.

## 2026-07-01: Official Domain Verifier

Decision: Move from blocklist-first filtering to an official-domain verifier for Phase 1 and Phase 2. Candidate companies should store `official_domain`, `official_domain_verified`, and `verification_notes`. Phase 2 should process only verified official-domain companies and same-domain official job leads.

Reason: A blocklist can reject known third-party recruitment sites, but unknown third-party sites can still slip through. The MVP needs company-owned or clearly company-operated hiring evidence before saving job details as final samples.

## 2026-07-01: Taxonomy Extraction Future Work

Decision: Keep the current SLAM keyword extraction as a Phase 2 MVP heuristic, but plan a taxonomy module before expanding to arbitrary roles such as Agent, backend, frontend, or data analysis.

Reason: A single fixed keyword list does not generalize well. Future extraction should identify the role family, load role-specific and common software-engineering taxonomies, normalize synonyms, classify skills, and preserve evidence from raw job text.
## Pending Decisions

- Final report page structure
- Data source strategy
- Cost control plan
- Deployment target
- Exact default query budget values
- First report export format
- Whether a local vector store is needed in the first MVP
- Exact timing for introducing task queue or background job execution
- Whether OpenAI web search or Tavily performs better for the first source
  discovery test
- Exact job-detail fetch strategy for recruitment platform and official company pages
- When to upgrade from the simple Python harness to OpenAI Agents SDK,
  LangGraph, or another orchestration framework




