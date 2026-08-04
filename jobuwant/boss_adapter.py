from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobuwant.db import DB_PATH, connect, initialize_database
from jobuwant.models import ParsedJobDetail




@dataclass(frozen=True)
class NormalizedBossJob:
    company_name: str
    job_title: str
    city: str
    salary: str
    experience: str
    education: str
    recruiter_title: str
    technical_keywords: list[str]
    original_url: str
    raw_job_text: str
    source_type: str
    content_hash: str

    def to_detail(self) -> ParsedJobDetail:
        return ParsedJobDetail(
            company_name=self.company_name,
            job_title=self.job_title,
            city=self.city,
            recruitment_stage=infer_recruitment_stage(self),
            responsibilities="",
            requirements="",
            technical_keywords=self.technical_keywords,
            original_url=self.original_url,
            raw_job_text=self.raw_job_text,
            source_type=self.source_type,
            source_confidence="high" if self.raw_job_text else "low",
            parse_confidence="source_imported",
            content_hash=self.content_hash,
            status="imported",
            error_message="",
        )


@dataclass(frozen=True)
class BossImportResult:
    input_path: Path
    read_count: int
    normalized_count: int
    saved_count: int
    skipped_count: int


def load_boss_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError("BOSS JSON root must be an object")
    return payload


def extract_boss_jobs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("BOSS JSON field 'jobs' must be a list")
    return [job for job in jobs if isinstance(job, dict)]


def normalize_boss_jobs(payload: dict[str, Any], limit: int | None = None) -> list[NormalizedBossJob]:
    jobs = extract_boss_jobs(payload)
    normalized: list[NormalizedBossJob] = []
    for raw_job in jobs:
        if limit is not None and len(normalized) >= limit:
            break
        job = normalize_boss_job(raw_job)
        if job is not None:
            normalized.append(job)
    return normalized


def normalize_boss_job(raw_job: dict[str, Any]) -> NormalizedBossJob | None:
    job_title = _text(raw_job.get("title"))
    company_name = _text(raw_job.get("company"))
    original_url = _text(raw_job.get("url"))
    raw_job_text = _text(raw_job.get('desc'))
    if not company_name or not job_title or not original_url or not raw_job_text:
        return None
    skills = _string_list(raw_job.get("skills"))
    inferred_keywords = []
    technical_keywords = _merge_unique([*skills, *inferred_keywords])

    return NormalizedBossJob(
        company_name=company_name,
        job_title=job_title,
        city=_text(raw_job.get("city")),
        salary=_text(raw_job.get("salary")),
        experience=_text(raw_job.get("exp")),
        education=_text(raw_job.get("edu")),
        recruiter_title=_text(raw_job.get("boss_title")),
        technical_keywords=technical_keywords,
        original_url=original_url,
        raw_job_text=raw_job_text,
        source_type=_text(raw_job.get("_source")) or "boss",
        content_hash=hashlib.sha256(raw_job_text.encode()).hexdigest(),
    )


def infer_recruitment_stage(job: NormalizedBossJob) -> str:
    text = " ".join([job.job_title, job.salary, job.experience, job.raw_job_text]).lower()
    if "intern" in text or "实习" in text or "元/天" in text or "天/周" in text:
        return "intern"
    if "应届" in text or "校招" in text or "毕业" in text:
        return "graduate"
    return "social"


def import_boss_json(conn: sqlite3.Connection, path: Path, limit: int | None = None) -> BossImportResult:
    payload = load_boss_json(path)
    raw_jobs = extract_boss_jobs(payload)
    normalized_jobs = normalize_boss_jobs(payload, limit=limit)
    saved_count = save_boss_jobs(conn, normalized_jobs)
    return BossImportResult(
        input_path=path,
        read_count=len(raw_jobs),
        normalized_count=len(normalized_jobs),
        saved_count=saved_count,
        skipped_count=max(0, len(raw_jobs) - len(normalized_jobs)),
    )


def save_boss_jobs(conn: sqlite3.Connection, jobs: list[NormalizedBossJob]) -> int:
    saved_count = 0
    for job in jobs:
        detail = job.to_detail()
        payload = detail.to_storage_dict()
        payload["technical_keywords_json"] = json.dumps(detail.technical_keywords, ensure_ascii=True)
        payload['source_metadata_json'] = json.dumps({'salary': job.salary, 'experience': job.experience, 'education': job.education, 'recruiter_title': job.recruiter_title, 'raw_source_type': job.source_type}, ensure_ascii=True)
        conn.execute(
            """
            INSERT INTO job_details (
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
                source_metadata_json,
                review_status,
                error_message
            )
            VALUES (
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
                :source_metadata_json,
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
                source_metadata_json = excluded.source_metadata_json,
                review_status = excluded.review_status,
                error_message = excluded.error_message,
                updated_at = CURRENT_TIMESTAMP
            """,
            payload,
        )
        saved_count += 1
    conn.commit()
    return saved_count


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _merge_unique(values: list[str]) -> list[str]:
    merged: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    return merged[:80]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import local BOSS JSON into JobUWant SQLite.")
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    conn = connect(args.db)
    initialize_database(conn)
    result = import_boss_json(conn, args.json_path, limit=args.limit)
    print(
        json.dumps(
            {
                "input_path": str(result.input_path),
                "read_count": result.read_count,
                "normalized_count": result.normalized_count,
                "saved_count": result.saved_count,
                "skipped_count": result.skipped_count,
                "db_path": str(args.db),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
