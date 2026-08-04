# Session Handoff

This document helps future sessions quickly understand the project state.

## Current Project State

- Project name: JobUWant
- User goal: build a local web pilot tool for job-search information gathering
  and role opportunity analysis
- Initial user: the project owner
- Possible future shape: public web application
- Formal development environment: WSL2 Ubuntu
- Formal project path: `/home/votally/projects/JobUWant`
- Windows UNC path: `\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant`
- Editor: VS Code
- Git branch: `main`
- GitHub remote: `git@github.com:MUDAOWAN/JobUWant.git`

## Current Phase

MVP phase 1 has been validated: real candidate-company discovery works through the OpenAI web-search provider.

The immediate user preference is to get the local MVP flow running before making
the first Git commit.

As of 2026-06-30, the project has completed a documentation handoff and harness research pass. The current architecture direction remains Streamlit, Python, SQLite, synchronous execution, and a simple in-repo Python harness. Phase 2 should start with a semi-manual job-detail collection flow: candidate job leads, user confirmation, pasted original job text fallback, structured parsing, human review, and SQLite persistence.

## Confirmed First MVP Scope

- City: Hangzhou
- Role: SLAM engineer / SLAM algorithm engineer
- Hiring stage: campus autumn hiring, compatible with early hiring batches
- Candidate status: new graduate
- Product shape: localhost web pilot tool
- Login: not required in the first version
- First technical direction: Streamlit, Python, SQLite, synchronous execution
- Later execution direction: task queue or background job flow when needed

## Completed

- Chose WSL2 Ubuntu for formal development.
- Created the project directory.
- Initialized Git.
- Added GitHub remote.
- Started core documentation.
- Confirmed Windows Codex CLI can operate on project documents through the WSL
  UNC path.
- Recorded first MVP positioning, product scope, report structure,
  incremental update concept, and cost/token visibility requirements.
- Confirmed first MVP technical direction for planning: Streamlit, Python,
  SQLite, and synchronous execution.
- Confirmed the first version should design a repeatable information update
  flow and explicit token/cost constraints.
- Confirmed a JobUWant-specific Codex skill should wait until the development
  workflow is stable.
- Recorded detailed information intake design in
  `docs/INFORMATION_INTAKE.md`, including company discovery, job-description
  location, source confidence, and incremental update behavior.
- Confirmed preference for a mostly automated intake chain with a
  candidate-company confirmation step before deeper job-description processing.
- Confirmed first-run budget direction: 20 candidate sources, 10 new or changed
  records, 10 model calls, and about CNY 5 estimated cost target.
- Recorded initial harness research in `docs/SKILL_RESEARCH.md`.
- Confirmed first MVP should use a simple in-repo Python harness before
  considering OpenAI Agents SDK, LangGraph, or another orchestration framework.
- Added the first local code skeleton with Streamlit entry point, SQLite
  initialization, simple Python harness, sample search provider, candidate
  company preview, usage counters, and HTML report preview.
- Verified Python bytecode compilation and SQLite initialization.
- Created `.venv`, installed Streamlit dependencies, and started the local app
  on `http://localhost:8501`.
- Localized the Streamlit UI, candidate table labels, default query values, and
  preview HTML report labels to Chinese.
- OpenAI web-search provider skeleton has been added behind the existing Python
  harness. It reads credentials from `.streamlit/secrets.toml` and keeps the
  local sample provider available as a fallback.
- OpenAI web-search provider has been tested through the Streamlit UI. The user
  confirmed it can return about 10 real Hangzhou/SLAM-related candidate
  companies, including Hikvision and Unitree.
- The current output is candidate-company evidence and summarized relevance. It
  does not yet fetch or preserve full job-description text exactly as shown on
  hiring pages.


## MVP Phase Status

### Phase 1: Candidate Company Discovery

Status: validated.

The app can take role/city/stage inputs, call the OpenAI web-search provider
through the in-repo Python harness, and return real candidate companies with
evidence links, usage counters, and estimated cost.

### Phase 2: Job Detail Collection

Status: next implementation phase.

Goal: move from "this company appears relevant" to "this company has this
specific role, with this original job description." The next workflow should
fetch or accept job-detail pages and preserve original job text, including:

- company name
- job title
- city
- hiring target, such as campus hiring or new graduate
- responsibilities
- requirements
- technical keywords
- original URL
- original job-description text
- source type and confidence label

Important: search snippets and model summaries are leads, not final evidence.
High-confidence records should keep the original job text or user-provided page
text.

### Phase 3: Multi-Job Analysis And Report

Status: after Phase 2.

Goal: analyze 10-20 preserved job descriptions and produce an integrated report
covering common technical stacks, skill frequency, role clusters, company
differences, new-graduate requirements, and preparation suggestions.

### Technology Direction

Continue developing the MVP in Streamlit for now. Do not switch to a full
frontend/backend stack yet. The main uncertainty is still the information
pipeline and analysis quality, not UI framework capacity. Reconsider FastAPI,
React/Next.js, task queues, and user accounts only after job-detail collection
and multi-job analysis are validated.
## Local Server Startup Notes

Normal foreground command:

```bash
.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Local URL:

```text
http://localhost:8501
```

Startup diagnosis from 2026-06-28:

- The app itself was healthy. A short foreground run reached Streamlit startup and printed the local and network URLs.
- Windows `Start-Process` and WSL `nohup ... &` returned without leaving a Streamlit process or a port 8501 listener.
- In that failure mode, `pgrep -af streamlit` returned no process and `ss -ltnp` did not show `0.0.0.0:8501`.
- The reliable background command was:

```bash
wsl -e bash -lc "cd /home/votally/projects/JobUWant && setsid .venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 > /tmp/jobuwant-streamlit.log 2>&1 < /dev/null & sleep 3 && pgrep -af streamlit && ss -ltnp"
```

Expected result:

- `pgrep -af streamlit` shows the Streamlit process.
- `ss -ltnp` shows `0.0.0.0:8501` owned by Streamlit.
- The browser can open `http://localhost:8501`.
- If `localhost` does not work from Windows, try the WSL network URL printed by a short foreground run.

## Codex CLI File Operation Notes

If a future Codex CLI conversation cannot read or update files through the
Windows UNC working directory, first check whether this is an execution-layer
path handling issue rather than a project problem.

Observed on 2026-06-28:

- Several direct file reads and patch writes against the UNC working directory
  failed before reaching project code.
- WSL read commands such as `wsl -e sed -n ...`, `wsl -e tail -n ...`, and
  `wsl -e grep -n ...` were reliable for inspection.
- `apply_patch` could not read the UNC file path in this environment during the
  session.
- For documentation-only updates, a constrained PowerShell edit against the UNC
  path worked after approval.

Recommended response:

1. Re-read `docs/SESSION_HANDOFF.md` and `docs/WORKLOG.md` first to check
   whether the same issue was already recorded.
2. Use WSL read-only commands for inspection when direct UNC reads fail.
3. Prefer `apply_patch` for normal edits when it can access the workspace.
4. If `apply_patch` cannot access the UNC path, explain the target documents and
   reason, then use a constrained approved edit that touches only those files.
5. Re-check with read-only commands and `git status --short --branch`.
## Next Recommended Steps

1. Implement Phase 2 job-detail collection: fetch or accept job-detail pages,
   preserve original job-description text, and store structured fields.
2. Keep the current candidate-company discovery provider as Phase 1 input to
   Phase 2.
3. Add confidence labels that distinguish official hiring pages, campus pages,
   recruitment platform detail pages, search snippets, and model summaries.
4. After Phase 2 works, implement Phase 3 multi-job analysis and report
   generation over 10-20 preserved job descriptions.
5. Make the first Git commit after the MVP skeleton has been tested and the user
   approves preserving it as the baseline.
6. Test GitHub connection if approved.
7. Push the first commit if approved.

## Important Constraints

- Do not start business code before product positioning and technical analysis.
- Do not install dependencies without approval.
- Do not push to GitHub without approval.
- Keep documenting decisions, work results, and next steps.

## New Conversation Start

For a new Codex CLI conversation, ask the agent to read
`docs/CODEX_CLI_HANDOFF.md` first, then continue from the current phase.


## 2026-07-01 Phase 2 Implementation Note

Phase 2 is now implemented as an automation-first MVP. The Streamlit app can process a limited batch of 1-2 candidate companies, discover candidate job leads, try to read public job-detail page text, parse structured job fields with validation, save raw evidence and parsed fields to SQLite, and display saved job details. Human pasted text remains a fallback for pages that cannot be read automatically.

Verification completed: bytecode compilation, SQLite initialization, Pydantic availability check, and an in-memory sample-provider smoke test.

## 2026-07-01 Current Handoff Summary

Current status:

- MVP Phase 1 candidate-company discovery was validated earlier with OpenAI web search.
- MVP Phase 2 has an automation-first implementation in Streamlit/Python/SQLite.
- The app can discover candidate companies, then process a limited Phase 2 batch of 1-2 companies.
- Phase 2 can search job leads, try to read public job-page text, parse structured fields with OpenAI + Pydantic validation, save raw evidence to SQLite, and display saved job details.
- The app is running at `http://localhost:8501` when started with the documented Streamlit command.

Important recent direction changes:

- Phase 1 and Phase 2 should now use official hiring evidence only.
- Third-party recruitment sites, school employment boards, copied job posts, content aggregators, and generic search pages should not enter final samples.
- Candidate companies now carry `official_domain`, `official_domain_verified`, and `verification_notes`.
- Phase 2 should only process companies whose official domain has been verified.
- Phase 2 job leads should be official URLs and, when possible, share the same base domain as the Phase 1 official evidence URL.
- Current official-domain verification is better than a blocklist-only approach, but it is still a heuristic. A stronger verifier should later fetch and inspect page title/body and handle company-operated external ATS domains more carefully.

Known runtime issue:

- A `524 origin_response_timeout` from `beefapi.com` means the configured upstream API service took longer than Cloudflare's 120-second read window. It is retryable after at least 120 seconds. If it persists, reduce query size or check the configured `OPENAI_BASE_URL` provider stability.

Current implementation files:

- `app.py`: Streamlit UI for Phase 1 discovery and Phase 2 automatic job-detail collection.
- `jobuwant/search.py`: provider interface, sample provider, OpenAI web-search provider, official-only prompts, job-lead discovery.
- `jobuwant/job_details.py`: URL/domain rules, official source verification, page text extraction, text cleaning, rule fallback parsing, OpenAI structured parsing, Pydantic schema, keyword heuristics.
- `jobuwant/harness.py`: workflow orchestration, Phase 1 persistence, Phase 2 job lead/detail/parse-run persistence, usage logging.
- `jobuwant/db.py`: SQLite schema including `candidate_companies`, `job_leads`, `job_details`, `parse_runs`, `usage_events`.
- `jobuwant/models.py`: dataclasses for candidates, leads, parsed details, usage snapshots, and collection results.

Verification already run:

- Python bytecode compilation for `app.py` and `jobuwant` passed.
- SQLite initialization passed with official-domain columns.
- Sample provider in-memory smoke test passed: 2 companies, 2 job leads, 2 job details.
- Rule checks passed: `campus.niuqizp.com` and `bebee.com` are rejected; `unitree.com` is accepted.

Next recommended work:

1. Test OpenAI real search in the browser with a small candidate limit.
2. Confirm whether official-only Phase 1 still finds enough companies.
3. Inspect Phase 2 results for source quality, raw text cleanliness, and parse accuracy.
4. Strengthen official-domain verification if any unverified third-party pages still appear.
5. Add a taxonomy module before expanding beyond SLAM to Agent/backend/frontend/data roles.
6. Keep first Git commit deferred until the user confirms the current MVP baseline is worth preserving.

## 2026-07-03 Current Handoff Summary

Current status:

- Phase 1 official-only candidate company discovery now runs as small-batch OpenAI web search.
- The target company count can be higher than one batch; the harness requests up to 3 companies per web-search call, accumulates unique results, and excludes already collected company names/domains in later batches.
- Browser testing confirmed Phase 1 found 10 official-domain candidate companies. One real run took 782.2 seconds, used 4 model calls, and estimated CNY 0.40.
- Phase 1 and Phase 2 now display elapsed time in the Streamlit metrics area.
- Phase 2 now performs a raw-page-text quality check before model parsing and marks weak pages as `lead_only`.
- A real Phase 2 browser run processed 2 companies / 4 rows in 92.4 seconds.

Important implementation changes:

- `jobuwant/search.py`: OpenAI company discovery supports exclusion lists for already collected companies and domains. It keeps each web-search call small, currently up to 3 companies.
- `jobuwant/harness.py`: Phase 1 loops over small batches, de-duplicates results, records elapsed time, and preserves official-domain fields. Phase 2 records elapsed time and applies the page-text quality gate before parsing.
- `jobuwant/job_details.py`: added `validate_job_page_text` for raw text quality checks before parsing.
- `jobuwant/models.py`: `DiscoveryResult` and `JobDetailCollectionResult` include `elapsed_seconds`.
- `app.py`: Phase 1 and Phase 2 metric rows display elapsed time.

Known behavior from real output review:

- Phase 1 quality is acceptable, but elapsed time can be high because each OpenAI web-search batch may take minutes under official-only constraints. This is mostly provider/search latency, not local SQLite or Python cost.
- Phase 2 raw text is currently retrieved by static HTML fetch (`urllib`) plus simple text extraction. Dynamic recruiting pages may not expose the browser-visible job description in the initial HTML.
- For Unitree, the specific job detail URL was conceptually correct but the stored raw text mostly contained navigation/product shell text, so it produced very few keywords and was marked `lead_only`. The broader Unitree job list URL contained more static job-related text and produced richer keywords despite being more mixed.
- For ArcSoft, the parsed keywords diverged from the browser-visible job description because the stored raw text included site/product/solution content instead of the exact duties and requirements. The browser-visible job text should yield terms such as image processing, computer vision, pattern recognition, PCA, Boosting, SVM, Neural Net, Regression, Haar, Gabor, LBP, SIFT, HOG, C/C++, and deep learning.
- ArcSoft's ATS listing page returned only shell text such as `ArcSoft����`, so it should remain `lead_only` or `needs_text`.

Current priority:

Make Phase 2 evidence-first. The app must verify that `raw_job_text` matches the browser-visible job description before treating any parsed fields or technical keywords as final evidence.

Recommended next work:

1. Separate Phase 2 display into parsed job details and non-final leads (`lead_only`, `needs_text`, weak raw text).
2. Make raw evidence review explicit: show raw text, raw length, quality notes, and parse eligibility before parse results.
3. Add a manual paste fallback for exact browser-visible job descriptions. This is the fastest way to guarantee one-to-one source text before adding heavier page retrieval.
4. Add job-list page handling to isolate a matching job block or follow a detail URL before parsing.
5. If approved later, add a rendered-page retrieval path using Playwright or a similar browser-based fetch method for dynamic official recruiting pages.
6. Later optimize Phase 1 latency with caching, provider split, or a dedicated URL discovery provider.

## 2026-07-15 BOSS Data Source Breakthrough

Current BOSS source direction:

- Use BOSS as the first practical job-detail data source before returning to official-company hiring pages.
- The most promising chain is not pure BossFlow and not pure standalone requests.
- Preferred chain:

```text
Chrome profile login -> load current BOSS session -> requests list API -> extract securityId -> requests detail API -> iv8 refresh on code=37 -> save normalized job JSON -> import into JobUWant SQLite
```

Validated results:

- BossFlow with real Chrome profile retrieved 15 Hangzhou `SLAM����ʦ` jobs and 15/15 detail descriptions.
- Combined `Chrome profile + iv8 + requests` path retrieved the list with `code=0` and then retrieved 5/5 detail descriptions after adding detail-level `code=37` retry handling.
- Detail output is saved at `ai-param-flow-test/output/profile_iv8_detail_batch_retry.json`.
- BossFlow full output is saved at `download/BossFlow/projects/hangzhou_slam/crawl_partial.json`.

Key technical notes:

- `code=37` is recoverable by downloading `security-js/{name}.js`, computing `encodeURIComponent((new window.ABC).z(seed, ts))` in iv8, updating `__zp_stoken__`, `__zp_sseed__`, `__zp_sname__`, and `__zp_sts__`, then retrying the current request once.
- `code=35` is more severe and should be handled by stopping or cooling down, not by repeated retries.
- For detail data, `securityId` is the important field. `jobId + lid` alone returned `code=17`; `securityId` worked.
- BossFlow remains useful as the login/profile holder, real-browser reference, and fallback collector.
- The lightweight `iv8 + requests` path is likely better suited for JobUWant integration once it imports into the existing SQLite/job-detail model.

Next suggested step:

- Build a controlled BOSS JSON import/normalization path into JobUWant before increasing BOSS fetch volume.


## 2026-07-17 AI Dynamic Job Insights Status

A first AI dynamic job-insights MVP is implemented in jobuwant/ai_job_insights.py. It reads BOSS job_details rows with quality_status='analysis_ready', calls the configured OpenAI-compatible Responses API, validates a fixed JSON shape with Pydantic, and writes data/boss_ai_job_insights.json.

Validated run:

`ash
.venv/bin/python -m jobuwant.ai_job_insights --db data/jobuwant.sqlite3 --source-type boss --output data/boss_ai_job_insights.json --target-role SLAM�㷨����ʦ --target-city ���� --max-text-chars-per-job 900 --request-timeout 120 --max-output-tokens 3500
`

Latest result:

- Input sample count: 9 BOSS analysis-ready jobs.
- Output file: data/boss_ai_job_insights.json.
- Model: configured OPENAI_MODEL from .streamlit/secrets.toml.
- Usage from the final run: 1 model call, 5377 input tokens, 1183 output tokens.
- Role clusters: ����/�ഫ����SLAM, �Ӿ�SLAM/VIO, ������/���˻����.
- Technical stack: C++, ROS, LiDAR, IMU, Ceres, VIO, SLAM.
- Graduate friendliness: �е�.

Implementation notes:

- The initial verbose JSON-schema prompt caused long waits. The working version uses a compact prompt plus tolerant validation.
- Do not print API key values. The successful calls only confirmed whether secrets were present and used.
- The analyzer backfills missing item-level evidence from top-level evidence so every displayed section has evidence available.

Recommended next step:

Compare data/boss_ai_job_insights.json with the rule baseline data/boss_job_insights.json, then decide what to expose in Streamlit.


## 2026-07-18 Guangzhou Agent Validation Status

A second city/role validation has been run for Guangzhou + intelligent-agent roles.

Input/search validation:

- City code: 101280100 for Guangzhou.
- Tested list queries: AI Agent, Agent, ������, ��ģ�� Agent, ��ģ��Ӧ��.
- Each tested query returned 15 list rows through the existing BOSS profile request path.
- The selected detail query was ������.

Detail result:

- Output JSON: i-param-flow-test/output/guangzhou_agent_detail_batch_retry.json.
- Detail batch size: 5.
- Detail success count: 5/5.
- One detail request needed a single dynamic-session refresh and then succeeded.

SQLite and analysis result:

- Imported the 5 records into job_details.
- Updated this batch to source_type='boss_gz_agent' so the earlier Hangzhou SLAM records remain separate.
- Quality labels for this batch: 3 nalysis_ready, 2 
eeds_review.
- AI output: data/guangzhou_agent_ai_job_insights.json.
- AI sample count: 3.
- AI usage: 1 model call, 2304 input tokens, 1182 output tokens.

AI summary:

- Role clusters: AI������Ӧ�ù���ʦ, AI����������������, ��������̬�ϻ���.
- Technical stack: Python, TensorFlow, PyTorch, NLP, Dify, Flowise, RPA, MySQL, API.
- Ability requirements: AIӦ�����, ҵ���������, ��Ŀʵʩ����, ���ݷ���, �ͻ���ͨ, ����ѧϰ.
- Graduate friendliness: �е�.

Product implication:

The city + role + BOSS detail + quality label + AI analysis chain is not limited to Hangzhou + SLAM. However, ������ is broad and returns a mixed batch including engineering, product, sales, and partner-style roles. The next product step should add role-intent filtering before final analysis, for example engineering/product/sales/intern/partner categories.


## 2026-07-19 Shenzhen AI Application Validation Status

The user pointed out that BOSS results are influenced by the logged-in profile and query wording. A new validation was run with ���� + AIӦ�ÿ�����.

Validated chain:

`	ext
���� city_code=101280600 + AIӦ�ÿ�����
-> BOSS list request
-> 15 list rows
-> first 3 detail requests
-> 3/3 detail success
-> import into SQLite
-> source_type='boss_sz_ai_app'
-> quality labeling
-> temporary AI include for the 3 requested rows
-> restore quality_status='needs_review'
-> AI analysis output
`

Artifacts:

- Detail output: i-param-flow-test/output/shenzhen_ai_app_detail_batch_retry.json.
- AI output: data/shenzhen_ai_app_ai_job_insights.json.

Imported rows:

- �ֽ�����: AIӦ�ú�˿���ʵϰ��������ʵϰת����
- ����ó��: AIӦ��ʵϰ���������Զ�������
- ����Խ������ó��: AI Ӧ��ʵϰ�����羳����AI�Զ���

Quality result:

- 3 rows were labeled 
eeds_review because all were internship positions.
- The rows were temporarily included in AI analysis to satisfy the 3-job validation request, then restored to 
eeds_review.

AI summary:

- Role clusters: AIӦ�ú�˿���, AI���������Զ���, �羳����AI��Ч.
- Technical stack: Java, Go, Python, Coze, Dify, RPA, RAG, SQL.
- Ability requirements: ҵ���������, ѧϰ�빤����Ӧ, ��ͨЭ��, �ĵ�����, Ч������.
- Graduate friendliness: ��.
- Usage: 1 model call, 2655 input tokens, 1220 output tokens.

Product implication:

This validates that a more specific AI application query produces a more coherent technical/intern batch than broad ������. Future product flow should let users specify intent such as full-time engineering vs internship vs product/sales, and quality gates should support an explicit internship-oriented analysis mode.

## 2026-07-21 Current Pipeline Handoff

The current MVP chain is now:

`job_details -> job_match_score.py -> ai_job_extract.py -> job_report.py -> ai_report_writer.py`

Validated artifacts:

- `data/job_report_input_sz_ai_app.json`
- `data/job_report_input_hz_slam.json`
- `data/job_report_sz_ai_app.json`
- `data/job_report_hz_slam.json`

Validated data:

- ���� + AIӦ�ÿ�����: 3 strong-match internship jobs, final report generated.
- ���� + SLAM: 5 strong-match engineering jobs, final report generated.

Important next design point:

Use sample-size based analysis-budget rules before scaling volume:

- 1-10 jobs: richer per-job extraction, more evidence is acceptable.
- 11-50 jobs: batch extraction, shorter evidence, local aggregation first.
- 51-100 jobs: stricter pre-filtering, shorter per-job text windows, only representative evidence in report input.
- 100+ jobs: stratify/sample by role family and match score, aggregate locally, and avoid sending all raw job text to final report generation.

Next recommended implementation:

Build `analysis_harness.py` to verify the chain end to end. It should check schema stability, token budget, evidence exact-match ratio, report-input size, cache reuse, and output usefulness for the two existing fixtures: ���� + AIӦ�ÿ����� and ���� + SLAM.

## 2026-07-26 Hangzhou Agent Internship Slow Pipeline Update

A parameterized slow collection script has been added:

- `ai-param-flow-test/src/collect_boss_jobs_slow.py`

Validated run:

- Query: Hangzhou city code `101210100`, `Agent����ʦ`, internship job type `1902`.
- Collection output: `ai-param-flow-test/output/hz_agent_intern_40_full_jobs.json`.
- Source type: `boss_hz_agent_intern_20260726_probe40`.
- Collection result: 40 unique list rows, 40 detail attempts, 40 detail successes, 40 import-ready jobs.
- No `code=36` and no check-page state were observed.
- SQLite import: 40/40 saved.
- Valid scoring run: `search_run_id=7`.
- Scoring result: 26 `strong_match`, 14 `review`, 0 `weak_match`.
- Ignore `search_run_id=6`; it was created by a failed shell quoting attempt.
- AI per-job extraction for run 7 completed for all 40 rows in four 10-job batches.
- Report input: `data/job_report_input_hz_agent_intern_probe40.json`, `report_input_id=10`, estimated prompt tokens 17330, evidence exact-match ratio 0.9849.
- Final report: `data/job_report_hz_agent_intern_probe40.json`, `report_id=8`.

Next recommended step:

Review the generated report and decide whether to expose this slow collection + staged analysis path in the Streamlit MVP, including controls for source type, target count, delays, and explicit internship-oriented analysis mode.

## 2026-08-01 Web App Collection Runner Handoff

Current Web App live execution status:

- Live task creation is implemented through `POST /api/tasks`.
- Collection action endpoint is implemented through `POST /api/tasks/{task_id}/actions/start-collection`.
- The collection action now validates task inputs, marks `collect_jobs` as `running`, submits a local one-worker background runner, and returns immediately.
- Runner file: `webapp/backend/app/runner/collection_runner.py`.
- The runner derives city, city code, keyword, job type, expected count, source type, and output path from `analysis_tasks`.
- The runner calls the existing slow BOSS collection script and imports generated JSON through `jobuwant.boss_adapter.import_boss_json`.
- On completion, the runner creates a `job_search_runs` row and records a `search_run` artifact in `task_artifacts` with `related_table='job_search_runs'` and `related_id=<search_run_id>`.
- Live task detail can now expose `search_run_id` and `collected_count` after collection completes.
- Backend tests use fake runner functions and do not perform real collection.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 16 passed, 7 warnings.

Important constraints for the next session:

- Do not call `start-collection` for a new live task unless the user explicitly wants to start a real collection run.
- Do not re-run the validated Hangzhou or Guangzhou fixtures unless the user explicitly asks.
- Do not call model stages unless the user explicitly agrees.

Recommended next implementation step:

- Implement `POST /api/tasks/{task_id}/actions/start-scoring`.
- It should read the latest `search_run` artifact from `task_artifacts`, call the existing local scoring function, write `job_search_run_items`, mark `score_jobs` completed or failed, and update docs/tests.

## 2026-08-01 Web App Local Scoring Handoff

Current live execution status:

- Live task creation is implemented.
- Collection runner boundary is implemented but should not be called unless the user explicitly wants a real collection run.
- Local scoring action is now implemented through `POST /api/tasks/{task_id}/actions/start-scoring`.
- Scoring service file: `webapp/backend/app/services/scoring_service.py`.
- The scoring action reuses the collection `job_search_runs.id` and records a `scored_jobs` artifact.
- Live task detail can now return match-status distribution, role-intent distribution, `analysis_ready_count`, and scored job rows after scoring.
- Rejected scoring before collection completion returns 409 and does not mutate task state.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 18 passed, 9 warnings.

Recommended next implementation step:

- Implement `POST /api/tasks/{task_id}/sample` for sample confirmation writes.
- It should read scored jobs from the task `search_run_id`, validate selected and excluded job ids, write `analysis_samples` and `analysis_sample_items`, mark `confirm_sample` completed, and record a `sample` artifact.

## 2026-08-01 Web App Sample Confirmation Handoff

Current live execution status:

- Live task creation is implemented.
- Collection runner boundary is implemented but should not be called unless the user explicitly wants a real collection run.
- Local scoring action is implemented and does not call any model.
- Sample confirmation is now implemented through `POST /api/tasks/{task_id}/sample`.
- Sample service file: `webapp/backend/app/services/sample_service.py`.
- Sample confirmation validates job ids against the task scoring run, writes `analysis_samples` and `analysis_sample_items`, records a `sample` artifact, and marks `confirm_sample` completed.
- Live job list responses reflect the latest saved sample selection.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 20 passed, 11 warnings.

Recommended next implementation step:

- Implement AI structuring batch execution APIs and runner state.
- Do not make real model calls until the user explicitly approves that stage.

## 2026-08-01 Web App Structuring Batch Plan Handoff

Current live execution status:

- Live task creation is implemented.
- Collection runner boundary is implemented but should not be called unless the user explicitly wants a real collection run.
- Local scoring action is implemented and does not call any model.
- Sample confirmation writes are implemented.
- AI structuring batch planning is now implemented through `POST /api/tasks/{task_id}/actions/start-structuring` and `GET /api/tasks/{task_id}/structure`.
- Structuring service file: `webapp/backend/app/services/structuring_service.py`.
- The start action reads the latest confirmed sample, creates pending `batch_runs`, records a `batch_runs` artifact, and marks `ai_structuring` as `waiting_for_user`.
- No model call is made by the current structuring endpoint.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 24 passed, 15 warnings.

Recommended next implementation step:

- Add actual structuring batch execution only after the user explicitly approves model calls.
- After real structuring is complete, continue to report-input generation.

## 2026-08-01 Web App Structuring Runner Handoff

Current live execution status:

- Live task creation is implemented.
- Collection runner boundary is implemented but should not be called unless the user explicitly wants a real collection run.
- Local scoring action is implemented and does not call any model.
- Sample confirmation writes are implemented.
- AI structuring batch planning is implemented.
- AI structuring batch execution boundary is now implemented through `POST /api/tasks/{task_id}/actions/run-structuring-batches`.
- Runner file: `webapp/backend/app/runner/structuring_runner.py`.
- The execution endpoint resumes an `ai_structuring` stage from `waiting_for_user` to `running`, queues a local one-worker runner, and returns immediately.
- The runner processes pending `batch_runs` sequentially and persists per-batch model, token, cost, timing, and error fields.
- Successful completion records an `extractions` artifact and marks `ai_structuring` completed.
- Tests use fake batch execution and did not call a model.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 28 passed, 17 warnings.

Recommended next implementation step:

- Implement `POST /api/tasks/{task_id}/actions/build-report-input` after a live task has completed AI structuring.

## 2026-08-02 Web App Report Input Generation Handoff

Current live execution status:

- Live task creation is implemented.
- Collection runner boundary is implemented but should not be called unless the user explicitly wants a real collection run.
- Local scoring action is implemented and does not call model work.
- Sample confirmation writes are implemented.
- Structuring batch planning and explicit structuring execution boundary are implemented.
- Report input generation is now implemented through `POST /api/tasks/{task_id}/actions/build-report-input`.
- Service file: `webapp/backend/app/services/report_input_service.py`.
- The action validates completed structuring output, builds the report input through `jobuwant.job_report`, stores `job_report_inputs`, writes `data/task_artifacts/{task_id}/report_input.json`, records a `report_input` artifact, and marks `build_report_input` completed.
- Live `GET /api/tasks/{task_id}/report-input` now reads generated live report input artifacts.
- Tests use seeded fake extraction data and did not perform model work.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 30 passed, 19 warnings.

Recommended next implementation step:

- Implement `POST /api/tasks/{task_id}/actions/write-final-report`.
- This final report step should require explicit approval before any real model work is run.
## 2026-08-02 Web App Final Report Generation Handoff

Current live execution status:

- Live task creation is implemented.
- Collection runner boundary is implemented but should not be called unless the user explicitly wants a real collection run.
- Local scoring action is implemented and does not call model work.
- Sample confirmation writes are implemented.
- Structuring batch planning and explicit structuring execution boundary are implemented.
- Report input generation is implemented.
- Final report generation is now implemented through `POST /api/tasks/{task_id}/actions/write-final-report`.
- Service file: `webapp/backend/app/services/final_report_service.py`.
- Runner file: `webapp/backend/app/runner/final_report_runner.py`.
- The action validates a generated report input, marks `write_final_report` running, queues the local runner, stores `job_reports`, writes `data/task_artifacts/{task_id}/final_report.json`, records a `report` artifact, and enables live `GET /api/tasks/{task_id}/report`.
- Tests use a fake report writer and did not perform model work.

Verification:

- Command: `cd /home/votally/projects/JobUWant/webapp/backend && PYTHONPATH=. /home/votally/projects/JobUWant/.venv/bin/pytest -q`
- Result: 32 passed, 21 warnings.

Recommended next implementation step:

- Wire frontend live workflow controls and polling for the eight-step backend flow.
- Keep UI polish after the real chain can be driven from the browser.
## 2026-08-02 Web App Frontend Live Workflow Handoff

Current frontend live workflow status:

- `/tasks` can create a live task through the backend.
- `/tasks/{taskId}` shows a Harness-aware next action panel.
- The task detail page polls while a live task stage is running.
- `/tasks/{taskId}/sample` can save selected job ids for live tasks.
- `/tasks/{taskId}/structure` now shows live batch status and can start planning or execution actions.
- `/tasks/{taskId}/report-input` and `/tasks/{taskId}/report` continue to read generated artifacts.
- Fixture tasks remain read-only.

Verification:

- Frontend lint passed.
- Frontend typecheck passed.
- Frontend production build passed.
- Backend tests passed: 32 passed, 21 warnings.
- Backend is available at `http://127.0.0.1:8000` in this session.
- Latest frontend preview is available at `http://127.0.0.1:3001/tasks` in this session.

Important constraints:

- Do not start a new collection run unless the user explicitly confirms the task parameters.
- Do not run model-backed stages unless the user explicitly agrees at that step.

Recommended next implementation step:

- Browser-test the live workflow end to end with a small user-approved task, then refine button disabled states and UI copy based on what happens in the real run.