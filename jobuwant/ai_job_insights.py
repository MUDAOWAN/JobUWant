from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, ValidationError, field_validator, model_validator

from jobuwant.config import OpenAISettings
from jobuwant.db import DB_PATH, connect, initialize_database


DEFAULT_OUTPUT = Path("data") / "boss_ai_job_insights.json"
DEFAULT_SECRETS_PATH = Path(".streamlit") / "secrets.toml"
MAX_TEXT_CHARS_PER_JOB = 4500


class EvidenceItem(BaseModel):
    job_id: int
    company: str
    job_title: str = ""
    quote: str
    interpretation: str = ""

    @field_validator("company", "quote")
    @classmethod
    def _required_text(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("evidence company and quote are required")
        return cleaned


class RoleCluster(BaseModel):
    name: str = Field(default="", validation_alias=AliasChoices("name", "cluster", "role_cluster"))
    summary: str = ""
    job_count: int = 0
    job_ids: list[int] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)


class TechnicalStackItem(BaseModel):
    category: str = "other"
    name: str = Field(default="", validation_alias=AliasChoices("name", "skill", "technology"))
    summary: str = ""
    importance: str = Field(default="unclear", description="core|common|nice_to_have|unclear")
    job_count: int = 0
    job_ids: list[int] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)


class AbilityRequirement(BaseModel):
    name: str = Field(default="", validation_alias=AliasChoices("name", "ability"))
    summary: str = ""
    job_count: int = 0
    job_ids: list[int] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)


class ExperienceRequirement(BaseModel):
    name: str = Field(default="", validation_alias=AliasChoices("name", "requirement"))
    summary: str = ""
    job_count: int = 0
    job_ids: list[int] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)


class GraduateFriendliness(BaseModel):
    level: str = Field(description="friendly|mixed|unfriendly|unclear")
    summary: str = ""
    reasons: list[Any] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list, min_length=1)


class AIJobInsightsOutput(BaseModel):
    role_clusters: list[RoleCluster] = Field(default_factory=list)
    technical_stack: list[TechnicalStackItem] = Field(default_factory=list)
    ability_requirements: list[AbilityRequirement] = Field(default_factory=list)
    experience_requirements: list[ExperienceRequirement] = Field(default_factory=list)
    graduate_friendliness: GraduateFriendliness
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _all_sections_have_content(self) -> "AIJobInsightsOutput":
        if not self.role_clusters:
            raise ValueError("role_clusters must not be empty")
        if not self.technical_stack:
            raise ValueError("technical_stack must not be empty")
        if not self.ability_requirements:
            raise ValueError("ability_requirements must not be empty")
        if not self.experience_requirements:
            raise ValueError("experience_requirements must not be empty")
        if not self.evidence:
            raise ValueError("top-level evidence must not be empty")
        return self


@dataclass(frozen=True)
class AnalysisJob:
    job_id: int
    company_name: str
    job_title: str
    city: str
    salary: str
    experience: str
    education: str
    quality_score: int
    raw_job_text: str

    def to_prompt_dict(self, max_text_chars: int) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "company": self.company_name,
            "job_title": self.job_title,
            "city": self.city,
            "salary": self.salary,
            "experience": self.experience,
            "education": self.education,
            "quality_score": self.quality_score,
            "job_text": self.raw_job_text[:max_text_chars],
        }


def load_analysis_jobs(conn: sqlite3.Connection, source_type: str) -> list[AnalysisJob]:
    initialize_database(conn)
    rows = conn.execute(
        """
        SELECT
            id,
            company_name,
            job_title,
            city,
            raw_job_text,
            source_metadata_json,
            quality_score
        FROM job_details
        WHERE source_type = ?
          AND quality_status = 'analysis_ready'
        ORDER BY id
        """,
        (source_type,),
    ).fetchall()
    jobs: list[AnalysisJob] = []
    for row in rows:
        metadata = _parse_metadata(row["source_metadata_json"])
        jobs.append(
            AnalysisJob(
                job_id=int(row["id"]),
                company_name=_text(row["company_name"]),
                job_title=_text(row["job_title"]),
                city=_text(row["city"]),
                salary=_text(metadata.get("salary")),
                experience=_text(metadata.get("experience")),
                education=_text(metadata.get("education")),
                quality_score=int(row["quality_score"] or 0),
                raw_job_text=_text(row["raw_job_text"]),
            )
        )
    return jobs


def analyze_jobs_with_openai(
    jobs: list[AnalysisJob],
    settings: OpenAISettings,
    target_role: str,
    target_city: str,
    max_text_chars_per_job: int = MAX_TEXT_CHARS_PER_JOB,
    request_timeout: float = 120.0,
    max_output_tokens: int = 2500,
) -> tuple[AIJobInsightsOutput, dict[str, int | float], str]:
    if not jobs:
        raise RuntimeError("no analysis-ready jobs found")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI analysis requires the `openai` package.") from exc

    client_kwargs: dict[str, Any] = {"api_key": settings.api_key}
    if settings.base_url:
        client_kwargs["base_url"] = settings.base_url
    if request_timeout > 0:
        client_kwargs["timeout"] = request_timeout
    client = OpenAI(**client_kwargs)
    prompt = build_prompt(
        jobs=jobs,
        target_role=target_role,
        target_city=target_city,
        max_text_chars_per_job=max_text_chars_per_job,
    )
    create_kwargs: dict[str, Any] = {"model": settings.model, "input": prompt}
    if max_output_tokens > 0:
        create_kwargs["max_output_tokens"] = max_output_tokens
    response = client.responses.create(**create_kwargs)
    output_json = extract_json_text(getattr(response, "output_text", "") or "")
    try:
        insights = AIJobInsightsOutput.model_validate_json(output_json)
    except ValidationError as exc:
        raise RuntimeError(f"AI job insights JSON failed validation: {exc}") from exc
    return insights, usage_from_response(response, settings), output_json


def build_prompt(
    jobs: list[AnalysisJob],
    target_role: str,
    target_city: str,
    max_text_chars_per_job: int,
) -> str:
    jobs_json = json.dumps(
        [job.to_prompt_dict(max_text_chars=max_text_chars_per_job) for job in jobs],
        ensure_ascii=False,
        indent=2,
    )
    role = target_role or 'not specified'
    city = target_city or 'not specified'
    return (
        'Return compact JSON only. No Markdown.\n'
        f'Target role: {role}\n'
        f'Target city: {city}\n'
        'Required keys: role_clusters, technical_stack, ability_requirements, experience_requirements, graduate_friendliness, evidence.\n'
        'Every list item must be a JSON object, not a plain string.\n'
        'graduate_friendliness must be a JSON object, not a string.\n'
        'Evidence item fields: job_id, company, job_title, quote, interpretation.\n'
        'technical_stack name must be a concrete skill such as C++, ROS, LiDAR, IMU, Ceres, VIO, or SLAM.\n'
        'Do not return empty name, empty summary, or empty evidence lists.\n'
        'Keep lists short. Use Chinese summaries under 80 Chinese characters.\n'
        'Jobs JSON:\n'
        f'{jobs_json}'
    )

def write_output(
    insights: AIJobInsightsOutput,
    output_path: Path,
    source_type: str,
    model_name: str,
    sample_count: int,
    usage: dict[str, int | float],
) -> None:
    insights_payload = insights.model_dump()
    evidence = insights_payload.get("evidence") or []
    if evidence:
        for section in ("role_clusters", "technical_stack", "ability_requirements", "experience_requirements"):
            for index, item in enumerate(insights_payload.get(section) or []):
                if isinstance(item, dict) and not item.get("evidence"):
                    item["evidence"] = [evidence[index % len(evidence)]]
        graduate_friendliness = insights_payload.get("graduate_friendliness")
        if isinstance(graduate_friendliness, dict) and not graduate_friendliness.get("evidence"):
            graduate_friendliness["evidence"] = [evidence[0]]
    payload = {
        "source_type": source_type,
        "model_name": model_name,
        "sample_count": sample_count,
        "usage": usage,
        "insights": insights_payload,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def store_usage(conn: sqlite3.Connection, model_name: str, usage: dict[str, int | float]) -> None:
    if not any(usage.get(key, 0) for key in ("model_calls", "input_tokens", "output_tokens", "estimated_cny")):
        return
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
            "ai_job_insights",
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
    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or _secret_text(secrets, "OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in the environment or .streamlit/secrets.toml")
    return OpenAISettings(
        api_key=resolved_api_key,
        base_url=base_url or os.getenv("OPENAI_BASE_URL") or _secret_text(secrets, "OPENAI_BASE_URL") or None,
        model=model or os.getenv("OPENAI_MODEL") or _secret_text(secrets, "OPENAI_MODEL") or "gpt-5.5",
        estimated_cny_per_call=estimated_cny_per_call,
    )


def load_secrets(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def extract_json_text(text: str) -> str:
    cleaned = (text or "").strip()
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
        raise RuntimeError("model did not return a JSON object")
    return cleaned[start : end + 1]


def usage_from_response(response: Any, settings: OpenAISettings) -> dict[str, int | float]:
    usage = getattr(response, "usage", None)
    return {
        "model_calls": 1,
        "input_tokens": _usage_value(usage, "input_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
        "estimated_cny": settings.estimated_cny_per_call,
    }


def _usage_value(usage: Any, key: str) -> int:
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


def _parse_metadata(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads(_text(value) or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _secret_text(secrets: dict[str, Any], key: str) -> str:
    return _text(secrets.get(key))


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build AI job insights from JobUWant SQLite.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--source-type", default="boss")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-role", default="")
    parser.add_argument("--target-city", default="")
    parser.add_argument("--sample-limit", type=int, default=0)
    parser.add_argument("--max-text-chars-per-job", type=int, default=MAX_TEXT_CHARS_PER_JOB)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--secrets", type=Path, default=DEFAULT_SECRETS_PATH)
    parser.add_argument("--estimated-cny-per-call", type=float, default=0.1)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    parser.add_argument("--max-output-tokens", type=int, default=2500)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    jobs = load_analysis_jobs(conn, source_type=args.source_type)
    if args.sample_limit > 0:
        jobs = jobs[: args.sample_limit]
    settings = load_settings(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        secrets_path=args.secrets,
        estimated_cny_per_call=args.estimated_cny_per_call,
    )
    insights, usage, _output_json = analyze_jobs_with_openai(
        jobs=jobs,
        settings=settings,
        target_role=args.target_role,
        target_city=args.target_city,
        max_text_chars_per_job=args.max_text_chars_per_job,
        request_timeout=args.request_timeout,
        max_output_tokens=args.max_output_tokens,
    )
    write_output(
        insights=insights,
        output_path=args.output,
        source_type=args.source_type,
        model_name=settings.model,
        sample_count=len(jobs),
        usage=usage,
    )
    store_usage(conn, model_name=settings.model, usage=usage)
    print(
        json.dumps(
            {
                "source_type": args.source_type,
                "sample_count": len(jobs),
                "model_name": settings.model,
                "output": str(args.output),
                "usage": usage,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
