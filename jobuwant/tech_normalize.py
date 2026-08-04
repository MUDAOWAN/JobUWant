from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from jobuwant.db import DB_PATH, connect, initialize_database


TRIM_RE = re.compile(r"^[\\s,，、/|;；:：()（）\\[\\]{}<>《》\"'`]+|[\\s,，、/|;；:：()（）\\[\\]{}<>《》\"'`]+$")
INNER_SPACE_RE = re.compile(r"\\s+")


class NormalizedTerm(BaseModel):
    canonical: str
    aliases: list[str] = Field(default_factory=list)
    category: str = "unknown"
    reason: str = ""

    @field_validator("canonical")
    @classmethod
    def canonical_required(cls, value: str) -> str:
        cleaned = clean_term(value)
        if not cleaned:
            raise ValueError("canonical is required")
        return cleaned


class NormalizationOutput(BaseModel):
    terms: list[NormalizedTerm] = Field(default_factory=list)


@dataclass(frozen=True)
class TermCandidate:
    term: str
    key: str
    source: str
    job_id: int


def clean_term(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", "" if value is None else str(value))
    normalized = TRIM_RE.sub("", normalized)
    normalized = INNER_SPACE_RE.sub(" ", normalized)
    return normalized.strip()


def term_key(value: object) -> str:
    cleaned = clean_term(value).casefold()
    return cleaned.replace(" ", "")


def collect_terms_for_jobs(conn: sqlite3.Connection, job_ids: list[int]) -> list[TermCandidate]:
    initialize_database(conn)
    if not job_ids:
        return []
    rows = conn.execute(
        f"""
        SELECT
            jd.id,
            jd.technical_keywords_json,
            je.output_json
        FROM job_details jd
        LEFT JOIN job_extractions je ON je.id = (
            SELECT id
            FROM job_extractions
            WHERE job_detail_id = jd.id
              AND status = 'completed'
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
        )
        WHERE jd.id IN ({",".join("?" for _ in job_ids)})
        ORDER BY jd.id
        """,
        tuple(job_ids),
    ).fetchall()
    candidates: list[TermCandidate] = []
    for row in rows:
        job_id = int(row["id"])
        for value in parse_list(row["technical_keywords_json"]):
            add_candidate(candidates, value, "source_skills", job_id)
        output = parse_dict(row["output_json"])
        for section_name in ["technical_stack", "tools_platforms"]:
            for item in output.get(section_name) or []:
                if isinstance(item, dict):
                    add_candidate(candidates, item.get("name"), section_name, job_id)
    return candidates


def summarize_candidates(candidates: list[TermCandidate]) -> dict[str, Any]:
    display_names: dict[str, Counter[str]] = defaultdict(Counter)
    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    job_ids_by_key: dict[str, set[int]] = defaultdict(set)
    for candidate in candidates:
        display_names[candidate.key][candidate.term] += 1
        source_counts[candidate.key][candidate.source] += 1
        job_ids_by_key[candidate.key].add(candidate.job_id)
    rows = []
    for key, job_ids in job_ids_by_key.items():
        rows.append(
            {
                "term": display_names[key].most_common(1)[0][0],
                "key": key,
                "job_count": len(job_ids),
                "sources": dict(source_counts[key]),
            }
        )
    rows.sort(key=lambda item: (-int(item["job_count"]), str(item["term"]).lower()))
    return {"unique_terms": len(rows), "terms": rows}


def build_normalization_prompt(candidates: list[TermCandidate], query: dict[str, str], max_terms: int = 160) -> str:
    summary = summarize_candidates(candidates)
    terms = summary["terms"][:max_terms]
    payload = {
        "query": query,
        "terms": terms,
    }
    return (
        "Return compact JSON only. No Markdown.\n"
        "Normalize job technical terms for this single search result set.\n"
        "Group aliases that mean the same technology, framework, tool, platform, or technical concept.\n"
        "Do not merge different technologies only because they are related.\n"
        "Output shape: {\"terms\":[{\"canonical\":\"Python\",\"aliases\":[\"python3\",\"py\"],\"category\":\"language\",\"reason\":\"same language\"}]}.\n"
        "Use concise canonical names. Keep Chinese concepts in Chinese when that is the common local wording.\n"
        "Input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    )


def apply_normalization(values: list[str], mapping: NormalizationOutput) -> list[str]:
    alias_to_canonical: dict[str, str] = {}
    for item in mapping.terms:
        canonical = clean_term(item.canonical)
        for alias in [item.canonical, *item.aliases]:
            key = term_key(alias)
            if key:
                alias_to_canonical[key] = canonical
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical = alias_to_canonical.get(term_key(value), clean_term(value))
        key = term_key(canonical)
        if canonical and key not in seen:
            seen.add(key)
            output.append(canonical)
    return output


def add_candidate(candidates: list[TermCandidate], value: object, source: str, job_id: int) -> None:
    term = clean_term(value)
    key = term_key(term)
    if not term or not key:
        return
    candidates.append(TermCandidate(term=term, key=key, source=source, job_id=job_id))


def parse_list(value: object) -> list[str]:
    try:
        parsed = json.loads("" if value is None else str(value) or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [clean_term(item) for item in parsed if clean_term(item)]


def parse_dict(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads("" if value is None else str(value) or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect dynamic technical-term candidates.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--job-ids", nargs="*", type=int, default=[])
    parser.add_argument("--query-city", default="")
    parser.add_argument("--query-keyword", default="")
    parser.add_argument("--show-prompt", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    candidates = collect_terms_for_jobs(conn, args.job_ids)
    summary = summarize_candidates(candidates)
    output: dict[str, Any] = {"candidate_summary": summary}
    if args.show_prompt:
        output["normalization_prompt"] = build_normalization_prompt(
            candidates,
            query={"city": args.query_city, "keyword": args.query_keyword},
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
