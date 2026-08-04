from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobuwant.analysis_budget import budget_for_job_count
from jobuwant.db import DB_PATH, connect, initialize_database
from jobuwant.tech_normalize import clean_term, term_key


DEFAULT_OUTPUT_DIR = Path("data")
DEFAULT_REPORT_TYPE = "job_market_v1"
MAX_QUOTE_CHARS = 90


@dataclass(frozen=True)
class ExtractedJobRow:
    job_id: int
    company_name: str
    job_title: str
    city: str
    raw_job_text: str
    match_score: float
    match_status: str
    query_city: str
    query_keyword: str
    source_type: str
    salary: str
    experience: str
    education: str
    source_skills: list[str]
    output: dict[str, Any]


@dataclass
class FrequencyBucket:
    name: str
    category: str
    count: int = 0
    job_ids: set[int] | None = None
    evidence: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.job_ids is None:
            self.job_ids = set()
        if self.evidence is None:
            self.evidence = []

    def add(self, row: ExtractedJobRow, item: dict[str, Any], max_evidence: int) -> None:
        assert self.job_ids is not None
        assert self.evidence is not None
        if row.job_id not in self.job_ids:
            self.count += 1
            self.job_ids.add(row.job_id)
        if len(self.evidence) >= max_evidence:
            return
        for ev in item.get("evidence") or []:
            quote = text(ev.get("quote"))
            if not quote:
                continue
            self.evidence.append(
                {
                    "job_id": row.job_id,
                    "company": row.company_name,
                    "job_title": row.job_title,
                    "field": text(ev.get("field")),
                    "quote": compact_quote(quote),
                    "quote_exact_match": quote in row.raw_job_text or quote in row.job_title,
                }
            )
            break

    def to_dict(self, total_jobs: int) -> dict[str, Any]:
        assert self.job_ids is not None
        assert self.evidence is not None
        return {
            "name": self.name,
            "category": self.category,
            "count": self.count,
            "ratio": round(self.count / total_jobs, 4) if total_jobs else 0,
            "job_ids": sorted(self.job_ids),
            "evidence": self.evidence,
        }


def build_report_input(
    conn: sqlite3.Connection,
    search_run_id: int,
    source_type: str,
    match_statuses: list[str],
    top_n: int,
    max_evidence_per_item: int,
    job_ids: list[int] | None = None,
) -> dict[str, Any]:
    initialize_database(conn)
    rows = load_extracted_rows(
        conn=conn,
        search_run_id=search_run_id,
        source_type=source_type,
        match_statuses=match_statuses,
    )
    if job_ids:
        wanted_ids = set(job_ids)
        rows = [row for row in rows if row.job_id in wanted_ids]
        missing_ids = sorted(wanted_ids - {row.job_id for row in rows})
        if missing_ids:
            raise RuntimeError(f"job_ids not found in extracted rows: {missing_ids}")
    if not rows:
        raise RuntimeError("no extracted jobs found for report input")

    query_city = first_non_empty([row.query_city for row in rows])
    query_keyword = first_non_empty([row.query_keyword for row in rows])
    resolved_source_type = first_non_empty([row.source_type for row in rows]) or source_type

    role_intent_counts = Counter(text(row.output.get("role_intent")) or "unclear" for row in rows)
    role_family_counts = Counter(text(row.output.get("role_family")) or "unclear" for row in rows)
    normalized_role_counts = Counter(text(row.output.get("normalized_role")) or "unclear" for row in rows)
    graduate_counts = Counter(
        text((row.output.get("graduate_friendliness") or {}).get("level")) or "unclear" for row in rows
    )

    budget = budget_for_job_count(len(rows))
    effective_top_n = top_n if top_n > 0 else budget.top_technical_stack
    effective_evidence_per_item = max_evidence_per_item if max_evidence_per_item > 0 else min(1, budget.evidence_per_item)

    technical_stack = aggregate_items(rows, "technical_stack", effective_top_n, effective_evidence_per_item)
    tools_platforms = aggregate_items(rows, "tools_platforms", effective_top_n, effective_evidence_per_item)
    business_domains = aggregate_items(rows, "business_domains", effective_top_n, effective_evidence_per_item)
    ability_requirements = aggregate_items(rows, "ability_requirements", budget.top_ability_requirements, effective_evidence_per_item)
    technical_terms_top = aggregate_technical_terms(rows, budget.top_technical_stack, effective_evidence_per_item)
    technical_terms_layers = layer_technical_terms(technical_terms_top, total_jobs=len(rows))
    salary_summary = summarize_salary(rows)
    representative_jobs = build_representative_jobs(rows, max_jobs=min(12, len(rows)), top_terms=technical_terms_top[:8])
    experience = aggregate_requirement(rows, "experience_requirements", effective_evidence_per_item)
    education = aggregate_requirement(rows, "education_requirements", effective_evidence_per_item)
    evidence_quality = summarize_evidence_quality(rows)

    payload = {
        "report_type": DEFAULT_REPORT_TYPE,
        "query": {
            "search_run_id": search_run_id or None,
            "source_type": resolved_source_type,
            "city": query_city,
            "keyword": query_keyword,
            "match_statuses": match_statuses,
        },
        "sample": {
            "total_jobs": len(rows),
            "job_ids": [row.job_id for row in rows],
            "match_score_average": round(sum(row.match_score for row in rows) / len(rows), 2),
            "role_intent_distribution": counter_to_list(role_intent_counts, len(rows)),
            "role_family_distribution": counter_to_list(role_family_counts, len(rows)),
            "normalized_role_distribution": counter_to_list(normalized_role_counts, len(rows)),
            "graduate_friendliness_distribution": counter_to_list(graduate_counts, len(rows)),
        },
        "budget": {
            "tier": budget.tier,
            "report_token_budget": budget.report_token_budget,
            "top_technical_stack": budget.top_technical_stack,
            "top_ability_requirements": budget.top_ability_requirements,
            "max_report_evidence": budget.max_report_evidence,
            "evidence_per_item": effective_evidence_per_item,
        },
        "technical_terms_top": technical_terms_top,
        "technical_terms_layers": technical_terms_layers,
        "salary_summary": salary_summary,
        "representative_jobs": representative_jobs,
        "technical_stack_frequency": technical_stack,
        "tools_platforms_frequency": tools_platforms,
        "business_domains_frequency": business_domains,
        "ability_requirements_frequency": ability_requirements,
        "experience_summary": experience,
        "education_summary": education,
        "evidence_quality": evidence_quality,
        "evidence_pack": build_evidence_pack(
            [technical_stack, tools_platforms, business_domains, ability_requirements],
            max_items=budget.max_report_evidence,
        ),
    }
    payload["input_hash"] = report_hash(payload)
    payload["estimated_prompt_tokens"] = estimate_tokens(payload)
    return payload


def load_extracted_rows(
    conn: sqlite3.Connection,
    search_run_id: int,
    source_type: str,
    match_statuses: list[str],
) -> list[ExtractedJobRow]:
    placeholders = ",".join("?" for _ in match_statuses)
    if search_run_id > 0:
        params: tuple[Any, ...] = (search_run_id, *match_statuses)
        sql = f"""
            SELECT
                jd.id AS job_id,
                jd.company_name,
                jd.job_title,
                jd.city,
                jd.raw_job_text,
                jd.technical_keywords_json,
                jd.source_metadata_json,
                sri.match_score,
                sri.match_status,
                jsr.query_city,
                jsr.query_keyword,
                jsr.source_type,
                je.output_json
            FROM job_search_run_items sri
            JOIN job_search_runs jsr ON jsr.id = sri.search_run_id
            JOIN job_details jd ON jd.id = sri.job_detail_id
            JOIN job_extractions je ON je.id = (
                SELECT id
                FROM job_extractions
                WHERE job_detail_id = jd.id
                  AND status = 'completed'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
            )
            WHERE sri.search_run_id = ?
              AND sri.match_status IN ({placeholders})
            ORDER BY sri.match_score DESC, jd.id
        """
    else:
        params = (source_type, *match_statuses)
        sql = f"""
            SELECT
                jd.id AS job_id,
                jd.company_name,
                jd.job_title,
                jd.city,
                jd.raw_job_text,
                jd.technical_keywords_json,
                jd.source_metadata_json,
                jd.last_match_score AS match_score,
                jd.last_match_status AS match_status,
                '' AS query_city,
                '' AS query_keyword,
                jd.source_type,
                je.output_json
            FROM job_details jd
            JOIN job_extractions je ON je.id = (
                SELECT id
                FROM job_extractions
                WHERE job_detail_id = jd.id
                  AND status = 'completed'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
            )
            WHERE jd.source_type = ?
              AND jd.last_match_status IN ({placeholders})
            ORDER BY jd.last_match_score DESC, jd.id
        """
    rows = conn.execute(sql, params).fetchall()
    return [
        ExtractedJobRow(
            job_id=int(row["job_id"]),
            company_name=text(row["company_name"]),
            job_title=text(row["job_title"]),
            city=text(row["city"]),
            raw_job_text=text(row["raw_job_text"]),
            match_score=float(row["match_score"] or 0),
            match_status=text(row["match_status"]),
            query_city=text(row["query_city"]),
            query_keyword=text(row["query_keyword"]),
            source_type=text(row["source_type"]),
            salary=text(parse_dict(row["source_metadata_json"]).get("salary")),
            experience=text(parse_dict(row["source_metadata_json"]).get("experience")),
            education=text(parse_dict(row["source_metadata_json"]).get("education")),
            source_skills=parse_list(row["technical_keywords_json"]),
            output=parse_dict(row["output_json"]),
        )
        for row in rows
    ]


def aggregate_items(
    rows: list[ExtractedJobRow],
    field_name: str,
    top_n: int,
    max_evidence_per_item: int,
) -> list[dict[str, Any]]:
    buckets: dict[str, FrequencyBucket] = {}
    display_names: dict[str, Counter[str]] = defaultdict(Counter)
    categories: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        seen_in_job: set[str] = set()
        for item in row.output.get(field_name) or []:
            if not isinstance(item, dict):
                continue
            name = text(item.get("name"))
            if not name:
                continue
            key = normalize_name(name)
            if key in seen_in_job:
                continue
            seen_in_job.add(key)
            category = text(item.get("category")) or "unknown"
            display_names[key][name] += 1
            categories[key][category] += 1
            if key not in buckets:
                buckets[key] = FrequencyBucket(name=name, category=category)
            buckets[key].name = display_names[key].most_common(1)[0][0]
            buckets[key].category = categories[key].most_common(1)[0][0]
            buckets[key].add(row=row, item=item, max_evidence=max_evidence_per_item)
    items = [bucket.to_dict(total_jobs=len(rows)) for bucket in buckets.values()]
    items.sort(key=lambda item: (-item["count"], item["name"].lower()))
    return items[:top_n]



def aggregate_technical_terms(rows: list[ExtractedJobRow], top_n: int, max_evidence_per_item: int) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        seen_in_job: set[str] = set()
        for skill in row.source_skills:
            add_technical_term(buckets, row=row, name=skill, source="source_skills", item=None, max_evidence=max_evidence_per_item)
            seen_in_job.add(term_key(skill))
        for section_name in ["technical_stack", "tools_platforms"]:
            for item in row.output.get(section_name) or []:
                if not isinstance(item, dict):
                    continue
                name = clean_term(item.get("name"))
                key = term_key(name)
                if not key or key in seen_in_job:
                    continue
                seen_in_job.add(key)
                add_technical_term(buckets, row=row, name=name, source=section_name, item=item, max_evidence=max_evidence_per_item)
    items = []
    total_jobs = len(rows)
    for key, bucket in buckets.items():
        job_ids = bucket["job_ids"]
        evidence = bucket["evidence"]
        count = len(job_ids)
        exact_ratio = round(bucket["exact_evidence"] / len(evidence), 4) if evidence else 0
        source_bonus = 0.15 if bucket["sources"].get("source_skills") else 0
        importance_bonus = bucket["importance_score"] / max(1, count) * 0.2
        score = count + source_bonus + importance_bonus + exact_ratio * 0.1
        items.append({
            "name": bucket["display_names"].most_common(1)[0][0],
            "key": key,
            "count": count,
            "ratio": round(count / total_jobs, 4) if total_jobs else 0,
            "score": round(score, 4),
            "job_ids": sorted(job_ids),
            "sources": dict(bucket["sources"]),
            "importance_distribution": dict(bucket["importance"]),
            "exact_evidence_ratio": exact_ratio,
            "evidence": evidence,
        })
    items.sort(key=lambda item: (-item["score"], -item["count"], item["name"].lower()))
    return items[:top_n]


def add_technical_term(
    buckets: dict[str, dict[str, Any]],
    row: ExtractedJobRow,
    name: str,
    source: str,
    item: dict[str, Any] | None,
    max_evidence: int,
) -> None:
    cleaned = clean_term(name)
    key = term_key(cleaned)
    if not key:
        return
    if key not in buckets:
        buckets[key] = {
            "display_names": Counter(),
            "job_ids": set(),
            "sources": Counter(),
            "importance": Counter(),
            "importance_score": 0.0,
            "evidence": [],
            "exact_evidence": 0,
        }
    bucket = buckets[key]
    bucket["display_names"][cleaned] += 1
    bucket["job_ids"].add(row.job_id)
    bucket["sources"][source] += 1
    importance = text((item or {}).get("importance")) or "unclear"
    bucket["importance"][importance] += 1
    bucket["importance_score"] += {"core": 1.0, "common": 0.7, "nice_to_have": 0.3}.get(importance, 0.1)
    if item is None or len(bucket["evidence"]) >= max_evidence:
        return
    for ev in item.get("evidence") or []:
        quote = text(ev.get("quote"))
        if not quote:
            continue
        exact = quote in row.raw_job_text or quote in row.job_title
        bucket["evidence"].append({
            "job_id": row.job_id,
            "company": row.company_name,
            "job_title": row.job_title,
            "source": source,
            "quote": compact_quote(quote),
            "quote_exact_match": exact,
        })
        if exact:
            bucket["exact_evidence"] += 1
        break


def layer_technical_terms(items: list[dict[str, Any]], total_jobs: int) -> dict[str, list[dict[str, Any]]]:
    layers = {"core": [], "common": [], "nice_to_have": [], "niche_signals": []}
    for item in items:
        ratio = float(item.get("ratio") or 0)
        count = int(item.get("count") or 0)
        importance = item.get("importance_distribution") or {}
        compact = {key: item[key] for key in ["name", "count", "ratio", "sources"] if key in item}
        if ratio >= 0.5 or int(importance.get("core") or 0) >= 2:
            layers["core"].append(compact)
        elif ratio >= 0.2 or count >= 2:
            layers["common"].append(compact)
        elif total_jobs <= 10:
            layers["nice_to_have"].append(compact)
        else:
            layers["niche_signals"].append(compact)
    return layers


def summarize_salary(rows: list[ExtractedJobRow]) -> dict[str, Any]:
    monthly: list[tuple[float, float]] = []
    daily: list[tuple[float, float]] = []
    unparsed: list[str] = []
    for row in rows:
        parsed = parse_salary(row.salary)
        if parsed is None:
            if row.salary:
                unparsed.append(row.salary)
            continue
        if parsed["unit"] == "monthly_cny":
            monthly.append((float(parsed["low"]), float(parsed["high"])))
        elif parsed["unit"] == "daily_cny":
            daily.append((float(parsed["low"]), float(parsed["high"])))
    return {
        "raw_salary_count": sum(1 for row in rows if row.salary),
        "parsed_count": len(monthly) + len(daily),
        "unparsed_count": len(unparsed),
        "unparsed_samples": sorted(set(unparsed))[:8],
        "monthly_cny": summarize_ranges(monthly),
        "daily_cny": summarize_ranges(daily),
    }


def parse_salary(value: str) -> dict[str, float | str] | None:
    source = text(value).replace(" ", "")
    if not source:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)[-~至](\d+(?:\.\d+)?)元/天", source)
    if match:
        return {"unit": "daily_cny", "low": float(match.group(1)), "high": float(match.group(2))}
    match = re.search(r"(\d+(?:\.\d+)?)[kK千][-~至](\d+(?:\.\d+)?)[kK千]?", source)
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)[-~至](\d+(?:\.\d+)?)[kK千]", source)
    if match:
        return {"unit": "monthly_cny", "low": float(match.group(1)) * 1000, "high": float(match.group(2)) * 1000}
    return None


def summarize_ranges(ranges: list[tuple[float, float]]) -> dict[str, Any]:
    if not ranges:
        return {"count": 0}
    lows = [low for low, _ in ranges]
    highs = [high for _, high in ranges]
    mids = [(low + high) / 2 for low, high in ranges]
    mids_sorted = sorted(mids)
    middle = len(mids_sorted) // 2
    median = mids_sorted[middle] if len(mids_sorted) % 2 else (mids_sorted[middle - 1] + mids_sorted[middle]) / 2
    return {
        "count": len(ranges),
        "min_low": round(min(lows), 2),
        "max_high": round(max(highs), 2),
        "average_low": round(sum(lows) / len(lows), 2),
        "average_high": round(sum(highs) / len(highs), 2),
        "median_mid": round(median, 2),
    }


def build_representative_jobs(rows: list[ExtractedJobRow], max_jobs: int, top_terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    top_keys = {text(item.get("key")) for item in top_terms}
    output = []
    for row in sorted(rows, key=lambda item: (-item.match_score, item.job_id))[:max_jobs]:
        terms = []
        for section_name in ["technical_stack", "tools_platforms"]:
            for item in row.output.get(section_name) or []:
                if not isinstance(item, dict):
                    continue
                name = clean_term(item.get("name"))
                if term_key(name) in top_keys and name not in terms:
                    terms.append(name)
        output.append({
            "job_id": row.job_id,
            "company": row.company_name,
            "job_title": row.job_title,
            "city": row.city,
            "salary": row.salary,
            "experience": row.experience,
            "education": row.education,
            "match_score": round(row.match_score, 1),
            "match_status": row.match_status,
            "top_terms": terms[:8],
        })
    return output

def aggregate_requirement(rows: list[ExtractedJobRow], field_name: str, max_evidence_per_item: int) -> dict[str, Any]:
    level_counts: Counter[str] = Counter()
    summaries: Counter[str] = Counter()
    evidence: list[dict[str, Any]] = []
    for row in rows:
        requirement = row.output.get(field_name) or {}
        if not isinstance(requirement, dict):
            continue
        level = text(requirement.get("level")) or "unclear"
        level_counts[level] += 1
        summary = text(requirement.get("summary"))
        if summary:
            summaries[summary] += 1
        if len(evidence) < max_evidence_per_item:
            for ev in requirement.get("evidence") or []:
                quote = text(ev.get("quote"))
                if quote:
                    evidence.append(
                        {
                            "job_id": row.job_id,
                            "company": row.company_name,
                            "job_title": row.job_title,
                            "field": text(ev.get("field")),
                            "quote": compact_quote(quote),
                            "quote_exact_match": quote in row.raw_job_text or quote in row.job_title,
                        }
                    )
                    break
    return {
        "level_distribution": counter_to_list(level_counts, len(rows)),
        "common_summaries": [name for name, _ in summaries.most_common(8)],
        "evidence": evidence,
    }


def summarize_evidence_quality(rows: list[ExtractedJobRow]) -> dict[str, Any]:
    total = 0
    exact = 0
    misses: list[dict[str, Any]] = []
    for row in rows:
        for evidence in collect_evidence(row.output):
            quote = text(evidence.get("quote"))
            if not quote:
                continue
            total += 1
            hit = quote in row.raw_job_text or quote in row.job_title
            if hit:
                exact += 1
            elif len(misses) < 10:
                misses.append(
                    {
                        "job_id": row.job_id,
                        "company": row.company_name,
                        "job_title": row.job_title,
                        "quote": quote[:120],
                    }
                )
    return {
        "evidence_count": total,
        "exact_quote_hits": exact,
        "exact_quote_hit_ratio": round(exact / total, 4) if total else 0,
        "miss_count": total - exact,
        "miss_samples": misses,
    }


def collect_evidence(value: Any) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "quote" in value:
            evidence.append(value)
        for child in value.values():
            evidence.extend(collect_evidence(child))
    elif isinstance(value, list):
        for item in value:
            evidence.extend(collect_evidence(item))
    return evidence


def build_evidence_pack(sections: list[list[dict[str, Any]]], max_items: int) -> list[dict[str, Any]]:
    pack: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for section in sections:
        for item in section[:8]:
            for ev in item.get("evidence") or []:
                key = (int(ev.get("job_id") or 0), text(ev.get("quote")))
                if key in seen:
                    continue
                seen.add(key)
                pack.append({"topic": item.get("name"), "job_id": ev.get("job_id"), "company": ev.get("company"), "job_title": ev.get("job_title"), "quote": compact_quote(ev.get("quote")), "quote_exact_match": ev.get("quote_exact_match")})
                if len(pack) >= max_items:
                    return pack
    return pack


def store_report_input(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    output_path: Path,
    token_budget: int,
) -> int:
    query = payload.get("query") or {}
    cursor = conn.execute(
        """
        INSERT INTO job_report_inputs (
            search_run_id,
            source_type,
            report_type,
            input_hash,
            input_json,
            token_budget
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(report_type, input_hash) DO UPDATE SET
            input_json = excluded.input_json,
            token_budget = excluded.token_budget
        """,
        (
            query.get("search_run_id"),
            query.get("source_type") or "unknown",
            payload.get("report_type") or DEFAULT_REPORT_TYPE,
            payload["input_hash"],
            json.dumps(payload, ensure_ascii=True),
            token_budget,
        ),
    )
    conn.commit()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if cursor.lastrowid:
        return int(cursor.lastrowid)
    row = conn.execute(
        "SELECT id FROM job_report_inputs WHERE report_type = ? AND input_hash = ?",
        (payload.get("report_type") or DEFAULT_REPORT_TYPE, payload["input_hash"]),
    ).fetchone()
    return int(row["id"])


def compact_quote(value: object) -> str:
    cleaned = text(value).replace("\n", " ")
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= MAX_QUOTE_CHARS:
        return cleaned
    return cleaned[:MAX_QUOTE_CHARS].rstrip()


def counter_to_list(counter: Counter[str], total: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count, "ratio": round(count / total, 4) if total else 0}
        for name, count in counter.most_common()
    ]


def report_hash(payload: dict[str, Any]) -> str:
    comparable = {key: value for key, value in payload.items() if key not in {"input_hash", "estimated_prompt_tokens"}}
    return hashlib.sha256(json.dumps(comparable, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def estimate_tokens(payload: dict[str, Any]) -> int:
    text_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return max(1, len(text_payload) // 2)


def first_non_empty(values: list[str]) -> str:
    for value in values:
        if text(value):
            return text(value)
    return ""


def normalize_name(value: str) -> str:
    cleaned = text(value).lower().replace(" ", "")
    aliases = {
        "python3": "python",
        "py": "python",
        "c++11": "c++",
        "c++14": "c++",
        "c++17": "c++",
        "ros2": "ros/ros2",
        "ros": "ros/ros2",
        "aiagent": "智能体",
        "agent": "智能体",
        "大模型agent": "智能体",
        "rag": "rag",
        "dify": "dify",
        "coze": "coze",
        "slam": "slam",
    }
    return aliases.get(cleaned, cleaned)



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
    parser = argparse.ArgumentParser(description="Build compact local report input from job extractions.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--search-run-id", type=int, default=0)
    parser.add_argument("--source-type", default="boss")
    parser.add_argument("--match-status", nargs="*", default=["strong_match"])
    parser.add_argument("--top-n", type=int, default=15)
    parser.add_argument("--max-evidence-per-item", type=int, default=1)
    parser.add_argument("--token-budget", type=int, default=0)
    parser.add_argument("--job-ids", nargs="*", type=int, default=[])
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    payload = build_report_input(
        conn=conn,
        search_run_id=args.search_run_id,
        source_type=args.source_type,
        match_statuses=args.match_status,
        top_n=args.top_n,
        max_evidence_per_item=args.max_evidence_per_item,
        job_ids=args.job_ids,
    )
    output_path = args.output or DEFAULT_OUTPUT_DIR / f"job_report_input_{args.search_run_id or args.source_type}.json"
    resolved_token_budget = args.token_budget or int((payload.get("budget") or {}).get("report_token_budget") or 0)
    report_input_id = store_report_input(
        conn=conn,
        payload=payload,
        output_path=output_path,
        token_budget=resolved_token_budget,
    )
    summary = {
        "report_input_id": report_input_id,
        "output": str(output_path),
        "query": payload["query"],
        "total_jobs": payload["sample"]["total_jobs"],
        "estimated_prompt_tokens": payload["estimated_prompt_tokens"],
        "budget": payload["budget"],
        "top_technical_terms": payload["technical_terms_top"][:8],
        "salary_summary": payload["salary_summary"],
        "top_technical_stack": payload["technical_stack_frequency"][:8],
        "top_tools_platforms": payload["tools_platforms_frequency"][:8],
        "top_ability_requirements": payload["ability_requirements_frequency"][:8],
        "graduate_friendliness_distribution": payload["sample"]["graduate_friendliness_distribution"],
        "evidence_quality": payload["evidence_quality"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
