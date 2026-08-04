from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from jobuwant.db import DB_PATH, connect, initialize_database


DEFAULT_CITY_NAMES = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "武汉",
    "西安",
    "重庆",
    "天津",
    "长沙",
    "合肥",
    "宁波",
    "无锡",
]

DETAIL_MARKERS = [
    "岗位职责",
    "职位描述",
    "工作职责",
    "工作内容",
    "任职要求",
    "任职资格",
    "岗位要求",
    "职位要求",
    "加分项",
]

SENIOR_TERMS = [
    "3-5年",
    "5-10年",
    "5年以上",
    "8年以上",
    "10年以上",
    "高级",
    "资深",
    "专家",
    "负责人",
    "技术总监",
    "架构师",
    "leader",
    "lead",
]

BASE_LOCATION_MARKERS = ["base", "工作地", "工作地点", "办公地", "办公地点", "常驻", "地点"]


@dataclass(frozen=True)
class QualityResult:
    status: str
    flags: list[str]
    score: int
    notes: str


def label_jobs(
    conn: sqlite3.Connection,
    target_city: str,
    target_keywords: list[str],
    source_type: str = "boss",
) -> dict[str, object]:
    initialize_database(conn)
    rows = _load_rows(conn, source_type)
    preferred_by_url = _preferred_ids_by_url(rows)
    status_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()

    for row in rows:
        result = evaluate_row(
            row=dict(row),
            target_city=target_city,
            target_keywords=target_keywords,
            preferred_by_url=preferred_by_url,
        )
        status_counts[result.status] += 1
        flag_counts.update(result.flags)
        conn.execute(
            """
            UPDATE job_details
            SET
                quality_status = ?,
                quality_flags_json = ?,
                quality_score = ?,
                quality_notes = ?,
                quality_updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                result.status,
                json.dumps(result.flags, ensure_ascii=True),
                result.score,
                result.notes,
                int(row["id"]),
            ),
        )
    conn.commit()
    return {
        "evaluated_count": len(rows),
        "status_counts": dict(status_counts),
        "flag_counts": dict(flag_counts),
    }


def evaluate_row(
    row: dict[str, object],
    target_city: str,
    target_keywords: list[str],
    preferred_by_url: dict[str, int],
) -> QualityResult:
    flags: list[str] = []
    notes: list[str] = []
    title = _text(row.get("job_title"))
    city = _text(row.get("city"))
    url = _text(row.get("original_url"))
    raw_text = _text(row.get("raw_job_text"))
    metadata = _metadata(row.get("source_metadata_json"))
    combined = f"{title}\n{raw_text}"

    if target_city and city and city != target_city:
        flags.append("city_mismatch")
        notes.append(f"city={city}, target_city={target_city}")

    base_city = find_base_city_mismatch(combined, target_city)
    if base_city:
        flags.append("base_city_mismatch")
        notes.append(f"base_city={base_city}")

    if url and preferred_by_url.get(url) not in {None, int(row["id"])}:
        flags.append("duplicate_url_variant")
        notes.append("same original_url has a fuller sibling record")

    keyword_hits = count_keyword_hits(combined, target_keywords)
    title_hits = count_keyword_hits(title, target_keywords)
    if target_keywords and title_hits == 0 and keyword_hits <= 1:
        flags.append("weak_relevance")
        notes.append(f"keyword_hits={keyword_hits}")

    marker_count = count_markers(raw_text)
    if is_thin_description(raw_text, marker_count, keyword_hits):
        flags.append("thin_description")
        notes.append(f"text_chars={len(raw_text)}, detail_markers={marker_count}")

    salary = _text(metadata.get("salary"))
    experience = _text(metadata.get("experience"))
    education = _text(metadata.get("education"))
    job_context = f"{title}\n{raw_text}\n{salary}\n{experience}".lower()

    if is_intern_position(job_context):
        flags.append("intern_position")
    if is_senior_required(job_context):
        flags.append("senior_required")
    if not salary:
        flags.append("missing_salary")
    if not experience:
        flags.append("missing_experience")
    if not education:
        flags.append("missing_education")

    status = quality_status(flags)
    score = quality_score(flags)
    return QualityResult(
        status=status,
        flags=sorted(set(flags)),
        score=score,
        notes="; ".join(notes) if notes else "passed rule checks",
    )


def quality_status(flags: list[str]) -> str:
    exclude_flags = {"city_mismatch", "base_city_mismatch", "duplicate_url_variant"}
    review_flags = {"weak_relevance", "thin_description", "senior_required", "intern_position"}
    flag_set = set(flags)
    if flag_set & exclude_flags:
        return "exclude_from_analysis"
    if flag_set & review_flags:
        return "needs_review"
    return "analysis_ready"


def quality_score(flags: list[str]) -> int:
    penalties = {
        "city_mismatch": 40,
        "base_city_mismatch": 40,
        "duplicate_url_variant": 35,
        "weak_relevance": 30,
        "thin_description": 25,
        "senior_required": 15,
        "intern_position": 15,
        "missing_salary": 5,
        "missing_experience": 5,
        "missing_education": 5,
    }
    return max(0, 100 - sum(penalties.get(flag, 0) for flag in set(flags)))


def count_keyword_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword and keyword.lower() in lowered)


def count_markers(text: str) -> int:
    return sum(1 for marker in DETAIL_MARKERS if marker in text)


def is_thin_description(text: str, marker_count: int, keyword_hits: int) -> bool:
    if len(text) < 120:
        return True
    return len(text) < 300 and marker_count == 0 and keyword_hits <= 1


def is_intern_position(text: str) -> bool:
    return any(term in text for term in ["实习", "intern", "元/天", "天/周", "个月"])


def is_senior_required(text: str) -> bool:
    return any(term in text for term in SENIOR_TERMS)


def find_base_city_mismatch(text: str, target_city: str) -> str:
    compact = text.replace(" ", "").lower()
    for city in DEFAULT_CITY_NAMES:
        if city == target_city:
            continue
        for marker in BASE_LOCATION_MARKERS:
            if f"{marker}{city}".lower() in compact or f"{city}{marker}".lower() in compact:
                return city
    return ""


def _load_rows(conn: sqlite3.Connection, source_type: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            id,
            company_name,
            job_title,
            city,
            original_url,
            raw_job_text,
            source_metadata_json
        FROM job_details
        WHERE source_type = ?
        ORDER BY id
        """,
        (source_type,),
    ).fetchall()


def _preferred_ids_by_url(rows: list[sqlite3.Row]) -> dict[str, int]:
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        url = _text(row["original_url"])
        if url:
            grouped[url].append(row)
    preferred: dict[str, int] = {}
    for url, url_rows in grouped.items():
        best = max(url_rows, key=lambda row: (len(_text(row["raw_job_text"])), int(row["id"])))
        preferred[url] = int(best["id"])
    return preferred


def _metadata(value: object) -> dict[str, object]:
    try:
        parsed = json.loads(_text(value) or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply JobUWant job quality labels.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--source-type", default="boss")
    parser.add_argument("--city", required=True)
    parser.add_argument("--keywords", nargs="*", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    conn = connect(args.db)
    summary = label_jobs(
        conn=conn,
        target_city=args.city,
        target_keywords=args.keywords,
        source_type=args.source_type,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
