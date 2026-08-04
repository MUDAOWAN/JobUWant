from __future__ import annotations

import json
from typing import Any

from jobuwant.config import OpenAISettings, QuerySpec
from jobuwant.job_details import (
    infer_source_type,
    is_acceptable_official_url,
    score_source_confidence,
    verify_official_company_source,
)
from jobuwant.models import CandidateCompany, CandidateSource, JobLead


class SearchProvider:
    name = "base"

    def search(self, query: QuerySpec, limit: int) -> list[CandidateSource]:
        raise NotImplementedError

    def discover_companies(
        self,
        query: QuerySpec,
        source_limit: int,
        company_limit: int,
        exclude_companies: set[str] | None = None,
        exclude_domains: set[str] | None = None,
    ) -> tuple[list[CandidateSource], list[CandidateCompany], dict[str, int | float]]:
        sources = self.search(query=query, limit=source_limit)
        return sources, [], {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cny": 0.0}

    def discover_job_leads(
        self, companies: list[CandidateCompany], query: QuerySpec, lead_limit: int
    ) -> tuple[list[JobLead], dict[str, int | float]]:
        return [], {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cny": 0.0}


class SampleSearchProvider(SearchProvider):
    name = "sample"

    def search(self, query: QuerySpec, limit: int) -> list[CandidateSource]:
        samples = [
            CandidateSource(
                title="Sample Robotics Campus Hiring - SLAM Algorithm Engineer",
                url="https://example.com/careers/slam-campus",
                snippet="Hangzhou campus hiring role mentioning SLAM, localization, mapping, C++, ROS, and sensor fusion.",
                source_type="company_official",
            ),
            CandidateSource(
                title="Sample Autonomous Driving Company - Localization Mapping",
                url="https://example.org/jobs/localization-mapping",
                snippet="New graduate algorithm role in Hangzhou with localization and mapping requirements.",
                source_type="company_official",
            ),
        ]
        return samples[:limit]

    def discover_companies(
        self,
        query: QuerySpec,
        source_limit: int,
        company_limit: int,
        exclude_companies: set[str] | None = None,
        exclude_domains: set[str] | None = None,
    ) -> tuple[list[CandidateSource], list[CandidateCompany], dict[str, int | float]]:
        sources = self.search(query=query, limit=source_limit)
        excluded_names = {name.strip().lower() for name in (exclude_companies or set()) if name.strip()}
        excluded_domains = {domain.strip().lower() for domain in (exclude_domains or set()) if domain.strip()}
        candidates = [
            CandidateCompany(
                company_name="Sample Robotics",
                possible_category="startup",
                related_direction="robotics official career page",
                evidence_url=sources[0].url,
                matched_keywords="SLAM, localization, mapping, ROS",
                confidence_label="medium",
                official_domain="example.com",
                official_domain_verified=True,
                verification_notes="sample official career page",
            ),
            CandidateCompany(
                company_name="Sample Autonomous Driving",
                possible_category="large_private_company",
                related_direction="autonomous driving official jobs page",
                evidence_url=sources[1].url,
                matched_keywords="localization, mapping, C++",
                confidence_label="medium",
                official_domain="example.org",
                official_domain_verified=True,
                verification_notes="sample official jobs page",
            ),
        ]
        candidates = [
            candidate for candidate in candidates
            if candidate.company_name.lower() not in excluded_names
            and candidate.official_domain.lower() not in excluded_domains
        ][:company_limit]
        return sources, candidates, {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cny": 0.0}

    def discover_job_leads(
        self, companies: list[CandidateCompany], query: QuerySpec, lead_limit: int
    ) -> tuple[list[JobLead], dict[str, int | float]]:
        leads: list[JobLead] = []
        for company in companies[:lead_limit]:
            source_type = infer_source_type(company.evidence_url, "company_official")
            leads.append(
                JobLead(
                    company_name=company.company_name,
                    job_title_guess="SLAM Algorithm Engineer",
                    url=company.evidence_url,
                    snippet=company.related_direction,
                    source_type=source_type,
                    source_confidence=score_source_confidence(source_type, True),
                )
            )
        return leads, {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cny": 0.0}


class OpenAIWebSearchProvider(SearchProvider):
    name = "openai_web_search"

    def __init__(self, settings: OpenAISettings) -> None:
        self.settings = settings

    def discover_companies(
        self,
        query: QuerySpec,
        source_limit: int,
        company_limit: int,
        exclude_companies: set[str] | None = None,
        exclude_domains: set[str] | None = None,
    ) -> tuple[list[CandidateSource], list[CandidateCompany], dict[str, int | float]]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI provider requires the `openai` package. Install dependencies from requirements.txt.") from exc

        client = self._client()
        # Keep the web-search task small. Large official-only searches can run
        # longer than some upstream gateways allow, so Phase 1 validates a small
        # official candidate set first and expands only after the flow is stable.
        max_candidates = min(company_limit, self.settings.max_candidates, 3)
        response = client.responses.create(
            model=self.settings.model,
            tools=[{"type": "web_search", "search_context_size": self.settings.search_context_size}],
            input=self._build_company_prompt(
                query=query,
                max_candidates=max_candidates,
                exclude_companies=exclude_companies or set(),
                exclude_domains=exclude_domains or set(),
            ),
        )
        payload = self._parse_json_payload(getattr(response, "output_text", "") or "")
        candidates = self._parse_candidates(payload, limit=max_candidates)
        candidates = self._filter_excluded_candidates(
            candidates,
            exclude_companies=exclude_companies or set(),
            exclude_domains=exclude_domains or set(),
        )
        if not candidates:
            raise RuntimeError("OpenAI web search returned no verified official company hiring pages. Try again later or loosen official-only constraints.")
        sources = self._sources_from_candidates(candidates, limit=source_limit)
        return sources, candidates, self._extract_usage(response)

    def discover_job_leads(
        self, companies: list[CandidateCompany], query: QuerySpec, lead_limit: int
    ) -> tuple[list[JobLead], dict[str, int | float]]:
        if not companies:
            return [], {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cny": 0.0}
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI provider requires the `openai` package. Install dependencies from requirements.txt.") from exc

        client = self._client()
        response = client.responses.create(
            model=self.settings.model,
            tools=[{"type": "web_search", "search_context_size": self.settings.search_context_size}],
            input=self._build_job_leads_prompt(companies=companies[:lead_limit], query=query),
        )
        payload = self._parse_json_payload(getattr(response, "output_text", "") or "")
        leads = self._parse_job_leads(payload, limit=lead_limit * 3)
        return leads, self._extract_usage(response)

    def _client(self):
        from openai import OpenAI

        client_kwargs = {"api_key": self.settings.api_key}
        if self.settings.base_url:
            client_kwargs["base_url"] = self.settings.base_url
        return OpenAI(**client_kwargs)

    def _build_company_prompt(
        self,
        query: QuerySpec,
        max_candidates: int,
        exclude_companies: set[str],
        exclude_domains: set[str],
    ) -> str:
        exclusion_lines = self._format_company_exclusions(exclude_companies, exclude_domains)
        return f"""
You are helping build a local job-search research tool. Do a quick targeted search for official company hiring sources only.

Find up to {max_candidates} real candidate companies for this query:
- Role: {query.role}
- City: {query.city}
- Hiring stage: {query.hiring_stage}
- Candidate status: {query.candidate_status}

Already collected companies/domains to avoid:
{exclusion_lines}

Rules:
- Return only official company career pages, official company campus hiring pages, or clearly official company hiring systems.
- Prefer pages on the company domain, such as /careers, /jobs, /campus, /join, /hr, or /position.
- Do not return recruitment platforms, school employment boards, content aggregators, forums, news pages, copied job posts, or generic search result pages.
- Good target signals: Hangzhou, Zhejiang, China, campus hiring, graduate hiring, early batch, internship, junior, SLAM, localization, mapping, navigation, robotics, autonomous driving, robot algorithm, or spatial intelligence.
- It is acceptable to return an official company hiring or campus page even when it is not a single job-detail page; Phase 2 will look for concrete jobs later.
- In related_direction, briefly mention the official-source signal and any role/location/stage signal found.
- Use confidence_label high only when the official page itself strongly supports the target; otherwise use medium or low.
- Return JSON only. Do not wrap it in Markdown.

JSON schema:
{{
  "companies": [
    {{
      "company_name": "company name",
      "possible_category": "startup|large_private_company|public_company|research_institute|unknown",
      "related_direction": "why this official source is relevant",
      "evidence_url": "https://official-company-domain-or-official-ats/...",
      "matched_keywords": "comma-separated keywords from the official page",
      "confidence_label": "high|medium|low"
    }}
  ]
}}
""".strip()

    def _build_job_leads_prompt(self, companies: list[CandidateCompany], query: QuerySpec) -> str:
        company_lines = "\n".join(
            f"- {company.company_name}: verified official domain {company.official_domain}; official evidence URL {company.evidence_url}; evidence: {company.related_direction}"
            for company in companies
            if company.official_domain_verified
        )
        return f"""
You are collecting concrete official job-detail leads for JobUWant.

Target query:
- Role: {query.role}
- City: {query.city}
- Hiring stage: {query.hiring_stage}
- Candidate status: {query.candidate_status}

Companies to process:
{company_lines}

Hard source rules:
- Only official company career pages, official company campus hiring pages, or official company ATS pages are allowed.
- Prefer URLs on the verified official domain listed above.
- Do not include third-party recruitment platforms, school employment boards, content aggregators, copied job posts, or generic search result pages.
- Forbidden examples include BOSS, Zhipin, Liepin, 51job, Lagou, Nowcoder, Zhaopin, beBee, WonderCV, LeetCode jobs, school career sites, and university employment sites.
- Do not invent URLs.

Find up to 3 official job-detail or official job-list pages per company. Prefer concrete full job-detail pages over job-list pages.
Return JSON only. Do not wrap it in Markdown.

JSON schema:
{{
  "job_leads": [
    {{
      "company_name": "company name",
      "job_title_guess": "job title or page title",
      "url": "https://official-company-domain-or-official-ats/...",
      "snippet": "why this official page may contain the target job detail",
      "source_type": "company_official|campus_official",
      "source_confidence": "high|medium|low"
    }}
  ]
}}
""".strip()

    def _format_company_exclusions(self, exclude_companies: set[str], exclude_domains: set[str]) -> str:
        lines: list[str] = []
        for name in sorted(name for name in exclude_companies if name):
            lines.append(f"- company: {name}")
        for domain in sorted(domain for domain in exclude_domains if domain):
            lines.append(f"- domain: {domain}")
        return "\n".join(lines) if lines else "- none"

    def _filter_excluded_candidates(
        self,
        candidates: list[CandidateCompany],
        exclude_companies: set[str],
        exclude_domains: set[str],
    ) -> list[CandidateCompany]:
        excluded_names = {name.strip().lower() for name in exclude_companies if name.strip()}
        excluded_domains = {domain.strip().lower() for domain in exclude_domains if domain.strip()}
        filtered: list[CandidateCompany] = []
        for candidate in candidates:
            if candidate.company_name.strip().lower() in excluded_names:
                continue
            if candidate.official_domain.strip().lower() in excluded_domains:
                continue
            filtered.append(candidate)
        return filtered

    def _parse_json_payload(self, text: str) -> dict[str, Any]:
        cleaned = self._extract_json_text(text)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI web search did not return valid JSON.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("OpenAI web search returned an unexpected response shape.")
        return payload

    def _extract_json_text(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise RuntimeError("OpenAI web search returned an empty response.")
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("OpenAI web search returned text without a JSON object.")
        return cleaned[start : end + 1]

    def _parse_candidates(self, payload: dict[str, Any], limit: int) -> list[CandidateCompany]:
        companies = payload.get("companies", [])
        if not isinstance(companies, list):
            return []
        parsed: list[CandidateCompany] = []
        for item in companies:
            if not isinstance(item, dict):
                continue
            evidence_url = str(item.get("evidence_url", "")).strip()
            company_name = str(item.get("company_name", "")).strip()
            if not company_name or not is_acceptable_official_url(evidence_url):
                continue
            related_direction = str(item.get("related_direction", "")).strip()
            matched_keywords = str(item.get("matched_keywords", "")).strip()
            evidence_text = " ".join([related_direction, matched_keywords, company_name, evidence_url])
            official_domain, official_verified, verification_notes = verify_official_company_source(
                company_name=company_name,
                url=evidence_url,
                evidence_text=evidence_text,
            )
            if not official_verified:
                continue
            if not self._is_target_relevant(company_name, related_direction, matched_keywords, evidence_url):
                continue
            parsed.append(
                CandidateCompany(
                    company_name=company_name,
                    possible_category=str(item.get("possible_category", "unknown")).strip() or "unknown",
                    related_direction=related_direction,
                    evidence_url=evidence_url,
                    matched_keywords=matched_keywords,
                    confidence_label=str(item.get("confidence_label", "low")).strip() or "low",
                    official_domain=official_domain,
                    official_domain_verified=official_verified,
                    verification_notes=verification_notes,
                )
            )
            if len(parsed) >= limit:
                break
        return parsed

    def _parse_job_leads(self, payload: dict[str, Any], limit: int) -> list[JobLead]:
        raw_leads = payload.get("job_leads", [])
        if not isinstance(raw_leads, list):
            return []
        parsed: list[JobLead] = []
        seen: set[tuple[str, str]] = set()
        for item in raw_leads:
            if not isinstance(item, dict):
                continue
            company_name = str(item.get("company_name", "")).strip()
            url = str(item.get("url", "")).strip()
            if not company_name or not is_acceptable_official_url(url):
                continue
            key = (company_name.lower(), url)
            if key in seen:
                continue
            seen.add(key)
            source_type = infer_source_type(url, str(item.get("source_type", "company_official")).strip() or "company_official")
            if source_type == "third_party_platform":
                continue
            parsed.append(
                JobLead(
                    company_name=company_name,
                    job_title_guess=str(item.get("job_title_guess", "")).strip(),
                    url=url,
                    snippet=str(item.get("snippet", "")).strip(),
                    source_type=source_type,
                    source_confidence=str(item.get("source_confidence", "")).strip() or score_source_confidence(source_type, False),
                )
            )
            if len(parsed) >= limit:
                break
        return parsed

    def _is_target_relevant(self, company_name: str, related_direction: str, matched_keywords: str, evidence_url: str) -> bool:
        text = " ".join([company_name, related_direction, matched_keywords, evidence_url]).lower()
        role_terms = ["slam", "localization", "mapping", "navigation", "robotics", "perception", "autonomous", "driving", "定位", "建图", "导航", "机器人", "感知", "自动驾驶", "算法"]
        target_terms = ["hangzhou", "zhejiang", "china", "campus", "graduate", "new graduate", "junior", "intern", "early batch", "school recruitment", "杭州", "浙江", "中国", "校招", "校园招聘", "应届", "提前批", "实习"]
        excluded_seniority = ["senior", "staff", "principal", "lead"]
        junior_terms = ["campus", "graduate", "new graduate", "junior", "intern", "校招", "应届", "实习"]
        has_role_signal = any(term in text for term in role_terms)
        has_target_signal = any(term in text for term in target_terms)
        is_senior_only = any(term in text for term in excluded_seniority) and not any(term in text for term in junior_terms)
        return has_role_signal and has_target_signal and not is_senior_only

    def _sources_from_candidates(self, candidates: list[CandidateCompany], limit: int) -> list[CandidateSource]:
        sources: list[CandidateSource] = []
        seen_urls: set[str] = set()
        for candidate in candidates:
            if candidate.evidence_url in seen_urls:
                continue
            seen_urls.add(candidate.evidence_url)
            sources.append(
                CandidateSource(
                    title=f"{candidate.company_name} official hiring evidence",
                    url=candidate.evidence_url,
                    snippet=candidate.related_direction,
                    source_type="company_official",
                )
            )
            if len(sources) >= limit:
                break
        return sources

    def _extract_usage(self, response: Any) -> dict[str, int | float]:
        usage = getattr(response, "usage", None)
        return {
            "model_calls": 1,
            "input_tokens": self._usage_value(usage, "input_tokens"),
            "output_tokens": self._usage_value(usage, "output_tokens"),
            "estimated_cny": self.settings.estimated_cny_per_call,
        }

    def _usage_value(self, usage: Any, key: str) -> int:
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(key, 0) or 0)
        if hasattr(usage, key):
            return int(getattr(usage, key, 0) or 0)
        if hasattr(usage, "model_dump"):
            data = usage.model_dump()
            if isinstance(data, dict):
                return int(data.get(key, 0) or 0)
        return 0
