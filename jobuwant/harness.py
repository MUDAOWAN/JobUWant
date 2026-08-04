from __future__ import annotations

import json
import sqlite3
import time

from jobuwant.config import FirstRunBudget, OpenAISettings, QuerySpec
from jobuwant.job_details import (
    detail_to_json,
    fetch_public_page_text,
    is_acceptable_official_url,
    parse_job_detail_with_openai,
    parse_job_detail_with_rules,
    same_base_domain,
    validate_job_page_text,
)
from jobuwant.models import (
    CandidateCompany,
    DiscoveryResult,
    JobDetailCollectionResult,
    JobLead,
    ParsedJobDetail,
    UsageSnapshot,
)
from jobuwant.search import SampleSearchProvider, SearchProvider


class JobUWantHarness:
    def __init__(
        self,
        conn: sqlite3.Connection,
        budget: FirstRunBudget,
        search_provider: SearchProvider | None = None,
        openai_settings: OpenAISettings | None = None,
    ) -> None:
        self.conn = conn
        self.budget = budget
        self.search_provider = search_provider or SampleSearchProvider()
        self.openai_settings = openai_settings

    def discover_candidates(self, query: QuerySpec) -> DiscoveryResult:
        started_at = time.perf_counter()
        target_count = self.budget.max_changed_records
        batch_size = min(3, target_count)
        max_batches = max(1, min(6, self.budget.max_model_calls or 1))

        sources: list = []
        candidates: list[CandidateCompany] = []
        usage = UsageSnapshot()
        seen_company_keys: set[str] = set()
        seen_domains: set[str] = set()
        seen_urls: set[str] = set()

        for _ in range(max_batches):
            if len(candidates) >= target_count:
                break
            if usage.model_calls >= self.budget.max_model_calls:
                break

            remaining = target_count - len(candidates)
            batch_limit = min(batch_size, remaining)
            try:
                batch_sources, batch_candidates, provider_usage = self.search_provider.discover_companies(
                    query=query,
                    source_limit=min(self.budget.max_candidate_sources, batch_limit),
                    company_limit=batch_limit,
                    exclude_companies=seen_company_keys,
                    exclude_domains=seen_domains,
                )
            except Exception:
                if candidates:
                    break
                raise
            batch_usage = UsageSnapshot(
                candidate_sources=len(batch_sources),
                changed_records=0,
                model_calls=int(provider_usage.get("model_calls", 0)),
                input_tokens=int(provider_usage.get("input_tokens", 0)),
                output_tokens=int(provider_usage.get("output_tokens", 0)),
                estimated_cny=float(provider_usage.get("estimated_cny", 0.0)),
            )
            usage = usage.plus(batch_usage)

            added_this_batch = 0
            for source in batch_sources:
                if source.url in seen_urls:
                    continue
                sources.append(source)
                seen_urls.add(source.url)

            for candidate in batch_candidates:
                company_key = candidate.company_name.strip().lower()
                domain_key = candidate.official_domain.strip().lower()
                url_key = candidate.evidence_url.strip().lower()
                dedupe_key = "|".join([company_key, domain_key, url_key])
                if not company_key or dedupe_key in seen_company_keys:
                    continue
                if domain_key and domain_key in seen_domains:
                    continue
                candidates.append(candidate)
                seen_company_keys.add(company_key)
                seen_company_keys.add(dedupe_key)
                if domain_key:
                    seen_domains.add(domain_key)
                added_this_batch += 1
                if len(candidates) >= target_count:
                    break

            if added_this_batch == 0:
                break

        candidates = candidates[:target_count]
        sources = sources[: self.budget.max_candidate_sources]
        usage = UsageSnapshot(
            candidate_sources=len(sources),
            changed_records=len(candidates),
            model_calls=usage.model_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            estimated_cny=usage.estimated_cny,
        )

        self._store_sources(sources)
        self._store_companies(candidates)
        self._store_usage(stage="candidate_discovery", usage=usage)
        elapsed_seconds = time.perf_counter() - started_at
        return DiscoveryResult(candidates=candidates, sources=sources, usage=usage, elapsed_seconds=elapsed_seconds)

    def collect_job_details(
        self,
        companies: list[CandidateCompany],
        query: QuerySpec,
        company_limit: int = 2,
        lead_limit_per_company: int = 3,
    ) -> JobDetailCollectionResult:
        started_at = time.perf_counter()
        selected_companies = [company for company in companies if company.official_domain_verified][:company_limit]
        max_leads = max(1, company_limit * lead_limit_per_company)
        leads, provider_usage = self.search_provider.discover_job_leads(
            companies=selected_companies,
            query=query,
            lead_limit=company_limit,
        )
        leads = self._filter_official_job_leads(leads, selected_companies)[:max_leads]
        self._store_job_leads(leads)
        usage = UsageSnapshot(
            candidate_sources=len(leads),
            changed_records=0,
            model_calls=int(provider_usage.get("model_calls", 0)),
            input_tokens=int(provider_usage.get("input_tokens", 0)),
            output_tokens=int(provider_usage.get("output_tokens", 0)),
            estimated_cny=float(provider_usage.get("estimated_cny", 0.0)),
        )
        self._store_usage(stage="job_lead_discovery", usage=usage)

        details: list[ParsedJobDetail] = []
        remaining_model_calls = max(0, self.budget.max_model_calls - usage.model_calls)
        for lead in leads:
            raw_text = fetch_public_page_text(lead.url)
            page_quality = validate_job_page_text(raw_text, query)
            if not page_quality["ready_for_parse"]:
                detail = parse_job_detail_with_rules(
                    lead=lead,
                    raw_text=raw_text,
                    query=query,
                    error_message=str(page_quality["notes"]),
                )
                detail = ParsedJobDetail(
                    **{**detail.to_storage_dict(), "status": str(page_quality["status"])}
                )
                job_detail_id = self._store_job_detail(detail)
                self._store_parse_run(
                    lead=lead,
                    detail=detail,
                    job_detail_id=job_detail_id,
                    output_json=detail_to_json(detail),
                    validation_errors=detail.error_message,
                    status=str(page_quality["status"]),
                )
                details.append(detail)
                continue
            if self.openai_settings and raw_text and remaining_model_calls > 0:
                try:
                    detail, parse_usage, output_json, validation_errors = parse_job_detail_with_openai(
                        lead=lead,
                        raw_text=raw_text,
                        query=query,
                        settings=self.openai_settings,
                    )
                except Exception as exc:
                    detail = parse_job_detail_with_rules(
                        lead=lead,
                        raw_text=raw_text,
                        query=query,
                        error_message=str(exc),
                    )
                    parse_usage = UsageSnapshot()
                    output_json = detail_to_json(detail)
                    validation_errors = str(exc)
                remaining_model_calls -= parse_usage.model_calls
                usage = usage.plus(parse_usage)
                job_detail_id = self._store_job_detail(detail)
                self._store_parse_run(
                    lead=lead,
                    detail=detail,
                    job_detail_id=job_detail_id,
                    output_json=output_json,
                    validation_errors=validation_errors,
                    status="completed" if not validation_errors else "needs_review",
                )
                self._store_usage(stage="job_detail_parse", usage=parse_usage)
            else:
                error = "public page text could not be extracted automatically"
                if raw_text and not self.openai_settings:
                    error = "OpenAI settings unavailable; saved rule-only parse"
                detail = parse_job_detail_with_rules(
                    lead=lead,
                    raw_text=raw_text,
                    query=query,
                    error_message=error,
                )
                job_detail_id = self._store_job_detail(detail)
                self._store_parse_run(
                    lead=lead,
                    detail=detail,
                    job_detail_id=job_detail_id,
                    output_json=detail_to_json(detail),
                    validation_errors=detail.error_message,
                    status=detail.status,
                )
            details.append(detail)
        elapsed_seconds = time.perf_counter() - started_at
        return JobDetailCollectionResult(leads=leads, details=details, usage=usage, elapsed_seconds=elapsed_seconds)

    def saved_job_details(self) -> list[dict[str, object]]:
        rows = self.conn.execute(
            """
            SELECT
                company_name,
                job_title,
                city,
                recruitment_stage,
                technical_keywords_json,
                original_url,
                source_type,
                source_confidence,
                parse_confidence,
                review_status,
                collected_at,
                updated_at
            FROM job_details
            ORDER BY updated_at DESC, id DESC
            LIMIT 50
            """
        ).fetchall()
        results: list[dict[str, object]] = []
        for row in rows:
            data = dict(row)
            try:
                keywords = json.loads(str(data.pop("technical_keywords_json") or "[]"))
            except json.JSONDecodeError:
                keywords = []
            data["technical_keywords"] = ", ".join(str(item) for item in keywords)
            results.append(data)
        return results


    def _filter_official_job_leads(
        self, leads: list[JobLead], companies: list[CandidateCompany]
    ) -> list[JobLead]:
        evidence_by_company = {
            company.company_name.strip().lower(): company.evidence_url for company in companies
        }
        filtered: list[JobLead] = []
        seen: set[tuple[str, str]] = set()
        for lead in leads:
            if not is_acceptable_official_url(lead.url):
                continue
            evidence_url = evidence_by_company.get(lead.company_name.strip().lower(), "")
            if evidence_url and not same_base_domain(lead.url, evidence_url):
                continue
            key = (lead.company_name.lower(), lead.url)
            if key in seen:
                continue
            seen.add(key)
            filtered.append(lead)
        return filtered
    def _store_sources(self, sources: list) -> None:
        self.conn.executemany(
            """
            INSERT INTO candidate_sources (title, url, snippet, source_type)
            VALUES (:title, :url, :snippet, :source_type)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                snippet = excluded.snippet,
                source_type = excluded.source_type,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            [source.to_dict() for source in sources],
        )
        self.conn.commit()

    def _store_companies(self, companies: list[CandidateCompany]) -> None:
        self.conn.executemany(
            """
            INSERT INTO candidate_companies (
                company_name,
                possible_category,
                related_direction,
                evidence_url,
                matched_keywords,
                confidence_label,
                official_domain,
                official_domain_verified,
                verification_notes
            )
            VALUES (
                :company_name,
                :possible_category,
                :related_direction,
                :evidence_url,
                :matched_keywords,
                :confidence_label,
                :official_domain,
                :official_domain_verified,
                :verification_notes
            )
            ON CONFLICT(company_name, evidence_url) DO UPDATE SET
                possible_category = excluded.possible_category,
                related_direction = excluded.related_direction,
                matched_keywords = excluded.matched_keywords,
                confidence_label = excluded.confidence_label,
                official_domain = excluded.official_domain,
                official_domain_verified = excluded.official_domain_verified,
                verification_notes = excluded.verification_notes,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            [company.to_dict() for company in companies],
        )
        self.conn.commit()

    def _store_job_leads(self, leads: list[JobLead]) -> None:
        self.conn.executemany(
            """
            INSERT INTO job_leads (
                candidate_company_id,
                company_name,
                job_title_guess,
                url,
                snippet,
                source_type,
                source_confidence,
                status
            )
            VALUES (
                (SELECT id FROM candidate_companies WHERE company_name = :company_name ORDER BY last_seen_at DESC LIMIT 1),
                :company_name,
                :job_title_guess,
                :url,
                :snippet,
                :source_type,
                :source_confidence,
                :status
            )
            ON CONFLICT(company_name, url) DO UPDATE SET
                job_title_guess = excluded.job_title_guess,
                snippet = excluded.snippet,
                source_type = excluded.source_type,
                source_confidence = excluded.source_confidence,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            [lead.to_dict() for lead in leads],
        )
        self.conn.commit()

    def _store_job_detail(self, detail: ParsedJobDetail) -> int:
        payload = detail.to_storage_dict()
        payload["technical_keywords_json"] = json.dumps(detail.technical_keywords, ensure_ascii=True)
        self.conn.execute(
            """
            INSERT INTO job_details (
                job_lead_id,
                candidate_company_id,
                company_name,
                job_title,
                city,
                recruitment_stage,
                responsibilities,
                requirements,
                technical_keywords_json,
                original_url,
                raw_job_text,
                raw_text_hash,
                source_type,
                source_confidence,
                parse_confidence,
                review_status,
                error_message
            )
            VALUES (
                (SELECT id FROM job_leads WHERE company_name = :company_name AND url = :original_url ORDER BY updated_at DESC LIMIT 1),
                (SELECT id FROM candidate_companies WHERE company_name = :company_name ORDER BY last_seen_at DESC LIMIT 1),
                :company_name,
                :job_title,
                :city,
                :recruitment_stage,
                :responsibilities,
                :requirements,
                :technical_keywords_json,
                :original_url,
                :raw_job_text,
                :content_hash,
                :source_type,
                :source_confidence,
                :parse_confidence,
                :status,
                :error_message
            )
            ON CONFLICT(company_name, original_url, raw_text_hash) DO UPDATE SET
                job_title = excluded.job_title,
                city = excluded.city,
                recruitment_stage = excluded.recruitment_stage,
                responsibilities = excluded.responsibilities,
                requirements = excluded.requirements,
                technical_keywords_json = excluded.technical_keywords_json,
                raw_job_text = excluded.raw_job_text,
                source_type = excluded.source_type,
                source_confidence = excluded.source_confidence,
                parse_confidence = excluded.parse_confidence,
                review_status = excluded.review_status,
                error_message = excluded.error_message,
                updated_at = CURRENT_TIMESTAMP
            """,
            payload,
        )
        self.conn.commit()
        row = self.conn.execute(
            """
            SELECT id FROM job_details
            WHERE company_name = ? AND original_url = ? AND raw_text_hash = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (detail.company_name, detail.original_url, detail.content_hash),
        ).fetchone()
        return int(row["id"]) if row else 0

    def _store_parse_run(
        self,
        lead: JobLead,
        detail: ParsedJobDetail,
        job_detail_id: int,
        output_json: str,
        validation_errors: str,
        status: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO parse_runs (
                job_lead_id,
                job_detail_id,
                model_name,
                input_hash,
                input_chars,
                output_json,
                validation_errors,
                parse_confidence,
                status
            )
            VALUES (
                (SELECT id FROM job_leads WHERE company_name = ? AND url = ? ORDER BY updated_at DESC LIMIT 1),
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                lead.company_name,
                lead.url,
                job_detail_id,
                self.openai_settings.model if self.openai_settings else None,
                detail.content_hash,
                len(detail.raw_job_text),
                output_json,
                validation_errors,
                detail.parse_confidence,
                status,
            ),
        )
        self.conn.commit()

    def _store_usage(self, stage: str, usage: UsageSnapshot) -> None:
        if not any([usage.model_calls, usage.input_tokens, usage.output_tokens, usage.estimated_cny]):
            return
        self.conn.execute(
            """
            INSERT INTO usage_events (
                stage,
                model_name,
                model_calls,
                input_tokens,
                output_tokens,
                estimated_cny
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stage,
                self.openai_settings.model if self.openai_settings else None,
                usage.model_calls,
                usage.input_tokens,
                usage.output_tokens,
                usage.estimated_cny,
            ),
        )
        self.conn.commit()



