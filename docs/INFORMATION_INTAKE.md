# Information Intake Design

Purpose: define how JobUWant discovers Hangzhou SLAM autumn-hiring companies,
locates relevant job descriptions, records source evidence, and updates results
incrementally under strict cost limits.

Status: initial design accepted on 2026-06-27. No implementation has started.

## Core Principle

The first MVP should not assume it already knows all Hangzhou SLAM employers.
It should build knowledge gradually from public sources, keep evidence for each
record, and prefer official company hiring pages when platform information is
incomplete.

Recruitment platforms are useful lead sources. Company official hiring pages
are higher-confidence evidence when they provide the actual job description.

## Source Types

First-version source priority:

1. Company official hiring pages and official campus hiring pages.
2. Recruitment platform job pages, such as Niuke and BOSS Zhipin, when publicly
   accessible.
3. University employment pages and public recruitment announcements.
4. Community posts or summaries only as discovery leads, not as final evidence
   for job requirements.

The product should record source type and confidence level so the report does
not treat all sources as equally reliable.

## Search Entry And Search API Options

A search entry is the way the product discovers candidate pages before it can
read or analyze any job description. A search API is a programmable service
that accepts a query and returns search results such as title, URL, snippet,
and sometimes page metadata.

The first MVP should prefer an automated search path, but should still keep
budget limits and user confirmation before expensive processing.

Candidate options:

- OpenAI web search tool: useful when the model workflow should perform search
  and reasoning together. It can reduce integration complexity, but search
  behavior and source coverage should be tested carefully for Chinese hiring
  pages.
- Tavily Search API: a developer-oriented search API that is often convenient
  for AI applications and can return concise search results for downstream
  processing.
- Brave Search API: a general web search API option that may be suitable for
  source discovery when coverage is acceptable.
- Google Programmable Search / Custom Search JSON API: possible, but may be
  less attractive for a new MVP because setup and search-engine configuration
  can add friction.
- Manual URL entry: fallback only, not the desired first-version workflow.

First-version plan: compare OpenAI web search and Tavily first with a small
fixed query set, then pick the one that finds better Chinese hiring and company
official pages for Hangzhou SLAM roles. Keep Brave Search, Exa, SerpAPI, and
manual URL entry as later candidates or fallback options.

The comparison should use the same query set and score each source method on:

- Whether it finds official company hiring or campus hiring pages.
- Whether it finds recruitment-platform leads such as Niuke or BOSS Zhipin.
- Whether the results are actually related to Hangzhou.
- Whether the results are actually related to SLAM, localization, mapping,
  robotics, or autonomous driving.
- Whether result metadata is easy to store in SQLite.
- Whether result snippets are enough for first-pass candidate-company
  extraction.
- Cost, response stability, and implementation complexity.

## How The System Learns Which Companies Exist

The system should maintain two company tables conceptually:

- Candidate company pool: companies discovered from public information but not
  yet confirmed or classified.
- Main company pool: companies that have been reviewed, classified, and used in
  reports.

The first MVP does not require the user to provide company names. Candidate
companies can be discovered through controlled queries such as:

- `Hangzhou SLAM engineer campus hiring`
- `Hangzhou SLAM algorithm engineer autumn hiring`
- `Hangzhou robotics SLAM campus hiring`
- `Hangzhou autonomous driving SLAM hiring`
- `company name SLAM campus hiring`

When a source mentions a company and the role appears relevant, the system adds
or updates a candidate company record with:

- Company name
- Possible company category
- Related direction, such as robotics, autonomous driving, intelligent
  manufacturing, UAV, or AR/VR
- City or area
- Matched role keywords
- Evidence URL
- Source type
- First seen time
- Last seen time
- Confidence label

The report should be able to show newly discovered companies since the previous
query.

## Candidate Confirmation Step

Before the product spends the larger processing budget on job-description
lookup and structuring, it should show a candidate-company review step:

- Display discovered company names.
- Show source evidence and matched keywords.
- Show possible company category and related direction when available.
- Indicate whether the company is new, previously known, or already processed.
- Let the user confirm the current candidate set before continuing.
- Let the user request a different batch if the candidates are poor.

After confirmation, the product continues to locate specific SLAM-related job
descriptions for those companies.

The first version should include this screen if implementation time allows,
because it protects the cost budget and makes the automated chain observable.

## How The System Locates A SLAM Job Description

The first version should use a layered process:

1. Start from the fixed query scope: Hangzhou, SLAM engineer / SLAM algorithm
   engineer, campus autumn hiring / early batch, new graduate.
2. Gather up to 20 candidate source records.
3. Identify possible company names and role names from source titles and
   snippets.
4. Prefer sources whose title or visible text includes role terms such as
   `SLAM`, `localization`, `mapping`, `robotics`, `autonomous driving`, or
   equivalent Chinese terms.
5. If a recruitment platform page lacks detailed skill requirements, search for
   the company's official hiring page using the company name and role terms.
6. On an official company hiring page, use visible filters or site search when
   available: city, campus hiring, algorithm, robotics, autonomous driving,
   SLAM, localization, mapping.
7. If no exact SLAM role is found, keep related roles as lower-confidence
   candidates, such as robotics algorithm engineer, autonomous driving
   localization and mapping engineer, perception and localization engineer, or
   motion planning roles that explicitly mention SLAM-related skills.
8. Save the source URL and content fingerprint before model processing.
9. Process only new or changed records within the current budget.

This process should keep the system explainable: every company and job record
should have evidence showing where it came from and why it matched the query.

## Matching Rules

The first MVP should use conservative matching rules before model processing:

- City match: Hangzhou, Zhejiang, or company page location indicating Hangzhou.
- Hiring stage match: campus hiring, autumn hiring, early batch, graduate, or
  new graduate.
- Role match: SLAM engineer, SLAM algorithm engineer, localization and mapping,
  robotics algorithm, autonomous driving localization, or related terms.
- Skill match: C++, Python, ROS, Linux, sensor fusion, visual SLAM, LiDAR SLAM,
  graph optimization, Kalman filtering, bundle adjustment, point cloud
  processing, mapping, localization, simulation, and engineering deployment.

Records that match only weakly should enter the candidate pool, not the final
high-confidence report, until more evidence is found.

## Confidence Levels

Suggested confidence labels:

- High: official company hiring page with clear role, city, hiring stage, and
  skill requirements.
- Medium: recruitment platform page with clear role and requirements, or
  official page with partial role detail.
- Low: announcement, summary, or related role that suggests possible fit but
  lacks complete role requirements.

Confidence should affect report wording. Low-confidence records should be
shown as leads or candidates, not as confirmed job evidence.

## Incremental Update Behavior

Every source item should be recorded with:

- `source_url`
- `source_type`
- `company_name`
- `job_title`
- `city`
- `publish_time`
- `content_hash`
- `structured_fields`
- `summary`
- `confidence_label`
- `first_seen_at`
- `last_seen_at`

On later queries, the system should:

- Skip unchanged records.
- Process only new or changed records.
- Show newly discovered companies.
- Show newly discovered jobs.
- Show changed job descriptions when content fingerprints differ.
- Preserve historical records for later trend analysis.

## First MVP Budget

Confirmed first budget:

- Candidate source records: up to 20 per query.
- New or changed records processed: up to 10 per query.
- Model calls: up to 10 per query.
- Initial per-query cost target: about CNY 5 for the first small-scale run.
- Report export: HTML.
- Local vector store: not included in the first MVP.

The UI should show when limits are reached and should require confirmation
before expanding the batch.

The first run should record actual token usage and estimated cost so later
limits can be adjusted from real measurements instead of guesses.

## Open Design Questions

- Whether OpenAI web search or Tavily should be tested first for source
  discovery.
- Which source types are allowed for automated reading and which should require
  manual URL entry or user confirmation.
- Whether the first version should include a review screen for promoting
  candidate companies into the main company pool.
- Exact default token and estimated-cost limits.
