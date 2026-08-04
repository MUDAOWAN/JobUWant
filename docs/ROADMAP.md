# Roadmap

Purpose: track the phased plan from setup to MVP, testing, deployment, and
continued improvement.

Status: initial product roadmap recorded on 2026-06-27.

## Current High-Level Roadmap

1. Environment and project location setup
2. Documentation foundation
3. Product positioning
4. Product analysis and report structure design
5. Technical architecture analysis
6. Agent workflow and project maintenance research
7. MVP development
8. Testing and iteration
9. Deployment planning
10. Launch and continued improvement

## Near-Term Roadmap

### Phase 1: Documentation Foundation

Status: mostly complete.

- Confirm project path, Git setup, and collaboration rules.
- Maintain handoff, decision, and worklog documents.
- Keep business code blocked until product and technical planning are clearer.

### Phase 2: Product Positioning And MVP Scope

Status: in progress.

- Confirm first city: Hangzhou.
- Confirm first role: SLAM engineer / SLAM algorithm engineer.
- Confirm first hiring stage: campus autumn hiring, compatible with early
  hiring batches.
- Confirm first user: the project owner.
- Confirm first product shape: localhost web pilot tool.
- Confirm no login requirement for the first version.
- Define the report structure, structured fields, incremental update concept,
  and cost visibility requirements.

### Phase 3: Technical Stack Selection And MVP Module Design

Status: in progress.

- Record first MVP stack: Streamlit, Python, SQLite, synchronous execution.
- Keep task queue or background job flow as a later improvement.
- Design the first MVP modules before implementation.
- Define budget controls for information intake and model usage.
- Define a repeatable information update flow.
- Record detailed company discovery and job-description location design.
- Decide whether to test OpenAI web search or Tavily first for source
  discovery.
- Design the candidate-company confirmation step.
- Use a simple in-repo Python harness for the first MVP.
- Decide whether a local vector store is needed in the first version.
- Decide exact default query budget values.
- Decide first report export format.

### Phase 4: MVP Implementation

Status: in progress.

#### Phase 4.1: Candidate Company Discovery

Status: validated.

- Built query entry for the fixed first scope.
- Added local sample data provider.
- Added OpenAI web-search provider behind the Python harness.
- Added source selection in the Streamlit UI.
- Confirmed the real provider can return Hangzhou/SLAM-related candidate
  companies such as Hikvision and Unitree.
- Confirmed usage counters and estimated cost are visible.

#### Phase 4.2: Job Detail Collection

Status: next.

- Start with an automation-first but tightly limited flow: process 1-2 companies per run and keep human text input as a fallback when page text cannot be read automatically.
- For each confirmed candidate company/source, identify candidate job leads.
- Let the user confirm whether a job lead is relevant.
- Fetch public job-detail page text when practical, but keep pasted original
  job text as the first reliable fallback.
- Preserve the original job-description text, not only a model summary.
- Parse and store structured fields: company name, job title, city,
  recruitment stage, responsibilities, requirements, technical keywords,
  original URL, raw job text, source type, source confidence, parse confidence,
  collected time, and updated time.
- Write reviewed job details to SQLite.
- Distinguish high-confidence official hiring pages and campus pages from
  recruitment platform details, search summaries, user-provided text, and model
  summaries.
- First validate the end-to-end flow with 1-2 companies, then expand to about
  10 companies.

#### Phase 4.3: Multi-Job Analysis And Report

Status: after Phase 4.2.

- Analyze 10-20 reviewed job details with preserved raw descriptions.
- Summarize technical-stack frequency and priority.
- Cluster responsibilities and requirements.
- Compare company categories, cities, and role direction differences.
- Produce new-graduate preparation suggestions.
- Produce resume optimization suggestions based on recurring requirements.
- Generate HTML report output from stored job records.
- Save analysis results and intermediate summaries so report output can be
  reviewed and regenerated.

#### Technical Direction During MVP

- Continue with Streamlit, Python, SQLite, synchronous execution, and the
  in-repo Python harness.
- Do not switch to a full frontend/backend stack until job-detail collection
  and multi-job analysis are validated.
- Keep implementation incremental: complete and verify one module before
  expanding to the next.
### Phase 5: Iteration And Expansion

Status: future.

- Expand to more cities and roles.
- Add resume-based matching and capability gap analysis.
- Add company knowledge base.
- Add role alias normalization.
- Add report export and historical trend analysis.
- Evaluate public website deployment and multi-model cost optimization.



## Phase 2 Quality TODOs

### Official Domain Verification

Status: in progress.

- Phase 1 must identify `company_official_domain`, such as `unitree.com` for Unitree.
- Only verified official company domains or clearly official company hiring systems should enter Phase 2.
- Third-party recruitment sites should be rejected by default, not accepted unless they happen to miss a blocklist.
- External ATS-style hiring systems need `official_domain_verified` and `verification_notes` before their pages can become final evidence.
- Search results should pass a verifier that checks company signal, hiring-page path signal, official-domain signal, and third-party/school/aggregator rejection rules.
- Unverified links should become `rejected` or `lead_only`; they must not enter final job-detail samples.

### Taxonomy-Based Keyword Extraction

Status: future.

- Do not keep expanding one fixed SLAM keyword list indefinitely.
- First identify the role family, such as SLAM, Agent, backend, frontend, data analysis, or product.
- Load a role-specific taxonomy plus a common software-engineering taxonomy.
- Extract technical terms from the original job text, then classify and normalize them through the taxonomy.
- For Agent roles, target categories include LLM/Agent, RAG/Knowledge, Backend/API, Data/Storage, Testing/Evaluation, Integration, and Ops.
- Preserve evidence text for extracted technical terms when practical.

### Immediate Next Steps After Official-Only Update

Status: next validation tasks.

1. Browser-test Phase 1 with OpenAI real search under official-only constraints.
2. Check whether the result count is still useful after third-party sources are rejected.
3. Browser-test Phase 2 on 1-2 verified official-domain companies.
4. Confirm that final job details preserve raw official job text and do not include third-party pages.
5. If official-only search returns too few companies, decide whether to add a separate `lead_only` mode for third-party hints that cannot become final evidence.
6. Improve official-domain verification by fetching page title/body and checking company name, hiring path, official domain, external ATS relationship, and third-party rejection signals.
7. Add duplicate and parent/child page handling so an official job list page and a specific official job detail page do not both become final samples for the same role.
8. Design a taxonomy module before supporting non-SLAM roles such as Agent, backend, frontend, data analysis, or product.
