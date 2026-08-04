# BOSS Data Source Comparison And Resume Notes

Date: 2026-07-15

This document records the BOSS data-source experiments, method comparison, engineering decisions, and resume-ready highlights for the JobUWant project.

## 1. Project Context

JobUWant is a job collection and analysis tool based on:

- Streamlit
- Python
- SQLite
- Simple in-repo harness
- Lightweight local experiments before product integration

The original MVP path was:

`web search -> company official hiring pages -> job text -> SQLite -> analysis/report`

During Phase 2 testing, many company official hiring pages only returned static page shell content through plain HTTP fetch. The browser-visible job text often could not be read directly from static HTML. This made official-page collection slow and inconsistent.

To unblock the MVP, BOSS was tested as the first practical job data source because it provides richer job volume, faster validation, and more stable structured job fields once the session and dynamic parameter flow are handled correctly.

## 2. Tested Methods

### Method A: BossFlow Browser Path

Core idea:

- Use a real Chrome browser context.
- Keep a logged-in Chrome profile.
- Open the search page and detail pages like a normal browser session.
- Read list and detail information from browser-observed responses and page state.

Validated result:

- City: Hangzhou, code `101210100`
- Query: `SLAM`
- List records: 15
- Detail descriptions: 15/15
- Total time: 126.495 seconds
- Output: `ai-param-flow-test/output/bossflow_native_method_timing.json`

Strengths:

- Closest to real browser behavior.
- Useful as a reference path when lightweight HTTP logic is uncertain.
- Good login/profile holder.
- Good fallback collector when lightweight requests fail.

Limitations:

- Slower.
- Heavier runtime dependency.
- Harder to integrate cleanly into the current Streamlit + Python + SQLite product path.
- More sensitive to browser startup, profile state, manual login, and UI timing.

### Method B: Chrome Profile + iv8 + requests Path

Core idea:

- Use Chrome profile only to keep a valid logged-in site session.
- Load current site cookies into an in-memory `requests.Session`.
- Use Python `requests` for list and detail APIs.
- Use `iv8` only when the site returns `code=37`, then generate fresh dynamic session values and retry the current request once.

Validated result:

- City: Hangzhou, code `101210100`
- Query: `SLAM`
- Browser page card count: 15
- List API: HTTP 200, business `code=0`
- Detail descriptions: 15/15
- Profile load: 3.275 seconds
- List request: 0.351 seconds
- Detail requests: 39.817 seconds
- Total time: 45.317 seconds
- Output: `ai-param-flow-test/output/profile_iv8_15_timing_slam_exact.json`

Strengths:

- Much faster than the full browser path.
- Easier to integrate into JobUWant.
- Keeps the main architecture simple.
- Can map output directly into SQLite and later Streamlit UI.
- Handles recoverable `code=37` responses through a controlled retry.

Limitations:

- Still depends on a valid logged-in Chrome profile.
- Needs careful request rhythm and small batches.
- Needs `securityId` from list results for detail retrieval.
- Needs fallback behavior when the session state becomes unsuitable.

## 3. Key Comparison

| Item | BossFlow Browser Path | Chrome Profile + iv8 + requests |
|---|---:|---:|
| Same test query | Hangzhou + SLAM | Hangzhou + SLAM |
| List count | 15 | 15 |
| Detail success | 15/15 | 15/15 |
| Total time | 126.495s | 45.317s |
| Runtime style | Browser-driven | Lightweight Python requests |
| Integration fit | Medium | High |
| Best role | Reference and fallback | Main BOSS source path |

Speed improvement:

- BossFlow browser path: 126.495 seconds
- Chrome profile + iv8 + requests path: 45.317 seconds
- The lightweight path is about 2.8x faster in this validated test.

## 4. Important Technical Findings

### 4.1 Login Session State Was The Main Missing Piece

Early direct `iv8 + requests` tests could retrieve list data in some cases, but details were unstable.

The successful chain showed that dynamic parameter generation alone was not enough. A valid logged-in browser profile and current site session state were also necessary.

Final working chain:

`Chrome profile login -> load current site session -> requests list API -> extract securityId -> requests detail API -> iv8 refresh on code=37 -> normalize JSON -> import into SQLite`

### 4.2 securityId Is Essential For Detail Retrieval

Observed detail API behavior:

- `job/detail.json?securityId=...` succeeded.
- `jobId + lid` alone returned business `code=17`.
- `jobId + lid + securityId` also succeeded.

Conclusion:

- `securityId` should be treated as a required detail key in the BOSS source adapter.

### 4.3 code=37 Is Recoverable

Observed behavior:

- Some detail requests returned business `code=37`.
- The response included `seed`, `name`, and `ts`.
- Downloading `security-js/{name}.js`, generating a fresh encoded value with `iv8`, updating the same session, and retrying only the current request succeeded.

Engineering rule:

- Retry only the current request once.
- Do not mix old and new `seed/name/ts` values.
- Do not print or store session cookie values.

### 4.4 code=35 Should Stop The Batch

Observed behavior:

- `code=35` appeared during earlier unstable tests.
- It was not solved by a simple dynamic parameter refresh.

Engineering rule:

- Treat `code=35` as a stop-or-cool-down signal.
- Avoid repeated probing.
- Keep batches small and request spacing conservative.

## 5. Engineering Improvements

### 5.1 From Official Page First To BOSS First

Problem:

- Official hiring pages are inconsistent.
- Some pages expose only page shell through static HTML.
- Dynamic job text is hard to standardize across many company sites.

Improvement:

- Move BOSS into the first MVP source path.
- Keep official hiring pages as a later enhancement.

Value:

- Faster data volume.
- Easier MVP validation.
- Better input for cleaning, filtering, ranking, and report generation.

### 5.2 From Full Browser Collection To Hybrid Lightweight Collection

Problem:

- Full browser flow works but is slow and harder to productize.

Improvement:

- Use browser only for login/profile.
- Use Python requests for structured list/detail data.
- Use `iv8` only when the site asks for refreshed dynamic session values.

Value:

- Faster.
- Simpler integration.
- Lower runtime complexity.
- Easier to persist into SQLite.

### 5.3 Evidence-First Job Detail Handling

Problem:

- Job list fields are not enough for skill analysis.
- The true requirement text lives in detail descriptions.

Improvement:

- Require detail `postDescription` before treating a record as analysis-ready.
- Store raw description and structured metadata separately.
- Use content hash for future deduplication.

Value:

- Better downstream analysis quality.
- Reduces false positives from weak list-only matches.

## 6. Resume-Ready Highlights

Possible resume bullet points:

- Built a Streamlit + Python + SQLite job intelligence prototype that collects, normalizes, and prepares job data for skill-demand analysis.
- Designed a hybrid BOSS data-source pipeline using Chrome profile session reuse, Python `requests`, and dynamic parameter refresh with `iv8`.
- Improved validated BOSS job-detail retrieval time from 126.5s to 45.3s for a 15-job Hangzhou SLAM test, while keeping 15/15 detail success.
- Identified and solved key data acquisition blockers including missing logged-in session state, missing `securityId`, recoverable `code=37`, and non-recoverable session/rhythm failures.
- Separated browser-based reference collection from lightweight production-oriented collection, reducing integration complexity while keeping a reliable fallback path.
- Established an evidence-first data quality strategy requiring detail-level job descriptions before downstream parsing and analysis.
- Created isolated test modules and work logs to validate risky data-source logic before integrating into the main product.

Shorter version:

- Developed a hybrid BOSS job-data pipeline for JobUWant, combining Chrome profile session reuse with lightweight Python API retrieval and dynamic parameter refresh. Reduced 15-detail test runtime from 126.5s to 45.3s while maintaining 100% detail retrieval in the validated test.

## 7. Innovation Points

### 7.1 Hybrid Browser + Lightweight Request Architecture

Instead of fully relying on browser automation or fully relying on plain HTTP requests, the project uses a hybrid design:

- Browser profile handles login/session continuity.
- Python requests handles fast structured retrieval.
- `iv8` handles dynamic session value refresh only when needed.

This keeps reliability and speed balanced.

### 7.2 Fallback-Oriented Source Strategy

The system does not discard BossFlow after finding a faster method. It assigns different roles:

- BossFlow: reference path, login/profile owner, fallback collector.
- Chrome profile + iv8 + requests: primary lightweight source path.

This makes the architecture more resilient.

### 7.3 Evidence-First Data Quality Gate

The project treats job details as evidence, not just optional enrichment.

A job record should become analysis-ready only when it has:

- Detail text
- Job title
- Company
- City
- Salary or experience fields when available
- Source URL or source identifier
- Content hash

This improves trust in later skill extraction and matching.

## 8. Next Integration Plan

Recommended next steps:

1. Keep BossFlow under `download/BossFlow` as an external reference and fallback tool.
2. Keep BOSS lightweight logic inside an isolated JobUWant adapter module.
3. Add a controlled import path:
   - read BOSS JSON output
   - normalize fields
   - compute content hash
   - save raw detail text and metadata into SQLite
4. Add Streamlit UI source option:
   - official company pages
   - BOSS source
5. Add filtering and scoring:
   - city match
   - keyword match
   - internship/full-time distinction
   - base-city mismatch
   - weak relevance titles
6. Keep small batches until the SQLite import and review UI are stable.

## 9. Future Resume Expansion Angles

If this project continues, the resume story can expand toward:

- Multi-source job intelligence platform
- Data quality scoring for job postings
- Skill-demand trend analysis
- Candidate-to-job matching
- Automated report generation
- Human-reviewable collection workflow
- SQLite-backed local analytics product

