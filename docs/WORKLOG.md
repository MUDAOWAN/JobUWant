# Worklog

This file records completed work, touched files, unresolved issues, and next
steps.

## 2026-06-27

Completed:

- Confirmed project name: JobUWant.
- Confirmed formal development environment: WSL2 Ubuntu.
- Confirmed formal project path: `/home/votally/projects/JobUWant`.
- Created the formal project directory.
- Initialized Git.
- Renamed the initial branch to `main`.
- Added GitHub remote: `git@github.com:MUDAOWAN/JobUWant.git`.
- Started the documentation foundation.

Changed files:

- `README.md`
- `docs/PROJECT_BRIEF.md`
- `docs/DECISIONS.md`
- `docs/WORKLOG.md`
- `docs/AGENT_RULES.md`
- `docs/SESSION_HANDOFF.md`
- `docs/CODEX_CLI_HANDOFF.md`
- `docs/PRODUCT_DESIGN.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DATA_POLICY.md`
- `docs/SKILL_RESEARCH.md`

Open items:

- Confirm whether to make the first Git commit.
- Confirm whether to test GitHub connection.
- Confirm whether to push the first commit.
- Continue to product positioning.

Additional notes:

- The user confirmed Codex CLI can now operate on project documents.
- Windows Codex CLI should use
  `\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant` as the working
  directory path.
- New conversations should first read `docs/CODEX_CLI_HANDOFF.md`.

## 2026-06-27 Product Positioning And Initial Planning

Completed:

- Recorded the first MVP positioning as a localhost web pilot tool.
- Confirmed first MVP city: Hangzhou.
- Confirmed first MVP role: SLAM engineer / SLAM algorithm engineer.
- Confirmed first MVP hiring stage: campus autumn hiring, compatible with early
  hiring batches.
- Confirmed first MVP target user: the project owner.
- Confirmed first MVP does not need login.
- Recorded core product ideas: query entry, company opportunity map,
  structured job fields, technical stack and capability analysis, visual
  report, incremental updates, and token/cost visibility.
- Recorded deferred expansion directions.

Changed files:

- `README.md`
- `docs/PROJECT_BRIEF.md`
- `docs/PRODUCT_DESIGN.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/WORKLOG.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/DATA_POLICY.md`
- `docs/SESSION_HANDOFF.md`

Open items:

- Prepare technical stack selection.
- Decide first UI approach.
- Decide backend language and application shape.
- Decide data storage option.
- Decide whether a local vector store is needed.
- Decide whether the first version needs background task handling.
- Decide whether cost statistics should be implemented from the start.
- Decide whether report export is required in the first MVP.
- Decide whether the first company pool should be manually maintained.

## 2026-06-27 Technical Direction And Process Planning

Completed:

- Confirmed first MVP technical direction for planning: Streamlit, Python,
  SQLite, and synchronous execution.
- Confirmed SQLite as the first MVP storage choice for local records, company
  pool data, structured job records, query history, source metadata, and
  token/cost records.
- Confirmed task queue or background job execution should remain a later
  improvement after the synchronous MVP is validated.
- Confirmed cost and token controls should be first-version work goals and
  implemented through staged limits.
- Confirmed report export can be included in the first MVP, with exact format
  still to be decided.
- Confirmed the user does not need to provide the initial company list.
- Confirmed a JobUWant-specific Codex skill should wait until repeated
  development workflows become stable.

Changed files:

- `README.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DATA_POLICY.md`
- `docs/DECISIONS.md`
- `docs/SESSION_HANDOFF.md`
- `docs/WORKLOG.md`
- `docs/AGENT_PROCESS.md`

Open items:

- Decide exact information intake method and allowed source types.
- Decide default query budget values.
- Decide whether a local vector store is needed in the first MVP.
- Decide first report export format.
- Convert MVP module plan into implementation tasks after user approval.

## 2026-06-27 Information Intake Design

Completed:

- Recorded the agreed direction for information intake.
- Added a dedicated design document for discovering Hangzhou SLAM-related
  companies and locating role job descriptions.
- Clarified that recruitment platforms are useful lead sources and official
  company hiring pages are preferred as high-confidence evidence.
- Recorded the layered process for candidate source discovery, company pool
  updates, official-page follow-up, source fingerprinting, structured
  processing, and incremental reporting.
- Confirmed first budget direction: 20 candidate source records, 10 new or
  changed records, 10 model calls, HTML export, and no local vector store in
  the first MVP.

Changed files:

- `README.md`
- `docs/INFORMATION_INTAKE.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/DATA_POLICY.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/SESSION_HANDOFF.md`
- `docs/WORKLOG.md`

Open items:

- Decide which search provider or source access method to use first.
- Decide which source types should require manual URL entry.
- Decide whether the first MVP needs a review screen for promoting candidate
  companies into the main company pool.
- Decide exact token and estimated-cost limits.

## 2026-06-27 Search Entry And Budget Planning

Completed:

- Clarified what a search entry and search API mean for JobUWant.
- Recorded candidate search options: OpenAI web search, Tavily, Brave Search,
  Google Programmable Search, and manual URL entry as fallback.
- Recorded the initial recommendation to compare OpenAI web search and Tavily
  first for Hangzhou SLAM source discovery.
- Confirmed the product should prefer a mostly automated intake chain.
- Confirmed a candidate-company confirmation step before deeper job-description
  processing.
- Confirmed the initial first-run budget target: 20 candidate sources, 10 new
  or changed records, 10 model calls, and about CNY 5 estimated cost.
- Recorded that the user expects API-based model calls and mentioned
  `gpt-5.5`, but the exact model identifier must be verified before
  implementation.

Changed files:

- `docs/INFORMATION_INTAKE.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/DATA_POLICY.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/SESSION_HANDOFF.md`
- `docs/WORKLOG.md`

Open items:

- Decide whether to test OpenAI web search or Tavily first.
- Verify the exact model identifier and availability before implementation.
- Decide whether to build the candidate-company confirmation screen in the
  first MVP.

## 2026-06-27 Harness Research And First MVP Direction

Completed:

- Recorded initial harness research in `docs/SKILL_RESEARCH.md`.
- Clarified that JobUWant should not create a project-specific Codex skill yet.
- Defined harness for this project as the workflow layer around search,
  source intake, model use, budget limits, persistence, confirmation points,
  traces, and evaluation.
- Compared simple in-repo Python harness, OpenAI Agents SDK, LangGraph,
  LlamaIndex workflows, Haystack pipelines, CrewAI flows, and OpenAI Evals.
- Selected simple in-repo Python harness as the first MVP direction.
- Deferred OpenAI Agents SDK, LangGraph, and evaluation tooling until the first
  workflow has real sample data and repeated patterns.

Changed files:

- `docs/INFORMATION_INTAKE.md`
- `docs/SKILL_RESEARCH.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/SESSION_HANDOFF.md`
- `docs/WORKLOG.md`

Open items:

- Decide whether the first search comparison starts with OpenAI web search or
  Tavily.
- Convert the simple harness stages into implementation tasks after approval.

## 2026-06-27 First MVP Skeleton

Completed:

- Added the first Streamlit app entry point.
- Added a `jobuwant` Python package for the MVP modules.
- Added SQLite initialization with tables for candidate sources, candidate
  companies, job records, and usage events.
- Added a simple in-repo Python harness using local sample data only.
- Added first-run budget configuration.
- Added candidate-company preview and confirmation flow in the UI skeleton.
- Added HTML report preview and download generation.
- Added `.gitignore` to exclude virtual environments, Python cache files,
  local data, and Streamlit secrets.
- Added `requirements.txt` with Streamlit as the first dependency.

Changed files:

- `.gitignore`
- `README.md`
- `app.py`
- `requirements.txt`
- `jobuwant/__init__.py`
- `jobuwant/config.py`
- `jobuwant/db.py`
- `jobuwant/harness.py`
- `jobuwant/models.py`
- `jobuwant/reports.py`
- `jobuwant/search.py`
- `docs/WORKLOG.md`
- `docs/SESSION_HANDOFF.md`

Verification:

- Ran Python bytecode compilation for `app.py` and `jobuwant`.
- Ran SQLite database initialization through `jobuwant.db`.

Open items:

- Install dependencies if approved.
- Start the Streamlit dev server if dependencies are available or after
  installation is approved.
- Add the candidate-company confirmation screen as a fuller workflow state.
- Add OpenAI web search and Tavily provider implementations after API choices
  and credentials are confirmed.
- Add model structuring after the exact model identifier and API credentials
  are confirmed.

## 2026-06-27 Dependency Install And Local Server

Completed:

- Created project virtual environment at `.venv`.
- Installed Streamlit dependencies from `requirements.txt`.
- Added `.streamlit/config.toml` to run Streamlit headlessly and avoid the
  first-run email prompt.
- Started the Streamlit app on port 8501.
- Verified the app responds with HTTP 200 at `http://127.0.0.1:8501`.

Notes:

- The first virtual environment attempt failed until `python3.12-venv` was
  installed in WSL.
- The first pip install attempt timed out but a later longer run completed.
- Streamlit first-run prompting required project config before background
  startup was reliable.

Changed files:

- `.streamlit/config.toml`
- `README.md`
- `docs/WORKLOG.md`
- `docs/SESSION_HANDOFF.md`

Open items:

- Keep using `http://localhost:8501` for local testing.
- Add real OpenAI web search or Tavily provider after API choice and
  credentials are confirmed.
- Add model structuring after model identifier and API credentials are
  confirmed.

## 2026-06-28 Local Server Startup Follow-up

Completed:

- Updated the handoff docs to reflect that the Streamlit MVP skeleton already exists.
- Confirmed the first commit should wait until the local MVP flow has been tested.
- Tried the documented Streamlit foreground command for diagnosis.
- Confirmed the app itself can start: the foreground diagnostic printed Streamlit local and network URLs.
- Found that two background startup methods did not keep the service running in this Codex/WSL context: Windows `Start-Process` and WSL `nohup ... &`.
- Confirmed the failure state by checking that no Streamlit process existed and port 8501 was not listening.
- Started the service successfully with `setsid` from WSL and confirmed `0.0.0.0:8501` was listening.
- User confirmed the web page opens successfully in the browser.

Reliable startup command for future sessions:

```bash
wsl -e bash -lc "cd /home/votally/projects/JobUWant && setsid .venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 > /tmp/jobuwant-streamlit.log 2>&1 < /dev/null & sleep 3 && pgrep -af streamlit && ss -ltnp"
```

Troubleshooting notes:

- If `http://localhost:8501` does not open, first check `pgrep -af streamlit` and `ss -ltnp`.
- A healthy run should show a Streamlit process and `0.0.0.0:8501` listening.
- If no process remains, run the short foreground command to capture Streamlit startup output.
- If localhost forwarding is delayed, use the WSL network URL printed during the foreground diagnostic run.

Open items:

- Continue testing the current sample-data MVP flow in the browser.
- Keep the first Git commit deferred until the user confirms the MVP skeleton is worth preserving as the baseline.

## 2026-06-28 Codex CLI File Operation Follow-up

Completed:

- Recorded that direct UNC reads and `apply_patch` writes can fail in this
  Windows Codex CLI plus WSL project setup before reaching project code.
- Confirmed WSL read-only commands were reliable for inspecting project files.
- Confirmed constrained PowerShell documentation edits against the UNC path can
  work after explicit approval when the normal patch path cannot access the
  workspace.
- Added quick-start troubleshooting notes to `docs/SESSION_HANDOFF.md`.
- Added agent process guidance to `docs/AGENT_PROCESS.md`.

Recommended future workflow:

- If a new conversation cannot read or write expected files, first inspect
  `docs/SESSION_HANDOFF.md` and `docs/WORKLOG.md` for prior notes.
- Verify with WSL read-only commands before assuming the project files are
  missing or damaged.
- Keep fallback edits narrow, approved, and followed by read-only verification.

## 2026-06-28 Chinese UI Follow-up

Completed:

- Confirmed the current MVP flow uses local sample data: 3 candidate sources,
  0 model calls, and CNY 0.00 estimated cost.
- Localized the visible Streamlit UI labels to Chinese.
- Localized the preview HTML report labels to Chinese.
- Localized candidate table column names to Chinese.
- Localized the default first MVP query values to Chinese.
- Kept the workflow logic unchanged: Streamlit remains the UI layer and the
  simple in-repo Python harness remains the workflow layer.
- Fixed an encoding issue from an earlier write attempt by storing Chinese UI
  strings as Unicode escapes in Python source files. This keeps the source files
  ASCII while still rendering Chinese correctly at runtime.

Changed files:

- `app.py`
- `jobuwant/config.py`
- `jobuwant/models.py`
- `jobuwant/reports.py`

Verification:

- Ran Python bytecode compilation for `app.py` and `jobuwant` successfully.

Open items:

- Refresh the browser and test the Chinese UI flow.
- Next implementation step: add the first real source discovery provider behind
  the existing harness boundary, while keeping the sample provider available.

## 2026-06-28 OpenAI Web Search Provider Skeleton

Completed:

- Added `openai>=1.88` to `requirements.txt`.
- Added `OpenAISettings` configuration with default model `gpt-5.5`.
- Kept the local sample provider as the default fallback path.
- Added an OpenAI web-search provider behind the existing in-repo Python
  harness boundary.
- Added UI selection between local sample data and OpenAI real search.
- Preserved the Streamlit role as the input/display layer; provider execution,
  result shaping, persistence, and usage tracking remain behind the harness.
- Split database dictionaries from Chinese display dictionaries so persistence
  keeps stable English field names while the UI shows Chinese labels.
- Added README instructions for creating `.streamlit/secrets.toml` locally.

API key location:

```toml
OPENAI_API_KEY = "your_api_key_here"
OPENAI_MODEL = "gpt-5.5"
```

Open items:

- Install the updated dependency set with `.venv/bin/pip install -r requirements.txt` after user approval.
- User should create `.streamlit/secrets.toml` locally and fill in `OPENAI_API_KEY`.
- Test the local sample provider again after refreshing the Streamlit app.
- Test the OpenAI provider only after dependency installation and API key setup.
## 2026-06-28 OpenAI Web Search Validation And MVP Phase Direction

Completed:

- Installed the OpenAI SDK dependency from `requirements.txt`.
- Confirmed the user's configured API key, base URL, and `gpt-5.5` model can
  call Chat Completions.
- Re-tested Responses API with the `web_search` tool and confirmed it is usable
  through the configured provider.
- Confirmed `web_search` is the supported tool name in this environment;
  `web_search_preview` returned an unsupported-tool error.
- Improved the OpenAI web-search provider response handling:
  - extracts JSON from response text more robustly
  - accepts JSON wrapped in Markdown fences
  - reads usage from object or dict-style responses
  - reports clear errors when no usable candidate company exists
- Tightened the OpenAI search prompt and local candidate filter around:
  - Hangzhou, Zhejiang, China
  - SLAM, localization, mapping, navigation, robotics, autonomous driving
  - campus hiring, new graduate, early batch, internship, junior roles
  - excluding overseas-only or senior/staff/principal-only roles without
    matching China/campus evidence
- Verified provider-level search returned target-relevant companies such as
  Unitree, Hikvision, Zhejiang SUPCON Information, Shining 3D, and Hithink with
  evidence URLs.
- Restarted the Streamlit service with the documented `setsid` command.
- User tested the Streamlit UI and confirmed OpenAI real search returns about
  10 real companies, including Hikvision and Unitree.

Current interpretation:

- MVP Phase 1, candidate-company discovery, is validated.
- The current app returns candidate-company evidence and summarized relevance.
- It does not yet fetch or preserve full job-description text exactly as shown
  on hiring pages.

Next phase:

- Implement MVP Phase 2: job-detail collection.
- For each candidate company/source, fetch or accept the matching job-detail
  page and preserve original job text.
- Store structured fields such as company, job title, city, hiring target,
  responsibilities, requirements, technical keywords, original URL, source type,
  confidence label, and original text.
- After Phase 2 works, implement MVP Phase 3: aggregate 10-20 job descriptions
  and analyze common technical stacks, skill frequency, company differences,
  and new-graduate preparation suggestions.

Technology note:

- Continue using Streamlit for MVP development.
- Do not switch to a full frontend/backend stack until job-detail collection
  and multi-job analysis are validated.

## 2026-06-30 Project Handoff, Harness Research, And Phase 2 Planning

Completed:

- Read the current handoff and planning documents:
  - `docs/CODEX_CLI_HANDOFF.md`
  - `docs/SESSION_HANDOFF.md`
  - `docs/WORKLOG.md`
  - `docs/ROADMAP.md`
  - `docs/DECISIONS.md`
  - `docs/AGENT_PROCESS.md`
- Confirmed the project root as `/home/votally/projects/JobUWant`.
- Created `docs/public` and copied the external reference file from the Windows desktop to `docs/public/tencent_harness.md`.
- Read `docs/public/tencent_harness.md` as reference material.
- Reviewed the current code boundaries in `app.py`, `jobuwant/db.py`, `jobuwant/harness.py`, `jobuwant/models.py`, and `jobuwant/search.py`.
- Researched current harness / agent workflow / skill-based workflow options, including OpenAI Agents SDK, LangGraph, LlamaIndex Workflows, PydanticAI, AutoGen, CrewAI, DSPy, and general workflow systems such as Prefect, Dagster, and Temporal.
- Confirmed the current MVP should continue with Streamlit, Python, SQLite, synchronous execution, and the simple in-repo Python harness.
- Recorded a Phase 2 direction: start with candidate job leads, user confirmation, user-pasted original job text fallback, structured parsing, human review, and SQLite persistence.

Changed files:

- `docs/public/tencent_harness.md`
- `docs/HARNESS_RESEARCH.md`
- `docs/AGENT_PROCESS.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/WORKLOG.md`
- `docs/SESSION_HANDOFF.md`

Open items:

- Design the Phase 2 minimal implementation in detail.
- Confirm whether to implement Phase 2 first with 1-2 companies using pasted original job text as the primary reliable path.
- Confirm whether to add Pydantic for structured validation.
- Confirm whether to add `job_leads`, `job_details`, and `parse_runs` tables or evolve the existing `job_records` table.
- Do not commit Git until the user explicitly approves.

## 2026-07-01 Phase 2 Automation-First Implementation

Completed:

- Confirmed Phase 2 should be automation-first, with the first run limited to 1-2 companies.
- Added Pydantic to `requirements.txt` for structured extraction validation.
- Added Phase 2 data models for job leads, parsed job details, and collection results.
- Added SQLite tables for `job_leads`, `job_details`, and `parse_runs` while keeping existing Phase 1 tables.
- Added `jobuwant/job_details.py` for public page text extraction, source confidence scoring, rule-based fallback parsing, OpenAI-assisted structured parsing, and content hashes.
- Extended the search provider interface with `discover_job_leads`.
- Added OpenAI web-search job lead discovery and sample provider job lead discovery.
- Extended the harness with `collect_job_details`, job lead persistence, job detail persistence, parse run persistence, and saved job detail listing.
- Updated the Streamlit app with a Phase 2 automatic job-detail collection area and saved job detail display.

Verification:

- Ran Python bytecode compilation for `app.py` and `jobuwant` successfully.
- Ran SQLite initialization successfully.
- Confirmed Pydantic is available in the current virtual environment.
- Ran an in-memory sample-provider smoke test: Phase 1 returned 2 companies, Phase 2 returned 2 job leads and 2 job details.

Open items:

- User should run the Streamlit app and test OpenAI real Phase 2 collection with 1-2 companies.
- If public page text extraction is weak for target sites, consider adding a dedicated page text extraction dependency after review.
- Do not commit Git until the user explicitly approves.

## 2026-07-01 Official-Only Phase 1 And Phase 2 Filtering

Completed:

- Tightened Phase 1 OpenAI web-search prompt to allow only official company hiring pages, official campus pages, or clearly official company hiring systems.
- Tightened Phase 2 job lead prompt with the same official-only rule.
- Added code-side filtering for known third-party recruitment platforms and school/employment-board style domains.
- Added Phase 2 filtering so job leads must be acceptable official URLs and, when possible, share the same base domain as the Phase 1 official evidence URL.
- Improved page text cleaning to remove common navigation/footer noise such as copyright, ICP records, public security registration text, language selectors, and legal links.
- Expanded technical keyword extraction to include more SLAM, robotics, sensor, library, optimization, and tooling terms.

Verification:

- Ran Python bytecode compilation for `app.py` and `jobuwant` successfully.
- Ran an in-memory sample-provider smoke test successfully: 2 companies, 2 job leads, 2 job details.
- Checked that `campus.niuqizp.com` and `bebee.com` are rejected by the official URL filter while `unitree.com` is accepted.
- Checked that common footer noise is removed by text cleaning.

## 2026-07-01 Official Domain Verifier And Taxonomy TODO

Completed:

- Explained that the Cloudflare 524 response means the configured upstream API service timed out after a 120-second proxy read window and is retryable after backoff.
- Added official-domain fields to candidate company records: `official_domain`, `official_domain_verified`, and `verification_notes`.
- Added an official company source verifier that rejects third-party or unsupported URLs, checks hiring-page path markers, and records verification notes.
- Updated Phase 1 candidate parsing to keep only verified official hiring evidence.
- Updated Phase 2 collection to process only verified official-domain companies.
- Recorded taxonomy-based keyword extraction as future work for general roles such as Agent, backend, frontend, and data analysis.

Open items:

- Build a stronger official-domain verifier that can fetch and inspect page title/body before accepting external ATS domains.
- Add a taxonomy module before trying to support arbitrary role families beyond the current SLAM-focused MVP.

## 2026-07-01 Current State Consolidation

Completed:

- Consolidated the current project state into `docs/SESSION_HANDOFF.md` for future conversations.
- Recorded that Phase 2 is implemented as automation-first but constrained to official hiring evidence.
- Recorded the current runtime issue pattern for Cloudflare 524 upstream timeout from `beefapi.com`.
- Recorded immediate validation tasks after the official-only update.
- Clarified that taxonomy-based keyword extraction is future work and should be designed before supporting arbitrary role families such as Agent roles.

Current todo:

- Test official-only OpenAI Phase 1 in the browser.
- Test Phase 2 against 1-2 verified official-domain companies.
- Review raw text cleanliness and parse accuracy.
- Strengthen official-domain verifier if any third-party page still enters results.
- Add duplicate/page-hierarchy handling for official job list pages versus specific official job detail pages.
- Design taxonomy module for general role support.
- Keep Git commit deferred until user approval.

## 2026-07-03 Phase 1 Batch Search, Timing, And Phase 2 Evidence Review

Completed:

- Browser-tested Phase 1 with OpenAI real search after switching to small-batch discovery.
- Confirmed Phase 1 can discover 10 official-domain candidate companies.
- Changed Phase 1 discovery to run as small batches of up to 3 companies per OpenAI web-search call, accumulating unique companies until the target count or model-call budget is reached.
- Added exclusion lists for already collected company names and official domains so later batches avoid repeating earlier results.
- Added code-side de-duplication by company name, official domain, and evidence URL.
- Fixed `candidate_companies` persistence so `official_domain`, `official_domain_verified`, and `verification_notes` are written to SQLite.
- Added elapsed-time measurement to `DiscoveryResult` and `JobDetailCollectionResult`.
- Displayed Phase 1 total elapsed time and Phase 2 total elapsed time in the Streamlit metrics area.
- Added a Phase 2 page-text quality gate before model parsing. The gate checks raw text length, job-detail markers, technical keyword hits, and target role/city/stage signals.
- Marked pages that fail the quality gate as `lead_only` instead of treating them as final parsed evidence.
- Investigated Phase 2 outputs exported to `C:\Users\Administrator\Desktop\test`.

Changed files:

- `app.py`
- `jobuwant/harness.py`
- `jobuwant/job_details.py`
- `jobuwant/models.py`
- `jobuwant/search.py`

Verification:

- Ran Python bytecode compilation for `app.py` and `jobuwant` successfully.
- Ran sample-provider smoke tests for Phase 1 timing and Phase 2 quality gating.
- Restarted Streamlit and confirmed `http://localhost:8501` returned HTTP 200.
- User reported one real Phase 1 run found 10 companies with 4 model calls, estimated CNY 0.40, and 782.2 seconds elapsed.
- User reported one real Phase 2 run processed 2 companies / 4 rows in 92.4 seconds.

Findings:

- Phase 1 correctness improved with official-only evidence, but elapsed time is high because each OpenAI web-search batch is slow. The 10-company run used 4 serial web-search calls, averaging roughly 195 seconds per call. This is mainly provider/search latency plus official-evidence constraints, not local Python or SQLite cost.
- Phase 2 currently depends on static HTML retrieval with `urllib` and a simple HTML text extractor. For dynamic recruiting pages, the stored `raw_job_text` may contain only the page shell, title, navigation, product menu, or footer rather than the browser-visible job description.
- Unitree's specific job URL looked correct in the browser, but the stored raw text mostly contained navigation/product text, so it produced very few technical keywords and was marked `lead_only`.
- Unitree's job-list URL contained more static job-related text, so it produced richer keywords even though it is conceptually less precise and more mixed.
- ArcSoft's specific job result diverged from the browser-visible job description because the stored raw text included site/product/solution text such as ADAS, AR/VR, SDKs, and vSLAM instead of the exact job duties and requirements. The expected job text includes image processing, computer vision, pattern recognition, PCA, Boosting, SVM, Neural Net, Regression, Haar, Gabor, LBP, SIFT, HOG, C/C++, and deep learning.
- ArcSoft's ATS listing page returned only a tiny shell text such as `ArcSoft虹软`, so it correctly cannot be parsed as final job evidence.

Current issues:

- Phase 1 can be correct but slow when using OpenAI web search through the configured provider.
- Phase 2 must become evidence-first: final parsing should only use raw text that matches the browser-visible job description.
- Static HTML extraction is insufficient for some official recruiting pages.
- Job-list pages and job-detail pages need different handling; list pages should not be parsed as a single final job description without first isolating the relevant job block.
- `lead_only` rows are still displayed near parsed details, which can confuse review.

Recommended next steps:

1. Split Phase 2 UI into two tables: final parse-ready/auto-parsed job details and `lead_only` / `needs_text` leads.
2. Show `raw_job_text` prominently before trusting parse output, and make raw evidence review the first Phase 2 validation step.
3. Add a manual pasted-text fallback so the user can paste the exact browser-visible job description and parse that authoritative text.
4. Add a rendered-page retrieval option, likely with Playwright, for dynamic official recruiting pages after user approval to add dependencies.
5. Add job-list page handling that isolates the relevant job block or follows the detail URL before parsing.
6. Consider a separate search provider or URL-discovery layer such as Tavily or self-hosted SearXNG later to reduce Phase 1 web-search latency.
7. Keep Git commit deferred until the user explicitly approves.

## 2026-07-15 BOSS Source Chain Breakthrough

### Goal

Validate a practical BOSS data-source path for JobUWant before returning to official-company hiring pages.

The original MVP direction was:

`web search -> company official hiring pages -> job text -> SQLite -> analysis/report`

During Phase 2 testing, many official pages could not be read reliably with static HTML fetch because the browser-visible job text was often loaded dynamically. To unblock the MVP data flow, we tested BOSS as a faster and richer job-source path.

### Tested Paths

#### 1. Direct `iv8 + requests` path

Purpose:

- Use Python requests for BOSS job APIs.
- Handle BOSS `code=37` by downloading `security-js/{name}.js`.
- Use `iv8` to run `new window.ABC().z(seed, ts)` and refresh `__zp_stoken__`.

Earlier result:

- Job list retrieval was validated once and returned 15 records.
- Detail probing later hit `code=35` or lacked stable detail parameters.
- This showed the token-generation method worked, but the session/context for detail retrieval was incomplete.

#### 2. BossFlow browser path

Purpose:

- Use a real Chrome profile and browser-driven page flow.
- Open the BOSS list page, listen to the list API response, open detail pages, and read detail API response or DOM text.

Validated result:

- WSL Chrome was installed and configured.
- Chinese font rendering was fixed with `fonts-noto-cjk` and `fonts-noto-cjk-extra`.
- Manual QR login succeeded and was persisted in `download/BossFlow/.chrome_profile`.
- Hangzhou + `SLAM工程师` returned 15 job cards.
- BossFlow retrieved 15 job records with 15/15 detail descriptions.
- Output was saved to `download/BossFlow/projects/hangzhou_slam/crawl_partial.json`.

#### 3. Combined path: Chrome profile login + `iv8 + requests`

This is the most important latest result.

Method:

- Use BossFlow/Chrome only to hold a valid logged-in profile.
- Reuse `download/BossFlow/.chrome_profile` to load current BOSS site session state into memory.
- Use Python `requests.Session` for the list and detail APIs.
- Use `iv8` only when an API response returns `code=37` and needs a fresh `__zp_stoken__`.

Validated result:

- List API returned HTTP 200, business `code=0`, and 15 records.
- The list records contained key detail fields such as `encryptJobId`, `securityId`, and `lid`.
- Single-detail probe succeeded with `job/detail.json?securityId=...`.
- `securityId` only succeeded and returned `zpData.jobInfo.postDescription`.
- `jobId + lid` alone failed with business `code=17` because required parameters were missing.
- `jobId + lid + securityId` also succeeded.
- A 5-detail batch initially succeeded 2/5, with later items returning `code=37`.
- After adding detail-level `code=37` refresh-and-retry handling, the 5-detail batch succeeded 5/5.
- Output was saved to `ai-param-flow-test/output/profile_iv8_detail_batch_retry.json`.

### Code 37 Meaning

`code=37` means the current session needs a fresh temporary verification cookie.

The response includes:

- `zpData.seed`
- `zpData.name`
- `zpData.ts`

Handling flow:

1. Download `https://www.zhipin.com/web/common/security-js/{name}.js`.
2. Build a minimal browser-like environment in `iv8`.
3. Load a small HTML snapshot containing the security JS.
4. Run `encodeURIComponent((new window.ABC).z(seed, ts))`.
5. Replace the current session cookies:
   - `__zp_stoken__`
   - `__zp_sseed__`
   - `__zp_sname__`
   - `__zp_sts__`
6. Retry only the current request once.

Important detail: the `seed`, `name`, and `ts` must come from the same `code=37` response. Old values should not be mixed with new responses.

### Code 35 Meaning

`code=35` was previously seen during detail probing and returned a message indicating abnormal IP/session behavior.

In practice, `code=35` is more severe than `code=37`:

- `code=37` is recoverable by refreshing `__zp_stoken__`.
- `code=35` is not solved by a simple token refresh.
- It usually means the request context, request rhythm, or session state looks unsuitable for continuing.

Current mitigation:

- Keep batches small.
- Reuse a valid logged-in Chrome profile.
- Avoid repeated endpoint guessing.
- Open the relevant page before detail requests when useful.
- Use realistic referer values.
- Add spacing between detail requests.
- Retry only the current request when `code=37` appears.

### BossFlow vs Combined iv8 Path

BossFlow path:

- Uses Chrome to open pages and listen to responses.
- Heavier but closer to real browser behavior.
- Best as a reference implementation and fallback.
- Validated at 15/15 detail descriptions.

Combined iv8 path:

- Uses Chrome profile only for login/session state.
- Uses `requests + iv8` to fetch list and details.
- Lighter and more suitable for JobUWant's Python/Streamlit/SQLite architecture.
- Validated at 5/5 detail descriptions after detail-level `code=37` retry handling.

Current preferred BOSS path for JobUWant:

`Chrome profile login -> load current site session -> requests list API -> extract securityId -> requests detail API -> iv8 refresh on code=37 -> save normalized job JSON -> import into JobUWant SQLite`

### Current Artifacts

- BossFlow successful 15-record output:
  - `download/BossFlow/projects/hangzhou_slam/crawl_partial.json`
- Desktop copy for manual inspection:
  - `C:\Users\Administrator\Desktop\bossflow_hangzhou_slam_result.json`
- Combined iv8 5-detail retry output:
  - `ai-param-flow-test/output/profile_iv8_detail_batch_retry.json`
- New combined-path test script:
  - `ai-param-flow-test/src/profile_iv8_detail_batch_retry.py`

### Recommended Next Steps

1. Keep BOSS as the first working data source for JobUWant.
2. Do not immediately merge BossFlow wholesale into JobUWant.
3. Treat BossFlow as:
   - logged-in Chrome profile owner,
   - true-browser reference flow,
   - fallback collector if lightweight requests fail.
4. Treat `iv8 + requests` as the likely lightweight JobUWant BOSS adapter path.
5. Next implementation step should be a controlled import path:
   - read BOSS JSON output,
   - normalize fields,
   - compute content hash,
   - store raw description and structured metadata into JobUWant SQLite.
6. Before increasing volume, keep one more validation step at 10-15 details with slow spacing and `code=37` retry handling.

## 2026-07-15 BOSS Method Timing Comparison

Goal:

- Compare BossFlow browser-driven path with the combined Chrome profile + iv8 + requests path under the same target condition.
- Target condition: Hangzhou city code 101210100, query SLAM, first-page 15 job cards/details.

Compared outputs:

- BossFlow native output: ai-param-flow-test/output/bossflow_native_method_timing.json
- Combined Chrome profile + iv8 + requests output: ai-param-flow-test/output/profile_iv8_15_timing_slam_exact.json

Result:

- BossFlow native path: result count 15, detail success 15/15, total time 126.495 seconds.
- Chrome profile + iv8 + requests path: browser page card count 15, list API HTTP 200 business code=0, detail success 15/15.
- Chrome profile + iv8 + requests timing: profile load 3.275 seconds, list request 0.351 seconds, detail requests 39.817 seconds, total time 45.317 seconds.

Conclusion:

- Both paths can retrieve the same class of job requirement information for the Hangzhou + SLAM test.
- BossFlow is slower but closer to a real browser flow and remains valuable as login/profile owner, reference path, and fallback collector.
- The combined path is much faster and fits JobUWant current Python + Streamlit + SQLite architecture better.
- Recommended integration direction: Chrome profile login -> load current site session -> requests list API -> extract securityId -> requests detail API -> iv8 refresh on code=37 -> normalize JSON -> import into SQLite.


## 2026-07-17 AI Dynamic Job Insights MVP

Completed:

- Added jobuwant/ai_job_insights.py for AI batch analysis over BOSS jobs labeled quality_status=analysis_ready.
- Verified .streamlit/secrets.toml OpenAI settings with a minimal call; the key/base/model path works.
- Reworked the analyzer prompt into a compact JSON task after the first schema-heavy prompt caused long waits.
- Added tolerant validation defaults and alias handling for model variants such as skill, bility, and 
equirement.
- Added local evidence backfill so sections with missing item-level evidence reuse top-level evidence instead of producing empty report slots.
- Ran a 1-job smoke output at data/boss_ai_job_insights_smoke.json.
- Ran the 9-job BOSS analysis-ready batch and wrote data/boss_ai_job_insights.json.

Current AI output summary:

- Sample count: 9.
- Role clusters: 激�?多传感器SLAM, 视觉SLAM/VIO, 机器�?无人机落�?
- Technical stack: C++, ROS, LiDAR, IMU, Ceres, VIO, SLAM.
- Ability requirements: 算法基础, 系统工程, 多传感器融合, 性能优化, 协作沟�?
- Graduate friendliness: 中等.

Verification:

- .venv Python bytecode compile passed for jobuwant/ai_job_insights.py.
- Final AI run completed with 1 model call, 5377 input tokens, 1183 output tokens, and wrote data/boss_ai_job_insights.json.


## 2026-07-18 Guangzhou Agent Validation

Completed:

- Validated a second city/role combination with the existing BOSS profile request path.
- Tested Guangzhou city code 101280100 with several role queries: AI Agent, Agent, 智能�? 大模�?Agent, and 大模型应�? each returned 15 list rows.
- Chose 广州 + 智能�?for the first cross-role detail run because the first result was closer to AI intelligent-agent development.
- Collected 5 detail records into i-param-flow-test/output/guangzhou_agent_detail_batch_retry.json.
- Imported those records into SQLite and marked them as source_type='boss_gz_agent' to avoid changing the previous Hangzhou SLAM analysis set.
- Ran quality labeling for Guangzhou intelligent-agent keywords. Result: 3 nalysis_ready, 2 
eeds_review; flags included senior_required and intern_position.
- Ran AI batch analysis for the 3 analysis-ready records and wrote data/guangzhou_agent_ai_job_insights.json.

AI result summary:

- Sample count: 3.
- Model usage: 1 call, 2304 input tokens, 1182 output tokens.
- Role clusters: AI智能体应用工程师, AI智能体解决方案销�? 智能体生态合伙人.
- Technical stack: Python, TensorFlow, PyTorch, NLP, Dify, Flowise, RPA, MySQL, API.
- Ability requirements: AI应用落地, 业务需求分�? 项目实施管理, 数据分析, 客户沟�? 持续学习.
- Graduate friendliness: 中等.

Product learning:

- The overall chain generalizes beyond Hangzhou + SLAM.
- The query 智能�?brings mixed technical, product, sales, and partner-style roles.
- Next filtering should distinguish target role intent such as engineering, product, sales, internship, and partner/business roles before final analysis.


## 2026-07-19 Shenzhen AI Application Validation

Completed:

- Re-ran the cross-city/role validation with the user-specified combination 深圳 + AI应用开发岗.
- Used Shenzhen city code 101280600.
- BOSS list request returned 15 rows.
- Detail batch size was 3, and detail success was 3/3.
- Detail output: i-param-flow-test/output/shenzhen_ai_app_detail_batch_retry.json.
- Imported the 3 records into SQLite and isolated them as source_type='boss_sz_ai_app'.
- Quality labeling result: 3 
eeds_review, all flagged with intern_position.
- Because the user explicitly asked to process 3 jobs and run AI analysis, the 3 rows were temporarily included for analysis, then restored to 
eeds_review.
- AI analysis output: data/shenzhen_ai_app_ai_job_insights.json.

AI result summary:

- Sample count: 3.
- Model usage: 1 call, 2655 input tokens, 1220 output tokens.
- Role clusters: AI应用后端开�? AI智能体与自动�? 跨境电商AI提效.
- Technical stack: Java, Go, Python, Coze, Dify, RPA, RAG, SQL.
- Ability requirements: 业务抽象能力, 学习与工具适应, 沟通协�? 文档沉淀, 效果复盘.
- Graduate friendliness: �?

Product learning:

- 深圳 + AI应用开发岗 produced a more coherent technical/intern batch than 广州 + 智能�?
- Search wording strongly affects role mix. For AI application roles, a more specific query can reduce sales/partner-style noise.
- Intern roles should remain review-gated, but can still be analyzed when the user explicitly wants an internship-oriented view.

## 2026-07-21 Job Analysis Pipeline MVP

Completed:

- Added `jobuwant/job_match_score.py` to score how well local jobs match a specific user search intent.
- Added local persistence for search runs, run items, local term candidates, AI extractions, compact report inputs, and final reports.
- Added `jobuwant/ai_job_extract.py` to extract per-job structured fields into `job_extractions`.
- Added `jobuwant/job_report.py` to aggregate `job_extractions` into compact report inputs without calling AI.
- Added `jobuwant/ai_report_writer.py` to generate user-facing job reports from compact report inputs.

Validated chain:

`job_details -> job_match_score.py -> ai_job_extract.py -> job_report.py -> ai_report_writer.py`

Validated samples:

- 深圳 + AI应用开发岗: 3 strong-match internship jobs.
- 杭州 + SLAM: 5 strong-match engineering jobs.

Artifacts:

- `data/job_report_input_sz_ai_app.json`
- `data/job_report_input_hz_slam.json`
- `data/job_report_sz_ai_app.json`
- `data/job_report_hz_slam.json`

Current usage:

- AI per-job extraction for 8 jobs: 2 calls, 6647 input tokens, 15853 output tokens.
- AI report writing for 2 reports: 2 calls, 14843 input tokens, 4652 output tokens.

Result summary:

- 深圳 AI application report identified Python, RAG, intelligent-agent workflow, Coze, Dify, RPA, and automation workflow as the main skill/tool signals. Graduate friendliness was high for the 3-job internship sample.
- 杭州 SLAM report identified SLAM, multi-sensor fusion, C++, ROS2, Linux, loop closure, VIO, and engineering deployment/debugging as the main signals. Graduate friendliness was low to medium for the 5-job engineering sample.

Known issues:

- AI extraction output is still too verbose. Evidence count per job/field should be limited before scaling.
- Some evidence quotes are AI-combined snippets instead of exact original substrings. The future harness should flag non-exact evidence.
- `ai_report_writer.py` now tolerates minor output-shape variants, but the prompt/schema should still be tightened.

TODO:

- Add sample-size based analysis-budget rules:
  - 1-10 jobs: allow richer per-job extraction and 1-3 evidence items per important field.
  - 11-50 jobs: batch extraction, keep only top fields and 1 evidence item per field/job, aggregate locally before final report.
  - 51-100 jobs: stricter pre-filtering, smaller per-job text windows, one evidence item per high-frequency item, final AI report receives only aggregated frequencies and representative evidence.
  - 100+ jobs: introduce sampling/stratification by role family and match score, then aggregate locally; avoid passing all raw text to final report generation.
- Make the budget rules configurable by CLI options and later by Streamlit controls.
- Add harness checks for token budget, evidence exact-match ratio, schema stability, cache reuse, and report-input size.

## 2026-07-25 Hangzhou Agent Internship 30-Item Test

Completed:

- Added `ai-param-flow-test/src/profile_iv8_detail_pages.py`, a parameterized BOSS profile detail runner.
- Ran Hangzhou city code `101210100` with query `AI Agent 实习`.
- The list stage returned 2 pages / 30 list rows.
- Detail retrieval succeeded for the first 15 rows. From row 16 onward the platform returned `code=36`, so the final analysis used the 15 rows with complete detail text.
- A slower second-page retry still returned `code=36` at list stage, so no additional detail rows were added.
- Imported the 15 successful rows into SQLite with `source_type='boss_hz_agent_intern'`.
- Created `search_run_id=5` for 杭州 + AI Agent 实习.
- Match scoring result: 1 `strong_match`, 5 `review`, 9 `weak_match`.
- Generated report input from `strong_match + review`, total 6 jobs.
- Generated final report:
  - `data/job_report_input_hz_agent_intern.json`
  - `data/job_report_hz_agent_intern.json`
  - `data/job_report_hz_agent_intern_timing.json`

Timing:

- Detail attempt for 30 rows: 119.651 seconds.
- Second-page retry: 10.247 seconds.
- AI extraction first attempt returned usable JSON but local validation was too strict for missing education evidence: 108 seconds.
- AI extraction successful retry after relaxing requirement-summary evidence: 91 seconds.
- Final report writing: 86 seconds.
- Total measured time with retry/fix path: 416.898 seconds.
- Successful path excluding the failed extraction attempt: 308.898 seconds.

Result summary:

- The sample is useful for identifying market mix, but it is not a clean 30-row Agent internship sample.
- The query produced many sales, solution, partner, and broad AI roles; only one row was a clean AI Agent development internship.
- Report Top signals include Python, 大语言模型, 深度学习, AI+应用, AI智慧教室, Prompt工程, RAG, and Agent frameworks such as LangChain/LlamaIndex/AutoGen/CrewAI from the clean internship row.
- Next retry should either wait for the current BOSS session to normalize or use a narrower query such as `AI Agent 开发实习生`, `智能体开发实习`, or `大模型应用开发实习`.

## 2026-07-26 Hangzhou Agent Internship 40-Item Slow Pipeline

Completed:

- Added `ai-param-flow-test/src/collect_boss_jobs_slow.py`, a parameterized slow BOSS collection script.
- The script defaults to Hangzhou city code `101210100`, query `Agent工程师`, and internship job type `1902`.
- It supports configurable target count, page size, page count, detail range, page delay, detail delay, batch rest, retry limit, and output path.
- It writes an import-ready JSON shape with `jobs` entries containing `title`, `company`, `city`, `salary`, `exp`, `edu`, `skills`, `desc`, `url`, and `_source`.
- It saves incrementally after list pages and detail items, and stops on `code=36`, check-page state, repeated empty details, or browser connection errors.

Validated run:

- Output JSON: `ai-param-flow-test/output/hz_agent_intern_40_full_jobs.json`.
- Source type: `boss_hz_agent_intern_20260726_probe40`.
- List stage: 3 pages requested, 40 unique rows kept.
- Detail stage: 40 attempted, 40 succeeded, 40 import-ready jobs saved.
- No `code=36` and no check-page state were observed.
- Imported 40/40 rows into SQLite.
- Correct search scoring run: `search_run_id=7`.
- Match scoring result: 26 `strong_match`, 14 `review`, 0 `weak_match`.
- AI per-job extraction completed for all 40 rows in four 10-job batches.
- Report input generated as `data/job_report_input_hz_agent_intern_probe40.json` with `report_input_id=10`, 40 jobs, estimated prompt tokens 17330, and evidence exact-match ratio 0.9849.
- Final report generated as `data/job_report_hz_agent_intern_probe40.json` with `report_id=8`.

Notes:

- An earlier scoring attempt produced `search_run_id=6` because shell quoting broke the Chinese city and keyword arguments. Ignore run 6; use run 7.
- The 40-row AI extraction was too slow as a single call, so the successful path uses 10-job batches with cache reuse.

## 2026-07-26 Streamlit BOSS Pipeline Panel

Completed:

- Added `jobuwant/boss_pipeline.py` as a reusable helper layer for the BOSS staged analysis path.
- Updated `app.py` with a `BOSS 实习岗位分阶段分析` expander.
- The panel shows the slow collection command, local collection JSON preview, source/run statistics, import action, local match scoring, one-batch AI structuring, report-input generation, and final report generation.
- The panel intentionally keeps the long slow collection command outside Streamlit and displays it as a command to run from the project terminal.
- The AI structuring action processes one batch at a time, defaulting to 10 jobs, matching the validated stable path from run 7.

Verification:

- `python -m py_compile app.py jobuwant/boss_pipeline.py` passed.
- Helper stats read the validated pipeline state: 40 imported jobs, latest run 7, 40 extractions, latest report 8.
- Streamlit was started on `http://localhost:8501` and returned HTTP 200.

## 2026-07-28 Web App Tech Route Update

Completed:

- Confirmed the formal Web App direction should account for future public use.
- Updated docs/WEB_APP_TECH_DESIGN.md to recommend FastAPI + Next.js + SQLite first.
- Kept React/Vite as a fallback quick local route, not the recommended baseline.
- Confirmed the first Web App implementation should be fixture-first, using the validated Hangzhou 40-job and Guangzhou 30-job outputs before connecting live long-running execution.
- Confirmed skill installation should wait until a concrete design, frontend implementation, frontend review, or browser testing phase needs it.
- Updated docs/WEB_APP_TODO.md with the confirmed route and staged skill usage.

Open items:

- User review of the updated technical design.
- After approval, create the webapp/ folder and start with backend API contracts plus fixture read endpoints.

## 2026-07-28 Web App Boundary Created

Completed:

- Confirmed the current Web App baseline remains FastAPI plus Next.js plus SQLite first.
- Created the formal Web App project boundary under webapp/.
- Added webapp/README.md with baseline stack, boundary rules, and fixture-first implementation rule.
- Added webapp/docs/PROJECT_BOUNDARY.md with ownership boundaries, next work gate, and staged skill usage.
- Added placeholder files for webapp/backend and webapp/frontend so the empty directories can be tracked.
- Did not initialize FastAPI, Next.js, or install dependencies.

Next recommended work:

- Define backend API contracts and task-level state tables before building full frontend pages.
- Start with fixture-first endpoints for the two validated runs.

## 2026-07-28 Fixture-First Backend API Skeleton

Completed:

- Added a FastAPI-oriented backend skeleton under webapp/backend.
- Added backend requirements file, without installing dependencies.
- Added task-level SQLite schema in webapp/backend/app/repositories/database.py.
- Added fixture registry for search_run_id 7 and search_run_id 8.
- Added read-only fixture service for task list, task detail, job rows, report input, final report, and events.
- Added FastAPI routes for health, tasks, jobs, report input, report, and events.
- Added API contract documentation in webapp/docs/API_CONTRACTS.md.
- Added task data model documentation in webapp/docs/DATA_MODEL.md.
- Added backend README and fixture service tests.

Verification:

- Python syntax compilation passed for backend app files.
- pytest was not run because pytest is not installed in the current virtual environment.
- Direct fixture service smoke check passed: task ids hz-agent-intern-40 and gz-gis-any-30 loaded; Hangzhou count was 40/40; Guangzhou count was 30/28; Guangzhou selected-only rows returned 28; report input and final report JSON were readable.

Open items:

- Install backend dependencies after user approval.
- Start FastAPI locally and verify HTTP endpoints.
- Begin Next.js frontend skeleton after API contracts are reviewed.

## 2026-07-28 Backend Dependency Install And HTTP Verification

Completed:

- Installed webapp/backend/requirements.txt into the existing project virtual environment after user approval.
- Verified FastAPI app import: title JobUWant Web API.
- Ran backend fixture tests: 4 passed.
- Started the FastAPI backend at http://localhost:8000.
- Verified HTTP endpoints for health, task list, Guangzhou selected job rows, Hangzhou report input, and Guangzhou final report.
- Confirmed Chinese report data is valid UTF-8 in source JSON; mojibake only appears in this terminal capture path.

Current server:

- Backend URL: http://localhost:8000
- API docs: http://localhost:8000/docs

Open items:

- Start Next.js frontend skeleton after API contracts are accepted.
- Build frontend pages against the fixture-first endpoints.

## 2026-07-29 Frontend Skeleton Continued

Completed:

- Recreated webapp/frontend with a Next.js TypeScript App Router skeleton after the earlier partial scaffold left malformed files.
- Added frontend API client for GET /api/health, GET /api/tasks, and GET /api/tasks/{task_id}.
- Added a fixture-first task dashboard page showing validated tasks, selected task metrics, stage timeline, match distribution chart, and artifact paths.
- Installed frontend dependencies recorded in package.json and package-lock.json: lucide-react, Recharts, TanStack Query, TanStack Table, and clsx.
- Added NEXT_PUBLIC_API_BASE_URL example configuration.
- Verified npm run typecheck passes.
- Updated webapp/docs/WORKFLOW.md and webapp/README.md with the current frontend state.

Verification result:

- TypeScript typecheck passed.
- Production build did not pass in this environment because Windows Node.js is being used against a WSL UNC project path; Next.js resolves mixed paths inconsistently during build.

Recommended next environment step:

- Install native Node.js inside WSL, or move frontend build execution to a normal Windows path. After that, rerun npm run build and start the local frontend.

## 2026-07-29 WSL Frontend Node Environment

Completed:

- Confirmed WSL is Ubuntu 24.04 and did not have native node available.
- Confirmed Next.js requires Node >=20.9.0.
- Downloaded Node.js v22.23.1 Linux x64 into webapp/.tools/node without changing system packages.
- Reinstalled frontend dependencies with project-local Linux Node.js to fix executable permissions from the earlier Windows Node install.
- Verified frontend typecheck passes.
- Verified frontend production build passes with npm run build.
- Updated webapp README and workflow notes with the required PATH command.

Frontend command prefix:

    export PATH=/home/votally/projects/JobUWant/webapp/.tools/node/bin:$PATH

## 2026-07-29 Frontend Dev Server Verification

Completed:

- Updated frontend dev script to use webpack mode, matching the verified production build path.
- Removed the package.json UTF-8 BOM introduced by Windows PowerShell JSON writing.
- Verified npm run typecheck passes with project-local Linux Node.js.
- Verified npm run build passes with project-local Linux Node.js.
- Started the frontend dev server and verified HTTP 200 at http://127.0.0.1:3000.
- Added webapp/.gitignore to keep local Node tools, frontend dependencies, and Next.js build output out of version control.

Current local URLs:

- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:3000

## 2026-07-29 Frontend Service Stability Check

Completed:

- Checked the reported frontend drop after the page initially loaded.
- Confirmed the backend health endpoint remained healthy at http://127.0.0.1:8000/api/health.
- Found the frontend dev server process was present but became unresponsive on port 3000.
- Stopped the dev server and switched local viewing to production preview with next start.
- Added webapp/scripts/start-frontend.sh with a clean Linux-only PATH for project-local Node.js.
- Started the frontend through Windows Start-Process calling WSL, with logs at C:\tmp\jobuwant-frontend.out.log and C:\tmp\jobuwant-frontend.err.log.
- Rechecked after startup: http://127.0.0.1:3000 returned HTTP 200, and http://127.0.0.1:8000/api/tasks returned HTTP 200.

Current recommendation:

- Use npm run build plus webapp/scripts/start-frontend.sh for stable local viewing.
- Use npm run dev only when actively editing frontend code.

## 2026-07-29 UI Design Direction Draft

Completed:

- Added webapp/docs/UI_DESIGN_DIRECTION.md as the UI design brief for the next Web App phase.
- Updated webapp/docs/WORKFLOW.md so Phase 4 references the UI design brief before page implementation.
- Clarified staged skill usage by exact names: ui-ux-pro-max, frontend-design, vercel-react-best-practices, web-design-guidelines, frontend-design-review, webapp-testing, and ComposioHQ/awesome-claude-skills as a reference catalog.
- Copied review files to the desktop:
  - C:\Users\Administrator\Desktop\JobUWant_UI_DESIGN_DIRECTION.md
  - C:\Users\Administrator\Desktop\JobUWant_WEBAPP_WORKFLOW.md

Next:

- Wait for user review of the UI direction before implementing the next frontend pages.
## 2026-07-29 Frontend Route Skeleton

Completed:

- Confirmed UI decisions: / redirects to /tasks, final report uses article-style reading with visualization charts, sample confirmation allows selection edits, and UI labels should be Chinese.
- Added formal Next.js route skeletons under webapp/frontend/src/app.
- Added /tasks, /tasks/[taskId], /tasks/[taskId]/sample, /tasks/[taskId]/structure, /tasks/[taskId]/report-input, and /tasks/[taskId]/report.
- Replaced the root page with a redirect to /tasks.
- Added a shared TaskWorkspace component with Chinese task navigation and fixture task context.
- Kept placeholder content for sample, structure, report-input, and report pages so each route can open before full page implementation.
- Restarted the frontend preview service after build.

Verification:

- npm run typecheck passed.
- npm run build passed.
- HTTP checks passed: / redirected, /tasks returned 200, task detail returned 200, sample returned 200, structure returned 200, report-input returned 200, and report returned 200.

Next:

- Implement task list and task detail pages with events and clearer task navigation before building the sample table.
## 2026-07-30 Task List Page

Completed:

- Added a dedicated /tasks page through webapp/frontend/src/features/tasks/task-list-page.tsx.
- Changed /tasks to use the new task list page instead of auto-selecting the first task in the workspace.
- Added Chinese task list UI with backend health, task summary metrics, search filter, task table, report status, and links to task detail.
- Kept the create task action disabled as a visible placeholder because write APIs are not connected yet.
- Added webapp/scripts/start-backend.sh for stable FastAPI startup.
- Restarted the frontend preview service after building.
- Restarted the backend service because port 8000 was not responding during verification.

Verification:

- npm run build passed.
- npm run typecheck passed after build regenerated .next/types.
- /tasks returned HTTP 200.
- /tasks/hz-agent-intern-40 returned HTTP 200.
- /tasks/gz-gis-any-30 returned HTTP 200.
- /api/health returned HTTP 200.
- /api/tasks returned HTTP 200.

Current local URLs:

- Frontend: http://127.0.0.1:3000/tasks
- Backend: http://127.0.0.1:8000

Next:

- Implement /tasks/[taskId] task detail with events, next action panel, and clearer artifact navigation.
## 2026-07-30 Task Detail Page

Completed:

- Added frontend API typing and client call for GET /api/tasks/{task_id}/events.
- Reworked /tasks/[taskId] into a task control page instead of a generic overview.
- Added task summary, stage progress, next action panel, artifact entries, event records, task metadata, and match distribution.
- Added Chinese labels for stages, event types, job type, city, and match status.
- Kept sample, structure, report-input, and report routes as placeholders for the following page-specific implementation phases.
- Restarted the frontend preview service after building.

Verification:

- npm run build passed.
- npm run typecheck passed.
- /tasks/hz-agent-intern-40 returned HTTP 200.
- /tasks/gz-gis-any-30 returned HTTP 200.
- /api/tasks/gz-gis-any-30/events returned HTTP 200.
- Frontend startup error log was empty after restart.

Next:

- Implement /tasks/[taskId]/sample as the sample confirmation page with job table, filters, selected-only mode, and row detail view.
## 2026-07-30 Sample Confirmation Page

Completed:

- Added frontend API typing and client call for GET /api/tasks/{task_id}/jobs.
- Added webapp/frontend/src/features/tasks/sample-confirmation-panel.tsx.
- Replaced the /tasks/[taskId]/sample placeholder with a fixture-backed job table.
- Added filters for title keyword, company keyword, match status, role intent, and selected-only mode.
- Added local selection preview with checkboxes. This does not persist changes yet because the sample write API is not connected.
- Added row expansion for match reasons, review reasons, metadata, and source URL.
- Restarted the frontend preview service after building.

Verification:

- npm run build passed.
- npm run typecheck passed.
- /tasks/hz-agent-intern-40/sample returned HTTP 200.
- /tasks/gz-gis-any-30/sample returned HTTP 200.
- /api/tasks/hz-agent-intern-40/jobs returned HTTP 200.
- /api/tasks/gz-gis-any-30/jobs?selected_only=true returned HTTP 200.
- Frontend startup error log was empty after restart.

Next:

- Implement /tasks/[taskId]/report-input with compact report input preview, charts, evidence quality, and JSON viewer.
## 2026-07-30 Web App Report Input Preview Page

Completed:

- Added the read-only report input preview page for the fixture-first Web App flow.
- Added frontend API typing and client call for GET /api/tasks/{task_id}/report-input.
- Replaced the report input placeholder in the task workspace with the real preview component.
- Displayed query boundary, sample metrics, evidence quality, salary summary, technical term chart, role distribution, technical evidence snippets, and raw JSON preview.
- Verified both validated samples without starting new collection or model calls.

Changed files:

- webapp/frontend/src/lib/api.ts
- webapp/frontend/src/features/tasks/task-workspace.tsx
- webapp/frontend/src/features/tasks/report-input-preview-panel.tsx
- webapp/docs/WORKFLOW.md
- docs/WORKLOG.md

Verification:

- npm run lint: passed.
- npm run typecheck: passed.
- npm run build: passed.
- GET /api/tasks/hz-agent-intern-40/report-input: 200.
- GET /api/tasks/gz-gis-any-30/report-input: 200.
- GET /tasks/hz-agent-intern-40/report-input: 200.
- GET /tasks/gz-gis-any-30/report-input: 200.

Next:

- Implement the final report view page.
- Then run a focused UI review pass before adding live task creation and write actions.
## 2026-07-31 Web App Final Report View Page

Completed:

- Added the read-only final report page for the fixture-first Web App flow.
- Added frontend API typing and client call for GET /api/tasks/{task_id}/report.
- Replaced the final report placeholder in the task workspace with the real report viewer.
- Displayed report title, audience summary, summary metrics, skill layer chart, priority chart, technical interpretations, skill layers, salary and threshold, experience and education, graduate friendliness, learning route, project suggestions, resume keywords, job search advice, caveats, and evidence references.
- Verified both validated samples without starting new collection or model calls.

Changed files:

- webapp/frontend/src/lib/api.ts
- webapp/frontend/src/features/tasks/task-workspace.tsx
- webapp/frontend/src/features/tasks/final-report-viewer.tsx
- webapp/docs/WORKFLOW.md
- docs/WORKLOG.md

Verification:

- npm run lint: passed.
- npm run typecheck: passed.
- npm run build: passed.
- GET /api/health: 200.
- GET /api/tasks/hz-agent-intern-40/report: 200.
- GET /api/tasks/gz-gis-any-30/report: 200.
- GET /tasks/hz-agent-intern-40/report: 200.
- GET /tasks/gz-gis-any-30/report: 200.

Next:

- Let the user review the final report page in browser.
- Then run a focused UI review pass and decide whether to refine page layout before implementing live task creation and write actions.
## 2026-07-31 Web App Harness Baseline

Completed:

- Added a lightweight in-repo Harness baseline for the Web App execution lifecycle.
- Defined task statuses, stage statuses, stage names, action names, stage order, artifact types, user-confirmation stage, next-stage calculation, action availability checks, and task status derivation.
- Added Harness unit tests.
- Added Web App documentation for Harness design, API integration direction, data model mapping, technical stack, and implementation record.
- Did not start new job collection or model work.

Changed files:

- webapp/backend/app/services/task_harness.py
- webapp/backend/tests/test_task_harness.py
- webapp/docs/WEB_APP_HARNESS.md
- webapp/docs/IMPLEMENTATION_RECORD.md
- webapp/docs/API_CONTRACTS.md
- webapp/docs/DATA_MODEL.md
- webapp/docs/WORKFLOW.md
- webapp/README.md
- docs/WORKLOG.md

Verification:

- Backend tests passed: 9 passed.

Next:

- Implement live task persistence repository and POST /api/tasks based on the Harness stage definitions.
## 2026-07-31 Web App Task Creation API

Completed:

- Added `AnalysisTaskCreate` request schema.
- Added live task repository functions for SQLite-backed task creation, listing, detail reading, stage listing, event listing, and artifact path listing.
- Added a unified task service that keeps fixture tasks readable while adding live task support.
- Added `POST /api/tasks`.
- New live tasks use public ids like `task-1`.
- Creating a task initializes six Harness stages as pending and writes a `task_created` event.
- Did not start new job collection or model work.

Changed files:

- webapp/backend/app/schemas/tasks.py
- webapp/backend/app/repositories/analysis_tasks.py
- webapp/backend/app/services/task_service.py
- webapp/backend/app/api/tasks.py
- webapp/backend/tests/test_analysis_tasks.py
- webapp/docs/API_CONTRACTS.md
- webapp/docs/DATA_MODEL.md
- webapp/docs/WEB_APP_HARNESS.md
- webapp/docs/IMPLEMENTATION_RECORD.md
- webapp/docs/WORKFLOW.md
- webapp/README.md
- docs/WORKLOG.md

Verification:

- Backend tests passed: 12 passed.
- GET /api/health returned 200.
- OpenAPI confirms `/api/tasks` supports `get` and `post`.

Next:

- Implement collection action endpoint under the Harness, including stage status updates, event records, and `search_run` artifact recording.

## 2026-07-31 Web App Collection Action Boundary

Completed:

- Added `POST /api/tasks/{task_id}/actions/start-collection`.
- Added live task repository helpers for stage running, completed, failed, task status refresh, and artifact records.
- Starting collection now marks `collect_jobs` as `running`, marks the task as `running`, and appends a `collect_jobs_started` event.
- Duplicate start requests return HTTP 409.
- Did not run actual job collection or model work.

Changed files:

- webapp/backend/app/repositories/analysis_tasks.py
- webapp/backend/app/services/task_service.py
- webapp/backend/app/api/tasks.py
- webapp/backend/tests/test_analysis_tasks.py
- webapp/docs/API_CONTRACTS.md
- webapp/docs/DATA_MODEL.md
- webapp/docs/WEB_APP_HARNESS.md
- webapp/docs/IMPLEMENTATION_RECORD.md
- webapp/docs/WORKFLOW.md
- webapp/README.md
- docs/WORKLOG.md

Verification:

- Backend tests passed: 14 passed.

Next:

- Connect the actual collection runner behind `start-collection`, then mark the stage completed or failed and record the `search_run` artifact.
## 2026-07-31 Web App Collection Runner Integration

Completed:

- Reviewed current Web App docs, Harness docs, and existing BOSS collection/scoring code before implementation.
- Added `webapp/backend/app/runner/collection_runner.py` as the first local background runner boundary.
- Updated `start_collection` so the API validates task inputs, marks `collect_jobs` running, queues the local runner, and returns immediately.
- Reused the existing slow collection script and `jobuwant.boss_adapter.import_boss_json` instead of rewriting collection logic.
- Added `job_search_runs` creation for collection output and recorded it as a `search_run` task artifact.
- Updated live task summaries so completed collection can surface `search_run_id` and `collected_count`.
- Added tests that use fake runner functions and do not start a real collection run.

Changed files:

- `webapp/backend/app/repositories/analysis_tasks.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/app/runner/__init__.py`
- `webapp/backend/app/runner/collection_runner.py`
- `webapp/backend/tests/test_analysis_tasks.py`
- `webapp/backend/tests/test_collection_runner.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 16 passed, 7 warnings.

Open items:

- Do not call `start-collection` for a new task unless the user explicitly wants to start a real collection run.
- Next backend step is `start-scoring`, using the collection `search_run` artifact as input.

## 2026-08-01 Web App Local Scoring Action

Completed:

- Added `POST /api/tasks/{task_id}/actions/start-scoring`.
- Added `webapp/backend/app/services/scoring_service.py`.
- Extended `jobuwant.job_match_score.score_jobs` with optional `existing_run_id` so live tasks can reuse the collection `job_search_runs` row.
- Scoring now writes `job_search_run_items` and `job_terms` against the task search run.
- Added `scored_jobs` artifact recording.
- Live task detail now returns match-status and role-intent counts after scoring.
- Live task jobs endpoint now returns scored rows after scoring.
- Added tests for successful local scoring and rejection before collection completion.
- Did not start real collection and did not call model work.

Changed files:

- `jobuwant/job_match_score.py`
- `webapp/backend/app/api/tasks.py`
- `webapp/backend/app/repositories/analysis_tasks.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/app/services/scoring_service.py`
- `webapp/backend/tests/test_scoring_service.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 18 passed, 9 warnings.

Next:

- Implement sample confirmation writes through `POST /api/tasks/{task_id}/sample`.

## 2026-08-01 Web App Sample Confirmation Writes

Completed:

- Added `POST /api/tasks/{task_id}/sample`.
- Added `SampleConfirmRequest` request schema.
- Added `webapp/backend/app/services/sample_service.py`.
- Added repository helpers for scored job id lookup, sample creation, and latest sample selection lookup.
- Sample confirmation now validates selected job ids against the task scoring run.
- Sample confirmation writes `analysis_samples` and `analysis_sample_items`.
- Sample confirmation records a `sample` task artifact and marks `confirm_sample` completed.
- Live job rows now reflect the latest saved sample selection.
- Added tests for successful sample confirmation and invalid job id rejection.
- Did not start real collection and did not call model work.

Changed files:

- `webapp/backend/app/api/tasks.py`
- `webapp/backend/app/repositories/analysis_tasks.py`
- `webapp/backend/app/schemas/tasks.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/app/services/sample_service.py`
- `webapp/backend/tests/test_sample_service.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 20 passed, 11 warnings.

Next:

- Implement AI structuring batch execution after explicit user approval for model calls.

## 2026-08-01 Web App Structuring Batch Plan

Completed:

- Added `POST /api/tasks/{task_id}/actions/start-structuring`.
- Added `GET /api/tasks/{task_id}/structure`.
- Added `StructuringBatchRead` and `StructuringStatusRead` schemas.
- Added `webapp/backend/app/services/structuring_service.py`.
- Added repository helpers for latest sample lookup, selected sample job ids, batch creation, and batch listing.
- Structuring start now creates pending `batch_runs` from the confirmed sample.
- Recorded a `batch_runs` task artifact.
- Marked `ai_structuring` as `waiting_for_user` after plan creation.
- Added Harness protection so repeated action requests against a waiting stage are rejected.
- Added tests for batch creation, status reading, and rejection before sample confirmation.
- Did not call model work.

Changed files:

- `webapp/backend/app/api/tasks.py`
- `webapp/backend/app/repositories/analysis_tasks.py`
- `webapp/backend/app/schemas/tasks.py`
- `webapp/backend/app/services/task_harness.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/app/services/structuring_service.py`
- `webapp/backend/tests/test_structuring_service.py`
- `webapp/backend/tests/test_task_harness.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 24 passed, 15 warnings.

Next:

- Actual AI structuring batch execution requires explicit user approval for model calls.

## 2026-08-01 Web App Structuring Batch Runner

Completed:

- Added `POST /api/tasks/{task_id}/actions/run-structuring-batches`.
- Added `webapp/backend/app/runner/structuring_runner.py`.
- Added repository helpers for resuming a waiting stage and updating `batch_runs` status.
- The runner processes pending batches sequentially.
- Batch rows now support persisted running/completed/failed state, model name, token usage, estimated cost, timing, and error fields.
- Successful completion records an `extractions` artifact and marks `ai_structuring` completed.
- Failed batch execution marks the failed batch and the stage failed.
- Added tests for queueing, fake successful batch execution, fake failed batch execution, and rejection before batch plan creation.
- Did not start real collection and did not call model work during verification.

Changed files:

- `webapp/backend/app/api/tasks.py`
- `webapp/backend/app/repositories/analysis_tasks.py`
- `webapp/backend/app/runner/structuring_runner.py`
- `webapp/backend/app/services/structuring_service.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/tests/test_structuring_runner.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 28 passed, 17 warnings.

Next:

- Implement report-input generation after AI structuring has completed for a live task.

## 2026-08-02 Web App Report Input Generation

Completed:

- Added `POST /api/tasks/{task_id}/actions/build-report-input`.
- Added `webapp/backend/app/services/report_input_service.py`.
- Added repository helper `get_task_row` for live task parameter lookup.
- Reused existing `jobuwant.job_report.build_report_input` and `store_report_input`.
- Generated report input is stored in `job_report_inputs` and `data/task_artifacts/{task_id}/report_input.json`.
- Live `GET /api/tasks/{task_id}/report-input` now reads generated artifacts.
- Fixed structuring runner test isolation by replacing background submission in the fake success test.
- Did not start real collection and did not perform model work.

Changed files:

- `webapp/backend/app/api/tasks.py`
- `webapp/backend/app/repositories/analysis_tasks.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/app/services/report_input_service.py`
- `webapp/backend/tests/test_report_input_service.py`
- `webapp/backend/tests/test_structuring_runner.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`
- `docs/SESSION_HANDOFF.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 30 passed, 19 warnings.

Next:

- Implement final report generation behind `POST /api/tasks/{task_id}/actions/write-final-report` after explicit approval for model work.
## 2026-08-02 Web App Final Report Generation

Completed:

- Added `POST /api/tasks/{task_id}/actions/write-final-report`.
- Added `webapp/backend/app/services/final_report_service.py`.
- Added `webapp/backend/app/runner/final_report_runner.py`.
- Reused existing `jobuwant.ai_report_writer` report generation, storage, and usage helpers.
- Final report output is stored in `job_reports` and `data/task_artifacts/{task_id}/final_report.json`.
- Live `GET /api/tasks/{task_id}/report` now reads generated report artifacts.
- Added tests for fake successful final report generation and rejection before report input generation.
- Did not start real collection during verification. Tests did not perform model work.

Changed files:

- `webapp/backend/app/api/tasks.py`
- `webapp/backend/app/runner/final_report_runner.py`
- `webapp/backend/app/services/final_report_service.py`
- `webapp/backend/app/services/task_service.py`
- `webapp/backend/tests/test_final_report_service.py`
- `webapp/docs/API_CONTRACTS.md`
- `webapp/docs/DATA_MODEL.md`
- `webapp/docs/WEB_APP_HARNESS.md`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/backend/README.md`
- `docs/WORKLOG.md`
- `docs/SESSION_HANDOFF.md`

Verification:

- `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 32 passed, 21 warnings.

Next:

- Wire the frontend live workflow controls and status polling for the eight-step flow.
## 2026-08-02 Web App Frontend Live Workflow Wiring

Completed:

- Added frontend API client support for all live write actions.
- Added task creation form on `/tasks`.
- Added Harness-aware next action panel on task detail pages.
- Added polling while live task stages are running.
- Connected sample saving from the sample page.
- Replaced the structure placeholder with live batch status and action controls.
- Started backend at `http://127.0.0.1:8000` and latest frontend preview at `http://127.0.0.1:3001`.
- Did not start a new collection run during verification and did not perform model work.

Changed files:

- `webapp/frontend/src/lib/api.ts`
- `webapp/frontend/src/features/tasks/task-list-page.tsx`
- `webapp/frontend/src/features/tasks/task-workspace.tsx`
- `webapp/frontend/src/features/tasks/sample-confirmation-panel.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `webapp/docs/WORKFLOW.md`
- `webapp/README.md`
- `webapp/frontend/README.md`
- `docs/WORKLOG.md`
- `docs/SESSION_HANDOFF.md`

Verification:

- `npm run lint` passed.
- `npm run typecheck` passed.
- `npm run build` passed.
- Backend tests passed: 32 passed, 21 warnings.
- `GET /api/health` returned 200.
- `GET /tasks` on frontend preview returned 200.

Next:

- Perform a guided browser test of the live workflow with a small task only after the user confirms the exact task parameters and agrees before long-running or model-backed stages.
## 2026-08-03 Web App UI Foundation Pass

Completed:

- Used `web-design-guidelines` for the first UI foundation pass.
- Added shared frontend UI primitives under `webapp/frontend/src/components/ui/shell.tsx`.
- Fixed unreadable Chinese UI copy in the report input preview and final report viewer components.
- Reused the shared panel, metric, empty-state, and button primitives in those report-facing components.
- Did not start new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/components/ui/shell.tsx`
- `webapp/frontend/src/features/tasks/report-input-preview-panel.tsx`
- `webapp/frontend/src/features/tasks/final-report-viewer.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- `npm run typecheck` passed.
- `npm run lint` passed.
- `npm run build` passed.

Next:

- Apply shared page shell and panel primitives to `/tasks` and `/tasks/{taskId}` before deeper per-page layout refactors.

## 2026-08-04 Web App Task Pages Shell Pass

Completed:

- Applied the shared `AppShell`, `PageBody`, status pill, error, empty-state, panel, metric, and button primitives to `/tasks` and the task workspace shell.
- Refactored task workspace summary, stage timeline, artifact, chart, event, metadata, and readonly placeholder panels to use the shared UI foundation where low-risk.
- Kept workflow calls, polling behavior, routes, API contracts, and task action ordering unchanged.
- Started local backend and frontend services only for readonly smoke verification.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/task-list-page.tsx`
- `webapp/frontend/src/features/tasks/task-workspace.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report-input` returned 200.

Next:

- Continue the interface review order with `/tasks/{taskId}/sample`, then `/tasks/{taskId}/structure`, then report input/final report display refinements.

## 2026-08-04 Web App Sample Page Layout Pass

Completed:

- Applied shared `Panel`, `MetricBlock`, `ErrorBanner`, and shared button styles to `/tasks/{taskId}/sample`.
- Removed the local sample-page metric helper in favor of the shared UI primitive.
- Added clearer button icon treatment for refresh and save actions.
- Added accessible labels to the sample filters, row selection checkboxes, and row expand control.
- Kept job loading, filters, selection state, sample save payload, and callback behavior unchanged.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/sample-confirmation-panel.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/sample` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/sample` returned 200.

Next:

- Continue the interface review order with `/tasks/{taskId}/structure`, then revisit report input and final report display refinements.

## 2026-08-04 Web App Structure Page Layout Pass

Completed:

- Applied shared `Panel`, `PanelHeader`, `MetricBlock`, `ErrorBanner`, and shared button styles to `/tasks/{taskId}/structure`.
- Reworked the structure status panel and batch list panel for consistent spacing, heading hierarchy, and shadow treatment with the rest of the task workspace.
- Added a reusable batch table message row and table accessibility attributes.
- Improved long job-id and error-message wrapping inside the batch table.
- Kept status loading, batch planning action, batch execution action, refresh behavior, and parent task refresh callback unchanged.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/task-workspace.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/structure` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/structure` returned 200.

Next:

- Continue with report input and final report display refinements, then do a consolidated visual review across all task routes.

## 2026-08-04 Web App Report Pages Layout Pass

Completed:

- Refined `/tasks/{taskId}/report-input` with shared `PanelHeader`, `ErrorBanner`, metric icons, and consistent chart/card spacing.
- Refined `/tasks/{taskId}/report` with shared `PanelHeader`, `ErrorBanner`, metric icons, and consistent section headers for report-heavy content.
- Kept report input loading, final report loading, refresh behavior, and navigation to report input unchanged.
- Preserved the existing report data parsing helpers and display sections.
- Did not start a new collection and did not call model-backed stages.

Changed files:

- `webapp/frontend/src/features/tasks/report-input-preview-panel.tsx`
- `webapp/frontend/src/features/tasks/final-report-viewer.tsx`
- `webapp/docs/IMPLEMENTATION_RECORD.md`
- `docs/WORKLOG.md`

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report-input` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/report` returned 200.

Next:

- Run a consolidated visual review across all task routes and identify remaining layout polish items before moving into a broader visual redesign pass.

## 2026-08-04 Web App Consolidated UI Review Pass

Completed:

- Ran a consolidated UI consistency review across task list, task detail, sample confirmation, structure, report input, and final report routes using the `web-design-guidelines` checklist.
- Added accessible labels to task search and task/sample tables.
- Added table column scopes to task list and sample confirmation tables.
- Unified the task list detail link with the shared primary button style.
- Replaced the remaining old task detail action panel styling with the shared `Panel` and `ErrorBanner` primitives.
- Added current/selected state semantics to task workspace navigation and task selector controls.
- Kept all API calls, task routing, polling, filtering, sample selection, and workflow action behavior unchanged.
- Did not start a new collection and did not call model-backed stages.

Review findings addressed:

- Table semantics were inconsistent across task list and sample confirmation pages.
- The task detail next-action panel still used the older shadow and local error treatment.
- Current navigation state was visual-only in the task workspace sidebar.

Verification:

- Frontend `npm run typecheck` passed.
- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- `GET http://127.0.0.1:8000/api/health` returned 200.
- `GET http://127.0.0.1:3000/tasks` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/sample` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/structure` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report-input` returned 200.
- `GET http://127.0.0.1:3000/tasks/hz-agent-intern-40/report` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/sample` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/structure` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/report-input` returned 200.
- `GET http://127.0.0.1:3000/tasks/gz-gis-any-30/report` returned 200.

Next:

- Move from shared-component cleanup into a broader visual redesign pass, starting with a concrete visual direction for task workspace density, sidebar behavior, and final report reading layout.
