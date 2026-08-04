# Product Design

Purpose: record product positioning, target users, MVP scope, workflows, report
structure, and features that are intentionally out of scope.

Status: product positioning and initial planning recorded on 2026-06-27.

## Product Positioning

JobUWant is a local web pilot tool for job-search information gathering and
role opportunity analysis. It helps the user analyze a target role, city, and
hiring season by organizing public job information, company information,
hiring requirements, and technical capability requirements into structured and
visual reports.

The first version is for personal use on localhost. A public website can be
considered later after the MVP validates report structure, data strategy,
technical approach, cost controls, and user value.

## First MVP Scope

- City: Hangzhou
- Role: SLAM engineer / SLAM algorithm engineer
- Hiring stage: campus autumn hiring, compatible with early hiring batches
- Candidate status: new graduate
- Target user: the project owner
- Product shape: localhost web pilot tool
- Login: not required in the first version
- Storage: undecided; local database and future cloud database options should
  be compared during technical stack selection

The first MVP should stay narrow. It should solve Hangzhou SLAM campus hiring
well before expanding to general roles and cities.

## Query Entry

The future query entry should support:

- Role name, for example `SLAM engineer`
- Target city, for example `Hangzhou`
- Hiring season, for example `2027 autumn hiring` or `early batch`
- Candidate status, for example `new graduate`
- Optional direction, for example robotics, autonomous driving, intelligent
  manufacturing, UAV, or AR/VR

For the first MVP, these can be fixed to:

- Hangzhou
- SLAM engineer / SLAM algorithm engineer
- Campus autumn hiring / early batch
- New graduate

## Company Opportunity Map

The system should build a company pool around the target city and target role,
then classify companies for comparison.

Company categories include:

- Central or state-owned enterprises / research institutes
- Large private companies
- Small and medium private companies
- Startups
- Foreign companies
- University or research-unit-related roles

The first version should focus on how different Hangzhou SLAM-related company
types differ in technical stack, project experience, education background, and
engineering capability requirements.

## Structured Job Fields

Each job record should try to extract and maintain these fields:

- Company name
- Company category
- City / area
- Job title
- Hiring season / publish time
- Education requirement
- Work experience requirement
- Technical stack
- Algorithm capability requirements
- Engineering capability requirements
- Project experience requirements
- Soft skill requirements
- Salary range, if publicly visible
- Information source
- Update time
- Confidence score

## Technical Stack And Capability Analysis

The first MVP should prioritize technical analysis. The report should cover:

- High-frequency technical stack ranking
- Required skills and bonus skills
- Requirement differences across company categories
- Capability preferences of large companies, small and medium companies,
  startups, research institutes, and foreign companies
- Project capabilities that new graduates should prepare
- Technical keywords that should be emphasized in a resume
- Learning path and improvement suggestions

## Visual Analysis Report

The first report should include:

- Opportunity overview: sample count, company count, time range, and confidence
  distribution
- Company classification: company counts by category and representative
  companies
- Technical stack heatmap: high-frequency technical keywords and frequency
- Company-category comparison: capability requirement differences by category
- Job requirement summary: education, project, algorithm, and engineering
  requirements
- Job-search suggestions: project preparation, resume focus, learning path,
  and application strategy
- Cost panel: model call count, token usage, estimated cost, and cache hit rate

## Incremental Update Mechanism

When the user first queries `Hangzhou + SLAM engineer + autumn hiring`, the
system should organize public job information and save structured results.

When the user runs the same or similar query later:

- Previously processed information should not be processed again.
- Only new or changed information should be analyzed.
- Historical data should be retained for trend comparison.
- Repeated model-call cost should be reduced.
- Time-based change analysis should be possible later.

Recommended fields for each saved information item:

- `source_url`
- `company_name`
- `job_title`
- `city`
- `publish_time`
- `content_hash`
- `structured_fields`
- `summary`
- `first_seen_at`
- `last_seen_at`

## Cost And Token Visibility

Cost visibility is a product highlight, not only an engineering concern. The
local web page should show:

- Input tokens for the current query
- Output tokens for the current query
- Model call count for the current query
- Estimated cost for the current query
- Cache hit rate
- Saved token count
- Processing stages with the highest cost
- Cost share by model

## Deferred Expansion

Record these directions, but do not implement them in the first planning stage:

- Expand from Hangzhou to more cities
- Expand from SLAM to more roles
- Expand from personal localhost tool to public website
- Add resume input for role matching and capability gap analysis
- Add a company knowledge base
- Add role alias normalization
- Add report export
- Add historical trend analysis
- Add multi-model cost optimization strategy

## MVP Success Criteria

The first MVP should be considered useful if it can:

- Produce a credible Hangzhou SLAM campus-hiring opportunity report.
- Clearly compare different company categories.
- Identify high-frequency technical requirements and new-graduate preparation
  priorities.
- Preserve enough structured data for repeated queries and later trend
  analysis.
- Make model usage and cost visible enough to guide future optimization.
