from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobuwant.db import DB_PATH, connect, initialize_database


ENGLISH_TERM_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9+#./-]{1,30}(?![A-Za-z0-9])")
SPLIT_RE = re.compile(r"[\s,，/|、;；:：()（）\[\]{}<>《》]+")

STOP_ENGLISH_TERMS = {
    "and",
    "or",
    "to",
    "for",
    "with",
    "the",
    "a",
    "an",
    "of",
    "in",
    "on",
    "by",
    "base",
    "job",
    "boss",
    "hr",
}

COMMON_ROLE_TERMS = [
    "AI",
    "Agent",
    "智能体",
    "大模型",
    "应用",
    "开发",
    "后端",
    "前端",
    "算法",
    "工程师",
    "产品",
    "运营",
    "实习",
    "机器人",
    "SLAM",
    "定位",
    "建图",
    "导航",
]

SENIOR_TERMS = ["5年以上", "8年以上", "10年以上", "资深", "高级", "专家", "负责人", "leader", "lead"]
INTERN_TERMS = ["实习", "intern", "元/天", "天/周"]
ENGINEERING_TERMS = ["工程师", "开发", "研发", "算法", "后端", "前端", "测试", "架构", "平台", "数据", "AI", "SLAM"]
PRODUCT_TERMS = ["产品经理", "产品专员", "产品运营"]
OPERATIONS_TERMS = ["运营", "内容", "用户增长", "社群"]
SALES_TERMS = ["销售", "客户经理", "商务", "渠道", "解决方案销售"]
PARTNER_TERMS = ["合伙人", "生态伙伴", "招商", "加盟"]


@dataclass(frozen=True)
class MatchResult:
    score: float
    status: str
    role_intent: str
    reasons: list[str]
    review_reasons: list[str]
    dimensions: dict[str, float]


def score_jobs(
    conn: sqlite3.Connection,
    source_type: str,
    target_city: str,
    target_keyword: str,
    target_keywords: list[str],
    expected_intent: str,
    allow_intern: bool,
    limit: int = 0,
    existing_run_id: int | None = None,
) -> dict[str, Any]:
    initialize_database(conn)
    query_terms = build_query_terms(target_keyword, target_keywords)
    rows = load_rows(conn, source_type=source_type, limit=limit)
    run_id = prepare_search_run(
        conn=conn,
        source_type=source_type,
        target_city=target_city,
        target_keyword=target_keyword,
        query_terms=query_terms,
        requested_limit=limit,
        collected_count=len(rows),
        expected_intent=expected_intent,
        allow_intern=allow_intern,
        existing_run_id=existing_run_id,
    )

    status_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    scores: list[float] = []
    top_matches: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        result = evaluate_row(
            row=dict(row),
            target_city=target_city,
            target_keyword=target_keyword,
            query_terms=query_terms,
            expected_intent=expected_intent,
            allow_intern=allow_intern,
        )
        persist_match_result(conn, run_id=run_id, row=row, source_rank=index, result=result)
        persist_local_terms(conn, run_id=run_id, row=dict(row), query_terms=query_terms)
        status_counts[result.status] += 1
        role_counts[result.role_intent] += 1
        scores.append(result.score)
        top_matches.append(
            {
                "job_id": int(row["id"]),
                "company": text(row["company_name"]),
                "job_title": text(row["job_title"]),
                "city": text(row["city"]),
                "score": round(result.score, 1),
                "status": result.status,
                "role_intent": result.role_intent,
                "review_reasons": result.review_reasons,
            }
        )

    analysis_ready_count = status_counts["strong_match"] + status_counts["review"]
    conn.execute(
        """
        UPDATE job_search_runs
        SET analysis_ready_count = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (analysis_ready_count, run_id),
    )
    conn.commit()

    top_matches.sort(key=lambda item: item["score"], reverse=True)
    return {
        "search_run_id": run_id,
        "source_type": source_type,
        "target_city": target_city,
        "target_keyword": target_keyword,
        "query_terms": query_terms,
        "evaluated_count": len(rows),
        "match_status_counts": dict(status_counts),
        "role_intent_counts": dict(role_counts),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "top_matches": top_matches[:10],
    }


def evaluate_row(
    row: dict[str, Any],
    target_city: str,
    target_keyword: str,
    query_terms: list[str],
    expected_intent: str,
    allow_intern: bool,
) -> MatchResult:
    title = text(row.get("job_title"))
    city = text(row.get("city"))
    raw_text = text(row.get("raw_job_text"))
    skills = parse_list(row.get("technical_keywords_json"))
    metadata = parse_dict(row.get("source_metadata_json"))
    combined = "\n".join([title, city, raw_text, " ".join(skills), json.dumps(metadata, ensure_ascii=False)])
    lowered = combined.lower()

    reasons: list[str] = []
    review_reasons: list[str] = []
    dimensions: dict[str, float] = {}

    if not target_city:
        city_score = 25.0
        reasons.append("未设置目标城市")
    elif city == target_city:
        city_score = 25.0
        reasons.append("城市匹配")
    elif target_city and target_city in combined:
        city_score = 15.0
        review_reasons.append("字段城市不匹配但正文出现目标城市")
    else:
        city_score = 0.0
        review_reasons.append(f"城市不匹配: {city or 'unknown'}")
    dimensions["city"] = city_score

    title_hits = matched_terms(title, query_terms)
    full_keyword_hit = bool(target_keyword and target_keyword.lower() in title.lower())
    if full_keyword_hit:
        title_score = 30.0
        reasons.append("岗位标题包含完整搜索词")
    else:
        title_score = min(30.0, 8.0 * len(title_hits))
        if title_hits:
            reasons.append("岗位标题命中: " + ", ".join(title_hits[:5]))
        else:
            review_reasons.append("岗位标题未命中搜索词")
    dimensions["title"] = title_score

    text_hits = matched_terms(combined, query_terms)
    skill_hits = matched_terms(" ".join(skills), query_terms)
    text_score = min(20.0, 5.0 * len(text_hits) + 3.0 * len(skill_hits))
    if text_hits:
        reasons.append("正文/技能命中: " + ", ".join(text_hits[:6]))
    else:
        review_reasons.append("正文和技能未命中搜索词")
    dimensions["text_relevance"] = text_score

    role_intent = infer_role_intent(title, raw_text, skills)
    if expected_intent == "any" or role_intent == expected_intent:
        role_score = 15.0
        reasons.append(f"岗位类型匹配: {role_intent}")
    elif role_intent == "intern" and allow_intern:
        role_score = 12.0
        reasons.append("实习岗位已允许进入分析")
    elif role_intent == "intern":
        role_score = 6.0
        review_reasons.append("实习岗位需要单独分析模式")
    elif role_intent == "other":
        role_score = 8.0
        review_reasons.append("岗位类型不明确")
    else:
        role_score = 3.0
        review_reasons.append(f"岗位类型偏离: {role_intent}")
    dimensions["role_intent"] = role_score

    if len(raw_text) >= 300:
        content_score = 10.0
    elif len(raw_text) >= 120:
        content_score = 6.0
        review_reasons.append("岗位正文偏短")
    else:
        content_score = 0.0
        review_reasons.append("岗位正文过短")
    dimensions["content"] = content_score

    score = city_score + title_score + text_score + role_score + content_score
    if any(term in lowered for term in SENIOR_TERMS):
        score -= 5.0
        review_reasons.append("资深要求需要确认用户阶段")
    score = max(0.0, min(100.0, score))

    if score >= 75.0:
        status = "strong_match"
    elif score >= 55.0:
        status = "review"
    else:
        status = "weak_match"

    if not reasons:
        reasons.append("未发现强匹配信号")
    return MatchResult(
        score=score,
        status=status,
        role_intent=role_intent,
        reasons=dedupe(reasons),
        review_reasons=dedupe(review_reasons),
        dimensions=dimensions,
    )


def infer_role_intent(title: str, raw_text: str, skills: list[str]) -> str:
    source = "\n".join([title, raw_text[:800], " ".join(skills)])
    lowered = source.lower()
    if any(term in lowered for term in INTERN_TERMS):
        return "intern"
    if any(term in source for term in PARTNER_TERMS):
        return "partner_business"
    if any(term in source for term in SALES_TERMS):
        return "sales_solution"
    if any(term in source for term in PRODUCT_TERMS):
        return "product"
    if any(term in source for term in OPERATIONS_TERMS):
        return "operations"
    if any(term.lower() in lowered for term in ENGINEERING_TERMS):
        return "engineering"
    return "other"


def build_query_terms(target_keyword: str, extra_keywords: list[str]) -> list[str]:
    terms: list[str] = []
    for value in [target_keyword, *extra_keywords]:
        cleaned = text(value)
        if not cleaned:
            continue
        terms.append(cleaned)
        terms.extend(part for part in SPLIT_RE.split(cleaned) if part)
        terms.extend(ENGLISH_TERM_RE.findall(cleaned))
        for role_term in COMMON_ROLE_TERMS:
            if role_term.lower() in cleaned.lower():
                terms.append(role_term)
        for suffix in ["岗位", "职位", "工程师", "开发岗", "方向", "岗"]:
            if cleaned.endswith(suffix) and len(cleaned) > len(suffix) + 1:
                terms.append(cleaned[: -len(suffix)])
    return dedupe([term for term in terms if len(term.strip()) >= 2])


def matched_terms(source: str, terms: list[str]) -> list[str]:
    lowered = source.lower()
    return [term for term in terms if term.lower() in lowered]


def load_rows(conn: sqlite3.Connection, source_type: str, limit: int) -> list[sqlite3.Row]:
    sql = """
        SELECT
            id,
            company_name,
            job_title,
            city,
            original_url,
            raw_job_text,
            technical_keywords_json,
            source_metadata_json,
            quality_status,
            quality_score
        FROM job_details
        WHERE source_type = ?
        ORDER BY id
    """
    if limit > 0:
        sql += " LIMIT ?"
        return conn.execute(sql, (source_type, limit)).fetchall()
    return conn.execute(sql, (source_type,)).fetchall()


def prepare_search_run(
    conn: sqlite3.Connection,
    source_type: str,
    target_city: str,
    target_keyword: str,
    query_terms: list[str],
    requested_limit: int,
    collected_count: int,
    expected_intent: str,
    allow_intern: bool,
    existing_run_id: int | None = None,
) -> int:
    if existing_run_id is None:
        return create_search_run(
            conn=conn,
            source_type=source_type,
            target_city=target_city,
            target_keyword=target_keyword,
            query_terms=query_terms,
            requested_limit=requested_limit,
            collected_count=collected_count,
            expected_intent=expected_intent,
            allow_intern=allow_intern,
        )
    row = conn.execute('SELECT id FROM job_search_runs WHERE id = ?', (existing_run_id,)).fetchone()
    if row is None:
        raise KeyError(f'job_search_run not found: {existing_run_id}')
    conn.execute(
        """
        UPDATE job_search_runs
        SET source_type = ?,
            source_name = ?,
            query_city = ?,
            query_keyword = ?,
            query_keywords_json = ?,
            requested_limit = ?,
            collected_count = ?,
            config_json = ?,
            notes = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            source_type,
            'local_sqlite',
            target_city,
            target_keyword,
            json.dumps(query_terms, ensure_ascii=True),
            requested_limit,
            collected_count,
            json.dumps({'expected_intent': expected_intent, 'allow_intern': allow_intern}, ensure_ascii=True),
            'scored by job_match_score',
            'running',
            existing_run_id,
        ),
    )
    conn.execute('DELETE FROM job_search_run_items WHERE search_run_id = ?', (existing_run_id,))
    conn.execute('DELETE FROM job_terms WHERE search_run_id = ?', (existing_run_id,))
    conn.commit()
    return existing_run_id


def create_search_run(
    conn: sqlite3.Connection,
    source_type: str,
    target_city: str,
    target_keyword: str,
    query_terms: list[str],
    requested_limit: int,
    collected_count: int,
    expected_intent: str,
    allow_intern: bool,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO job_search_runs (
            source_type,
            source_name,
            query_city,
            query_keyword,
            query_keywords_json,
            requested_limit,
            collected_count,
            config_json,
            notes,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_type,
            "local_sqlite",
            target_city,
            target_keyword,
            json.dumps(query_terms, ensure_ascii=True),
            requested_limit,
            collected_count,
            json.dumps({"expected_intent": expected_intent, "allow_intern": allow_intern}, ensure_ascii=True),
            "created by job_match_score",
            "completed",
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def persist_match_result(conn: sqlite3.Connection, run_id: int, row: sqlite3.Row, source_rank: int, result: MatchResult) -> None:
    reasons_json = json.dumps(
        {"reasons": result.reasons, "dimensions": result.dimensions},
        ensure_ascii=True,
    )
    review_json = json.dumps(result.review_reasons, ensure_ascii=True)
    conn.execute(
        """
        INSERT INTO job_search_run_items (
            search_run_id,
            job_detail_id,
            source_rank,
            match_score,
            match_status,
            role_intent,
            match_reasons_json,
            review_reasons_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(search_run_id, job_detail_id) DO UPDATE SET
            source_rank = excluded.source_rank,
            match_score = excluded.match_score,
            match_status = excluded.match_status,
            role_intent = excluded.role_intent,
            match_reasons_json = excluded.match_reasons_json,
            review_reasons_json = excluded.review_reasons_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            run_id,
            int(row["id"]),
            source_rank,
            result.score,
            result.status,
            result.role_intent,
            reasons_json,
            review_json,
        ),
    )
    conn.execute(
        """
        UPDATE job_details
        SET
            last_match_score = ?,
            last_match_status = ?,
            last_match_reasons_json = ?,
            last_match_updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (result.score, result.status, reasons_json, int(row["id"])),
    )


def persist_local_terms(conn: sqlite3.Connection, run_id: int, row: dict[str, Any], query_terms: list[str]) -> None:
    job_id = int(row["id"])
    terms = extract_local_terms(row=row, query_terms=query_terms)
    for item in terms[:120]:
        conn.execute(
            """
            INSERT INTO job_terms (
                job_detail_id,
                search_run_id,
                term,
                normalized_term,
                category,
                source_field,
                evidence,
                confidence_label,
                extractor_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_detail_id, search_run_id, normalized_term, category, source_field) DO UPDATE SET
                term = excluded.term,
                evidence = excluded.evidence,
                confidence_label = excluded.confidence_label,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                job_id,
                run_id,
                item["term"],
                item["normalized_term"],
                item["category"],
                item["source_field"],
                item["evidence"],
                item["confidence_label"],
                item["extractor_name"],
            ),
        )


def extract_local_terms(row: dict[str, Any], query_terms: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    title = text(row.get("job_title"))
    raw_text = text(row.get("raw_job_text"))
    skills = parse_list(row.get("technical_keywords_json"))

    for skill in skills:
        add_term(items, skill, "source_skill", "technical_keywords_json", skill, "high")

    for term in matched_terms(title, query_terms):
        add_term(items, term, "query_term", "job_title", title, "high")
    for term in matched_terms(raw_text, query_terms):
        add_term(items, term, "query_term", "raw_job_text", snippet_around(raw_text, term), "medium")

    for match in ENGLISH_TERM_RE.findall("\n".join([title, raw_text])):
        normalized = normalize_term(match)
        if normalized in STOP_ENGLISH_TERMS or len(normalized) < 2:
            continue
        add_term(items, match, "candidate_tech_term", "raw_job_text", snippet_around(raw_text, match), "low")
    return items


def add_term(
    items: list[dict[str, str]],
    term: str,
    category: str,
    source_field: str,
    evidence: str,
    confidence_label: str,
) -> None:
    cleaned = text(term)
    if not cleaned:
        return
    item = {
        "term": cleaned,
        "normalized_term": normalize_term(cleaned),
        "category": category,
        "source_field": source_field,
        "evidence": text(evidence)[:240],
        "confidence_label": confidence_label,
        "extractor_name": "local_match_score_v1",
    }
    identity = (item["normalized_term"], item["category"], item["source_field"])
    if identity not in {(existing["normalized_term"], existing["category"], existing["source_field"]) for existing in items}:
        items.append(item)


def snippet_around(source: str, term: str, window: int = 80) -> str:
    if not source or not term:
        return ""
    index = source.lower().find(term.lower())
    if index < 0:
        return source[:window]
    start = max(0, index - window // 2)
    end = min(len(source), index + len(term) + window // 2)
    return source[start:end]


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


def normalize_term(value: str) -> str:
    cleaned = text(value)
    if re.fullmatch(r"[A-Za-z0-9+#./-]+", cleaned):
        return cleaned.lower()
    return cleaned.lower().replace(" ", "")


def dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = text(value)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output


def text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score local jobs against a user search intent.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--source-type", default="boss")
    parser.add_argument("--city", default="")
    parser.add_argument("--keyword", default="")
    parser.add_argument("--keywords", nargs="*", default=[])
    parser.add_argument("--expected-intent", default="engineering", choices=["engineering", "product", "operations", "sales_solution", "partner_business", "intern", "any"])
    parser.add_argument("--allow-intern", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    summary = score_jobs(
        conn=conn,
        source_type=args.source_type,
        target_city=args.city,
        target_keyword=args.keyword,
        target_keywords=args.keywords,
        expected_intent=args.expected_intent,
        allow_intern=args.allow_intern,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

