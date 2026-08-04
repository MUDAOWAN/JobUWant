from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from jobuwant.analysis_budget import AnalysisBudget, resolve_budget, tier_names
from jobuwant.config import OpenAISettings
from jobuwant.db import DB_PATH, connect, initialize_database
from jobuwant.ai_job_insights import extract_json_text, usage_from_response


DEFAULT_SECRETS_PATH = Path(".streamlit") / "secrets.toml"
DEFAULT_SCHEMA_VERSION = "job_extract_v1"
DEFAULT_EXTRACTOR_NAME = "ai_job_extract"
DEFAULT_MAX_TEXT_CHARS_PER_JOB = 2600

RoleIntent = Literal[
    "engineering",
    "algorithm",
    "product",
    "operations",
    "sales_solution",
    "partner_business",
    "intern",
    "other",
    "unclear",
]
Importance = Literal["core", "common", "nice_to_have", "unclear"]
Friendliness = Literal["high", "medium", "low", "unclear"]


class EvidenceItem(BaseModel):
    field: str = ""
    quote: str
    interpretation: str = ""

    @field_validator("quote")
    @classmethod
    def quote_required(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("quote is required")
        return cleaned


class ExtractedItem(BaseModel):
    name: str
    category: str = "unknown"
    importance: Importance = "unclear"
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)

    @field_validator("name")
    @classmethod
    def name_required(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned


class RequirementSummary(BaseModel):
    level: str = "unclear"
    summary: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)


class GraduateFriendliness(BaseModel):
    level: Friendliness = "unclear"
    reason: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)


class ExtractedJob(BaseModel):
    job_id: int
    role_intent: RoleIntent = "unclear"
    normalized_role: str
    role_family: str
    technical_stack: list[ExtractedItem] = Field(default_factory=list)
    tools_platforms: list[ExtractedItem] = Field(default_factory=list)
    business_domains: list[ExtractedItem] = Field(default_factory=list)
    ability_requirements: list[ExtractedItem] = Field(default_factory=list)
    experience_requirements: RequirementSummary
    education_requirements: RequirementSummary
    graduate_friendliness: GraduateFriendliness
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)

    @field_validator("normalized_role", "role_family")
    @classmethod
    def role_text_required(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("role text is required")
        return cleaned

    @model_validator(mode="after")
    def important_sections_need_content(self) -> "ExtractedJob":
        if not self.ability_requirements:
            raise ValueError("ability_requirements must not be empty")
        return self


class BatchExtractionOutput(BaseModel):
    jobs: list[ExtractedJob] = Field(default_factory=list, min_length=1)


@dataclass(frozen=True)
class SourceJob:
    job_id: int
    company_name: str
    job_title: str
    city: str
    salary: str
    experience: str
    education: str
    skills: list[str]
    raw_text_hash: str
    raw_job_text: str
    match_score: float
    match_status: str
    role_intent_hint: str
    query_city: str
    query_keyword: str

    def to_prompt_dict(self, max_text_chars: int) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "query_city": self.query_city,
            "query_keyword": self.query_keyword,
            "company": self.company_name,
            "job_title": self.job_title,
            "city": self.city,
            "salary": self.salary,
            "experience": self.experience,
            "education": self.education,
            "source_skills": self.skills,
            "match_score": self.match_score,
            "match_status": self.match_status,
            "role_intent_hint": self.role_intent_hint,
            "job_text": self.raw_job_text[:max_text_chars],
        }

    def input_hash(self, model_name: str, schema_version: str, max_text_chars: int) -> str:
        payload = {
            "model_name": model_name,
            "schema_version": schema_version,
            "job_id": self.job_id,
            "raw_text_hash": self.raw_text_hash,
            "query_city": self.query_city,
            "query_keyword": self.query_keyword,
            "max_text_chars": max_text_chars,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def load_jobs(
    conn: sqlite3.Connection,
    search_run_id: int,
    source_type: str,
    match_statuses: list[str],
    sample_limit: int,
    include_cached: bool,
    extractor_name: str,
    schema_version: str,
    model_name: str,
    max_text_chars: int,
) -> list[SourceJob]:
    initialize_database(conn)
    if search_run_id > 0:
        rows = conn.execute(
            """
            SELECT
                jd.id,
                jd.company_name,
                jd.job_title,
                jd.city,
                jd.raw_job_text,
                jd.raw_text_hash,
                jd.technical_keywords_json,
                jd.source_metadata_json,
                sri.match_score,
                sri.match_status,
                sri.role_intent,
                jsr.query_city,
                jsr.query_keyword
            FROM job_search_run_items sri
            JOIN job_details jd ON jd.id = sri.job_detail_id
            JOIN job_search_runs jsr ON jsr.id = sri.search_run_id
            WHERE sri.search_run_id = ?
              AND sri.match_status IN ({placeholders})
            ORDER BY sri.match_score DESC, jd.id
            """.format(placeholders=",".join("?" for _ in match_statuses)),
            (search_run_id, *match_statuses),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT
                jd.id,
                jd.company_name,
                jd.job_title,
                jd.city,
                jd.raw_job_text,
                jd.raw_text_hash,
                jd.technical_keywords_json,
                jd.source_metadata_json,
                jd.last_match_score AS match_score,
                jd.last_match_status AS match_status,
                COALESCE((
                    SELECT role_intent
                    FROM job_search_run_items
                    WHERE job_detail_id = jd.id
                    ORDER BY id DESC
                    LIMIT 1
                ), 'unknown') AS role_intent,
                '' AS query_city,
                '' AS query_keyword
            FROM job_details jd
            WHERE jd.source_type = ?
              AND jd.last_match_status IN ({placeholders})
            ORDER BY jd.last_match_score DESC, jd.id
            """.format(placeholders=",".join("?" for _ in match_statuses)),
            (source_type, *match_statuses),
        ).fetchall()

    jobs = [row_to_source_job(row) for row in rows]
    if not include_cached:
        jobs = [
            job for job in jobs
            if not has_cached_extraction(
                conn=conn,
                job=job,
                extractor_name=extractor_name,
                schema_version=schema_version,
                model_name=model_name,
                max_text_chars=max_text_chars,
            )
        ]
    if sample_limit > 0:
        jobs = jobs[:sample_limit]
    return jobs


def count_candidate_jobs(
    conn: sqlite3.Connection,
    search_run_id: int,
    source_type: str,
    match_statuses: list[str],
    sample_limit: int,
) -> int:
    initialize_database(conn)
    placeholders = ",".join("?" for _ in match_statuses)
    if search_run_id > 0:
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM job_search_run_items
            WHERE search_run_id = ?
              AND match_status IN ({placeholders})
            """,
            (search_run_id, *match_statuses),
        ).fetchone()
    else:
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM job_details
            WHERE source_type = ?
              AND last_match_status IN ({placeholders})
            """,
            (source_type, *match_statuses),
        ).fetchone()
    count = int(row["count"] or 0) if row is not None else 0
    if sample_limit > 0:
        return min(count, sample_limit)
    return count


def row_to_source_job(row: sqlite3.Row) -> SourceJob:
    metadata = parse_dict(row["source_metadata_json"])
    return SourceJob(
        job_id=int(row["id"]),
        company_name=text(row["company_name"]),
        job_title=text(row["job_title"]),
        city=text(row["city"]),
        salary=text(metadata.get("salary")),
        experience=text(metadata.get("experience")),
        education=text(metadata.get("education")),
        skills=parse_list(row["technical_keywords_json"]),
        raw_text_hash=text(row["raw_text_hash"]),
        raw_job_text=text(row["raw_job_text"]),
        match_score=float(row["match_score"] or 0),
        match_status=text(row["match_status"]),
        role_intent_hint=text(row["role_intent"]),
        query_city=text(row["query_city"]),
        query_keyword=text(row["query_keyword"]),
    )


def has_cached_extraction(
    conn: sqlite3.Connection,
    job: SourceJob,
    extractor_name: str,
    schema_version: str,
    model_name: str,
    max_text_chars: int,
) -> bool:
    input_hash = job.input_hash(model_name=model_name, schema_version=schema_version, max_text_chars=max_text_chars)
    row = conn.execute(
        """
        SELECT 1
        FROM job_extractions
        WHERE job_detail_id = ?
          AND extractor_name = ?
          AND schema_version = ?
          AND input_hash = ?
          AND status = 'completed'
        LIMIT 1
        """,
        (job.job_id, extractor_name, schema_version, input_hash),
    ).fetchone()
    return row is not None


def extract_jobs_with_openai(
    jobs: list[SourceJob],
    settings: OpenAISettings,
    budget: AnalysisBudget,
    max_text_chars_per_job: int,
    request_timeout: float,
    max_output_tokens: int,
) -> tuple[BatchExtractionOutput, dict[str, int | float], str]:
    if not jobs:
        raise RuntimeError("no jobs to extract")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI extraction requires the `openai` package.") from exc

    client_kwargs: dict[str, Any] = {"api_key": settings.api_key}
    if settings.base_url:
        client_kwargs["base_url"] = settings.base_url
    if request_timeout > 0:
        client_kwargs["timeout"] = request_timeout
    client = OpenAI(**client_kwargs)
    prompt = build_prompt(jobs=jobs, budget=budget, max_text_chars_per_job=max_text_chars_per_job)
    create_kwargs: dict[str, Any] = {"model": settings.model, "input": prompt}
    if max_output_tokens > 0:
        create_kwargs["max_output_tokens"] = max_output_tokens
    response = client.responses.create(**create_kwargs)
    output_json = extract_json_text(getattr(response, "output_text", "") or "")
    try:
        output = BatchExtractionOutput.model_validate_json(output_json)
    except ValidationError as exc:
        raise RuntimeError(f"AI job extraction JSON failed validation: {exc}") from exc
    return output, usage_from_response(response, settings), output_json


def build_prompt(jobs: list[SourceJob], budget: AnalysisBudget, max_text_chars_per_job: int) -> str:
    jobs_json = json.dumps(
        [job.to_prompt_dict(max_text_chars=max_text_chars_per_job) for job in jobs],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        "Return compact JSON only. No Markdown.\n"
        "You extract structured job facts for a job market report.\n"
        "Use the user query fields to normalize each role, but only use job text as evidence.\n"
        "Output exactly this top-level shape: {\"jobs\":[...]}\n"
        "Each job item keys: job_id, role_intent, normalized_role, role_family, technical_stack, "
        "tools_platforms, business_domains, ability_requirements, experience_requirements, "
        "education_requirements, graduate_friendliness, evidence.\n"
        "role_intent choices: engineering, algorithm, product, operations, sales_solution, partner_business, intern, other, unclear.\n"
        "technical_stack/tools_platforms/business_domains/ability_requirements are arrays of objects: "
        "{name, category, importance, evidence:[{field, quote, interpretation}]}.\n"
        "importance choices: core, common, nice_to_have, unclear.\n"
        "experience_requirements and education_requirements are objects: {level, summary, evidence}.\n"
        "graduate_friendliness is {level, reason, evidence}; level choices: high, medium, low, unclear.\n"
        f"Budget tier: {budget.tier}. Keep each job compact.\n"
        f"For each job, technical_stack <= {budget.max_technical_stack_items}, "
        f"tools_platforms <= {budget.max_tools_platforms_items}, "
        f"business_domains <= {budget.max_business_domains_items}, "
        f"ability_requirements <= {budget.max_ability_items}.\n"
        f"For each item, evidence length <= {budget.evidence_per_item}; prefer one exact quote when the budget is 1.\n"
        "Quotes must be exact substrings from job_text or job_title. Avoid stitched or rewritten quotes.\n"
        "Every non-empty conclusion must include short original Chinese quote evidence. Do not invent evidence.\n"
        "If a field is not supported by the text, use empty arrays or unclear.\n"
        "Keep names normalized, for example Python not python3, AI Agent and 智能体 can map to 智能体.\n"
        "Jobs JSON:\n"
        f"{jobs_json}"
    )


def save_extractions(
    conn: sqlite3.Connection,
    jobs: list[SourceJob],
    output: BatchExtractionOutput,
    extractor_name: str,
    schema_version: str,
    model_name: str,
    max_text_chars: int,
) -> dict[str, Any]:
    jobs_by_id = {job.job_id: job for job in jobs}
    saved = 0
    missing_ids: list[int] = []
    for extracted in output.jobs:
        job = jobs_by_id.get(extracted.job_id)
        if job is None:
            missing_ids.append(extracted.job_id)
            continue
        payload = extracted.model_dump()
        evidence_json = json.dumps(collect_evidence(payload), ensure_ascii=True)
        input_hash = job.input_hash(model_name=model_name, schema_version=schema_version, max_text_chars=max_text_chars)
        conn.execute(
            """
            INSERT INTO job_extractions (
                job_detail_id,
                extractor_name,
                schema_version,
                input_hash,
                output_json,
                evidence_json,
                status,
                validation_errors
            )
            VALUES (?, ?, ?, ?, ?, ?, 'completed', '')
            ON CONFLICT(job_detail_id, extractor_name, schema_version, input_hash) DO UPDATE SET
                output_json = excluded.output_json,
                evidence_json = excluded.evidence_json,
                status = excluded.status,
                validation_errors = excluded.validation_errors,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                job.job_id,
                extractor_name,
                schema_version,
                input_hash,
                json.dumps(payload, ensure_ascii=True),
                evidence_json,
            ),
        )
        saved += 1
    conn.commit()
    return {"saved_count": saved, "unexpected_job_ids": missing_ids}


def collect_evidence(value: Any) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if set(["field", "quote"]).issubset(value.keys()):
            evidence.append(value)
        for child in value.values():
            evidence.extend(collect_evidence(child))
    elif isinstance(value, list):
        for item in value:
            evidence.extend(collect_evidence(item))
    return evidence


def store_usage(conn: sqlite3.Connection, model_name: str, usage: dict[str, int | float]) -> None:
    conn.execute(
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
            "ai_job_extract",
            model_name,
            int(usage.get("model_calls", 0) or 0),
            int(usage.get("input_tokens", 0) or 0),
            int(usage.get("output_tokens", 0) or 0),
            float(usage.get("estimated_cny", 0.0) or 0.0),
        ),
    )
    conn.commit()


def load_settings(
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    secrets_path: Path,
    estimated_cny_per_call: float,
) -> OpenAISettings:
    secrets = load_secrets(secrets_path)
    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or secret_text(secrets, "OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in the environment or .streamlit/secrets.toml")
    return OpenAISettings(
        api_key=resolved_api_key,
        base_url=base_url or os.getenv("OPENAI_BASE_URL") or secret_text(secrets, "OPENAI_BASE_URL") or None,
        model=model or os.getenv("OPENAI_MODEL") or secret_text(secrets, "OPENAI_MODEL") or "gpt-5.5",
        estimated_cny_per_call=estimated_cny_per_call,
    )


def load_secrets(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def secret_text(secrets: dict[str, Any], key: str) -> str:
    return text(secrets.get(key))


def parse_list(value: object) -> list[str]:
    try:
        parsed = json.loads(text(value) or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [text(item) for item in parsed if text(item)]


def parse_dict(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads(text(value) or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract structured fields from matched jobs with AI.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--search-run-id", type=int, default=0)
    parser.add_argument("--source-type", default="boss")
    parser.add_argument("--match-status", nargs="*", default=["strong_match"])
    parser.add_argument("--sample-limit", type=int, default=0)
    parser.add_argument("--budget-tier", choices=tier_names(), default="auto")
    parser.add_argument("--max-text-chars-per-job", type=int, default=0)
    parser.add_argument("--extractor-name", default=DEFAULT_EXTRACTOR_NAME)
    parser.add_argument("--schema-version", default=DEFAULT_SCHEMA_VERSION)
    parser.add_argument("--include-cached", action="store_true")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--secrets", type=Path, default=DEFAULT_SECRETS_PATH)
    parser.add_argument("--estimated-cny-per-call", type=float, default=0.1)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    parser.add_argument("--max-output-tokens", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    settings = load_settings(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        secrets_path=args.secrets,
        estimated_cny_per_call=args.estimated_cny_per_call,
    )
    candidate_count = count_candidate_jobs(
        conn=conn,
        search_run_id=args.search_run_id,
        source_type=args.source_type,
        match_statuses=args.match_status,
        sample_limit=args.sample_limit,
    )
    budget = resolve_budget(args.budget_tier, candidate_count)
    sample_limit = args.sample_limit
    if sample_limit <= 0 and budget.max_jobs_for_ai_extraction > 0:
        sample_limit = budget.max_jobs_for_ai_extraction
    max_text_chars = args.max_text_chars_per_job or budget.max_text_chars_per_job
    max_output_tokens = args.max_output_tokens or budget.max_output_tokens
    jobs = load_jobs(
        conn=conn,
        search_run_id=args.search_run_id,
        source_type=args.source_type,
        match_statuses=args.match_status,
        sample_limit=sample_limit,
        include_cached=args.include_cached,
        extractor_name=args.extractor_name,
        schema_version=args.schema_version,
        model_name=settings.model,
        max_text_chars=max_text_chars,
    )
    if not jobs:
        print(json.dumps({"status": "no_jobs", "saved_count": 0}, ensure_ascii=False, indent=2))
        return 0
    output, usage, _raw_json = extract_jobs_with_openai(
        jobs=jobs,
        settings=settings,
        budget=budget,
        max_text_chars_per_job=max_text_chars,
        request_timeout=args.request_timeout,
        max_output_tokens=max_output_tokens,
    )
    save_summary = save_extractions(
        conn=conn,
        jobs=jobs,
        output=output,
        extractor_name=args.extractor_name,
        schema_version=args.schema_version,
        model_name=settings.model,
        max_text_chars=max_text_chars,
    )
    store_usage(conn, model_name=settings.model, usage=usage)
    print(
        json.dumps(
            {
                "status": "completed",
                "search_run_id": args.search_run_id,
                "source_type": args.source_type,
                "requested_jobs": len(jobs),
                "returned_jobs": len(output.jobs),
                "saved_count": save_summary["saved_count"],
                "unexpected_job_ids": save_summary["unexpected_job_ids"],
                "budget": {
                    "tier": budget.tier,
                    "candidate_count": candidate_count,
                    "sample_limit": sample_limit,
                    "max_text_chars_per_job": max_text_chars,
                    "max_output_tokens": max_output_tokens,
                    "evidence_per_item": budget.evidence_per_item,
                },
                "model_name": settings.model,
                "usage": usage,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
