# Data Policy

Purpose: record data source principles, quality rules, source attribution,
sample-size notes, update time, confidence labels, and cost controls.

Status: initial data principles recorded. Final data source strategy is still
to be decided before implementation.

## Initial Data Principles

- Prioritize structured summaries and necessary fields over long-term storage
  of large raw text blocks.
- Preserve source attribution, update time, and confidence score for each
  structured record.
- Keep enough source metadata to support repeated queries, incremental updates,
  and later trend analysis.
- Track sample count, company count, time range, and confidence distribution in
  every report.
- Make model call count, token usage, estimated cost, cache hit rate, and saved
  token count visible in the product.

## Recommended Saved Item Fields

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

## Incremental Update Policy

For repeated queries such as `Hangzhou + SLAM engineer + autumn hiring`, the
system should identify information that has already been processed, process
only new or changed information, retain historical structured results, and
support future time-based comparison.

## Information Intake And Budget Policy

The first MVP should use a controlled, repeatable intake process:

1. Discover candidate companies and job information for the fixed first scope.
2. Save source metadata and content fingerprints before model processing.
3. Skip unchanged items through `content_hash` comparison.
4. Process only new or changed items.
5. Extract short summaries and structured fields rather than storing large raw
   text blocks as the primary long-term record.
6. Record confidence labels and update timestamps.
7. Generate reports from structured records and summaries.

Every query should be constrained by explicit limits:

- Source item limit
- New or changed item processing limit
- Model call limit
- Input token limit
- Output token limit
- Estimated cost limit
- Per-stage usage counters

Initial first-run budget:

- 20 candidate source records
- 10 new or changed records processed
- 10 model calls
- About CNY 5 estimated cost target

The system should record actual usage during the first run and use that data to
adjust future token and cost limits.

Detailed source priority, company discovery, job-description location,
confidence labels, and update behavior are recorded in
`docs/INFORMATION_INTAKE.md`.

## Company Pool Policy

The first MVP does not require the user to provide a company list. The product
should support a candidate company pool that is gradually built from public
information. Candidate records can later be reviewed, corrected, classified, or
promoted into the main company pool.

Before spending the larger processing budget on job-description lookup, the UI
should show candidate companies and let the user confirm or request another
candidate batch.

## To Be Decided

- MVP data sources
- Source recording format
- Time and sample-size recording
- Confidence labels
- Quality review process
- Cost control process
- Deferred sources
