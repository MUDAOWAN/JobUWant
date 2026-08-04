from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobuwant.analysis_budget import budget_for_job_count
from jobuwant.ai_job_extract import (
    DEFAULT_EXTRACTOR_NAME,
    DEFAULT_MAX_TEXT_CHARS_PER_JOB,
    DEFAULT_SCHEMA_VERSION,
    ExtractedJob,
)
from jobuwant.ai_report_writer import AIJobReport
from jobuwant.db import DB_PATH, connect, initialize_database


MIN_EVIDENCE_EXACT_RATIO = 0.95


@dataclass(frozen=True)
class Fixture:
    name: str
    search_run_id: int
    source_type: str
    city: str
    keyword: str
    report_input_path: Path
    final_report_path: Path
    expected_report_jobs: int
    expected_strong_matches: int | None = None


@dataclass
class CheckResult:
    status: str
    name: str
    details: str


FIXTURES = [
    Fixture(
        name="shenzhen_ai_app",
        search_run_id=4,
        source_type="boss_sz_ai_app",
        city="Shenzhen",
        keyword="AI application development",
        report_input_path=Path("data/job_report_input_sz_ai_app.json"),
        final_report_path=Path("data/job_report_sz_ai_app.json"),
        expected_report_jobs=3,
        expected_strong_matches=3,
    ),
    Fixture(
        name="hangzhou_slam",
        search_run_id=3,
        source_type="boss",
        city="Hangzhou",
        keyword="SLAM",
        report_input_path=Path("data/job_report_input_hz_slam.json"),
        final_report_path=Path("data/job_report_hz_slam.json"),
        expected_report_jobs=5,
        expected_strong_matches=None,
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    initialize_database(conn)

    results: list[CheckResult] = []
    for fixture in FIXTURES:
        results.extend(run_fixture_checks(conn, fixture, args.token_budget))

    print_results(results)
    failed = any(result.status == "FAIL" for result in results)
    warned = any(result.status == "WARN" for result in results)
    if failed:
        print("\nResult: FAIL")
        return 1
    if warned:
        print("\nResult: PASS with warnings")
        return 0
    print("\nResult: PASS")
    return 0


def run_fixture_checks(conn: sqlite3.Connection, fixture: Fixture, token_budget_override: int) -> list[CheckResult]:
    results: list[CheckResult] = []
    report_input = load_json_file(fixture.report_input_path)
    final_report = load_json_file(fixture.final_report_path)
    report_job_ids = [int(value) for value in ((report_input.get("sample") or {}).get("job_ids") or [])]

    results.append(check_search_run(conn, fixture))
    results.append(check_report_sample(fixture, report_input, report_job_ids))
    results.append(check_extractions_schema(conn, fixture, report_job_ids))
    results.append(check_report_input_budget(fixture, report_input, token_budget_override))
    results.append(check_report_input_enhanced(fixture, report_input))
    results.append(check_report_input_compact(fixture, report_input, conn, report_job_ids))
    results.append(check_evidence_quotes(conn, fixture, report_job_ids))
    results.append(check_final_report(fixture, final_report))
    results.append(check_cached_extractions(conn, fixture, report_job_ids))
    results.append(check_role_direction(fixture, report_input, final_report))
    return results


def check_search_run(conn: sqlite3.Connection, fixture: Fixture) -> CheckResult:
    run = conn.execute(
        """
        SELECT id, source_type, query_city, query_keyword, status
        FROM job_search_runs
        WHERE id = ?
        """,
        (fixture.search_run_id,),
    ).fetchone()
    if run is None:
        return fail(f"{fixture.name}: search run", f"search_run_id={fixture.search_run_id} not found")
    rows = conn.execute(
        """
        SELECT match_status, COUNT(*) AS count
        FROM job_search_run_items
        WHERE search_run_id = ?
        GROUP BY match_status
        ORDER BY match_status
        """,
        (fixture.search_run_id,),
    ).fetchall()
    counts = {str(row["match_status"]): int(row["count"]) for row in rows}
    strong_count = counts.get("strong_match", 0)
    if fixture.expected_strong_matches is not None and strong_count != fixture.expected_strong_matches:
        return fail(
            f"{fixture.name}: search run",
            f"strong_match={strong_count}, expected={fixture.expected_strong_matches}",
        )
    detail = (
        f"id={run['id']}, source_type={run['source_type']}, "
        f"status={run['status']}, status_counts={counts}"
    )
    if fixture.expected_strong_matches is None and strong_count != fixture.expected_report_jobs:
        return warn(
            f"{fixture.name}: search run",
            f"{detail}; report fixture uses {fixture.expected_report_jobs} selected jobs",
        )
    return ok(f"{fixture.name}: search run", detail)


def check_report_sample(fixture: Fixture, report_input: dict[str, Any], report_job_ids: list[int]) -> CheckResult:
    sample = report_input.get("sample") or {}
    query = report_input.get("query") or {}
    total_jobs = int(sample.get("total_jobs") or 0)
    if total_jobs != fixture.expected_report_jobs:
        return fail(
            f"{fixture.name}: report sample",
            f"total_jobs={total_jobs}, expected={fixture.expected_report_jobs}",
        )
    if len(report_job_ids) != total_jobs:
        return fail(
            f"{fixture.name}: report sample",
            f"job_ids={len(report_job_ids)}, total_jobs={total_jobs}",
        )
    if int(query.get("search_run_id") or 0) != fixture.search_run_id:
        return fail(
            f"{fixture.name}: report sample",
            f"report input points to search_run_id={query.get('search_run_id')}",
        )
    budget = budget_for_job_count(total_jobs)
    return ok(
        f"{fixture.name}: report sample",
        f"total_jobs={total_jobs}, job_ids={report_job_ids}, budget_tier={budget.tier}",
    )


def check_extractions_schema(conn: sqlite3.Connection, fixture: Fixture, job_ids: list[int]) -> CheckResult:
    rows = load_latest_extractions(conn, job_ids)
    missing = sorted(set(job_ids) - set(rows))
    errors: list[str] = []
    legacy_compatible: list[int] = []
    for job_id, payload in rows.items():
        try:
            ExtractedJob.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            if has_required_extraction_shape(payload) and collect_evidence(payload):
                legacy_compatible.append(job_id)
            else:
                errors.append(f"job_id={job_id}: {exc}")
    if missing or errors:
        details = []
        if missing:
            details.append(f"missing_extractions={missing}")
        if errors:
            details.append("schema_errors=" + "; ".join(errors[:3]))
        return fail(f"{fixture.name}: extraction schema", " | ".join(details))
    if legacy_compatible:
        return warn(
            f"{fixture.name}: extraction schema",
            f"{len(rows) - len(legacy_compatible)}/{len(job_ids)} strict valid; legacy-compatible job_ids={legacy_compatible}",
        )
    return ok(f"{fixture.name}: extraction schema", f"{len(rows)}/{len(job_ids)} valid")


def check_report_input_budget(
    fixture: Fixture,
    report_input: dict[str, Any],
    token_budget_override: int,
) -> CheckResult:
    estimated_tokens = int(report_input.get("estimated_prompt_tokens") or 0)
    if estimated_tokens <= 0:
        return fail(f"{fixture.name}: token budget", "estimated_prompt_tokens is missing")
    total_jobs = int(((report_input.get("sample") or {}).get("total_jobs")) or 0)
    budget = budget_for_job_count(total_jobs)
    embedded_budget = report_input.get("budget") or {}
    embedded_token_budget = int(embedded_budget.get("report_token_budget") or 0)
    if embedded_token_budget != budget.report_token_budget:
        return fail(
            f"{fixture.name}: token budget",
            f"embedded_budget={embedded_token_budget}, expected={budget.report_token_budget}",
        )
    limits = [("analysis_budget", budget.report_token_budget)]
    if token_budget_override > 0:
        limits.append(("cli_override", token_budget_override))
    over_limits = [f"{name}={limit}" for name, limit in limits if estimated_tokens > limit]
    if over_limits:
        return fail(
            f"{fixture.name}: token budget",
            f"estimated_prompt_tokens={estimated_tokens}, over {', '.join(over_limits)}",
        )
    return ok(
        f"{fixture.name}: token budget",
        f"estimated_prompt_tokens={estimated_tokens}, tier={budget.tier}, budget={budget.report_token_budget}",
    )


def check_report_input_enhanced(fixture: Fixture, report_input: dict[str, Any]) -> CheckResult:
    required_shapes = {
        "budget": dict,
        "technical_terms_top": list,
        "technical_terms_layers": dict,
        "salary_summary": dict,
        "representative_jobs": list,
    }
    shape_errors = []
    for key, expected_type in required_shapes.items():
        value = report_input.get(key)
        if not isinstance(value, expected_type):
            shape_errors.append(f"{key}=missing_or_wrong_type")
    if shape_errors:
        return fail(f"{fixture.name}: enhanced input", ", ".join(shape_errors))

    total_jobs = int(((report_input.get("sample") or {}).get("total_jobs")) or 0)
    sample_job_ids = {int(value) for value in ((report_input.get("sample") or {}).get("job_ids") or [])}
    errors = []
    errors.extend(validate_term_counts(report_input["technical_terms_top"], total_jobs, sample_job_ids))
    errors.extend(validate_salary_summary(report_input["salary_summary"]))
    errors.extend(validate_technical_layers(report_input["technical_terms_layers"]))
    errors.extend(validate_representative_jobs(report_input["representative_jobs"], total_jobs))
    if errors:
        return fail(f"{fixture.name}: enhanced input", "; ".join(errors[:6]))
    return ok(
        f"{fixture.name}: enhanced input",
        (
            f"technical_terms_top={len(report_input['technical_terms_top'])}, "
            f"parsed_salary={report_input['salary_summary'].get('parsed_count')}, "
            f"representative_jobs={len(report_input['representative_jobs'])}"
        ),
    )


def check_report_input_compact(
    fixture: Fixture,
    report_input: dict[str, Any],
    conn: sqlite3.Connection,
    job_ids: list[int],
) -> CheckResult:
    raw_keys = find_keys(report_input, {"raw_job_text", "job_text", "description_text"})
    if raw_keys:
        return fail(f"{fixture.name}: compact input", f"raw text keys found: {raw_keys[:5]}")

    serialized = json.dumps(report_input, ensure_ascii=False)
    raw_rows = conn.execute(
        f"""
        SELECT id, raw_job_text
        FROM job_details
        WHERE id IN ({",".join("?" for _ in job_ids)})
        """,
        tuple(job_ids),
    ).fetchall()
    long_hits: list[int] = []
    for row in raw_rows:
        raw_text = clean_spaces(str(row["raw_job_text"] or ""))
        if len(raw_text) < 500:
            continue
        probe = raw_text[:500]
        if probe and probe in clean_spaces(serialized):
            long_hits.append(int(row["id"]))
    if long_hits:
        return fail(f"{fixture.name}: compact input", f"long raw text appears for job_ids={long_hits}")
    return ok(f"{fixture.name}: compact input", "no large job text detected")


def validate_term_counts(items: list[Any], total_jobs: int, sample_job_ids: set[int]) -> list[str]:
    errors: list[str] = []
    if not items:
        return ["technical_terms_top is empty"]
    for item in items:
        if not isinstance(item, dict):
            errors.append("technical_terms_top contains non-object item")
            continue
        name = text(item.get("name")) or "<unnamed>"
        job_ids = [int(value) for value in item.get("job_ids") or []]
        unique_job_ids = set(job_ids)
        count = int(item.get("count") or 0)
        ratio = float(item.get("ratio") or 0)
        expected_ratio = round(count / total_jobs, 4) if total_jobs else 0
        if count != len(unique_job_ids):
            errors.append(f"{name}: count={count}, unique_job_ids={len(unique_job_ids)}")
        if sample_job_ids and not unique_job_ids.issubset(sample_job_ids):
            errors.append(f"{name}: job_ids outside sample")
        if abs(ratio - expected_ratio) > 0.0001:
            errors.append(f"{name}: ratio={ratio}, expected={expected_ratio}")
    return errors


def validate_salary_summary(summary: dict[str, Any]) -> list[str]:
    parsed_count = int(summary.get("parsed_count") or 0)
    monthly_count = int((summary.get("monthly_cny") or {}).get("count") or 0)
    daily_count = int((summary.get("daily_cny") or {}).get("count") or 0)
    if parsed_count <= 0:
        return ["salary_summary has no parsed salaries"]
    if parsed_count != monthly_count + daily_count:
        return [f"salary_summary parsed_count={parsed_count}, monthly+daily={monthly_count + daily_count}"]
    return []


def validate_technical_layers(layers: dict[str, Any]) -> list[str]:
    required = {"core", "common", "nice_to_have", "niche_signals"}
    missing = sorted(required - set(layers))
    if missing:
        return ["technical_terms_layers missing: " + ", ".join(missing)]
    wrong = [key for key in required if not isinstance(layers.get(key), list)]
    if wrong:
        return ["technical_terms_layers non-list values: " + ", ".join(sorted(wrong))]
    if not any(layers.get(key) for key in required):
        return ["technical_terms_layers is empty"]
    return []


def validate_representative_jobs(items: list[Any], total_jobs: int) -> list[str]:
    if not items:
        return ["representative_jobs is empty"]
    if len(items) > min(12, total_jobs):
        return [f"representative_jobs={len(items)}, max={min(12, total_jobs)}"]
    errors: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            errors.append("representative_jobs contains non-object item")
            continue
        raw_keys = find_keys(item, {"raw_job_text", "job_text", "description_text"})
        if raw_keys:
            errors.append(f"representative job raw keys: {raw_keys[:3]}")
        if len(json.dumps(item, ensure_ascii=False)) > 700:
            errors.append(f"representative job too long: job_id={item.get('job_id')}")
    return errors


def check_evidence_quotes(conn: sqlite3.Connection, fixture: Fixture, job_ids: list[int]) -> CheckResult:
    rows = conn.execute(
        f"""
        SELECT
            jd.id,
            jd.job_title,
            jd.raw_job_text,
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
        WHERE jd.id IN ({",".join("?" for _ in job_ids)})
        ORDER BY jd.id
        """,
        tuple(job_ids),
    ).fetchall()
    total = 0
    exact = 0
    misses: list[str] = []
    for row in rows:
        source = f"{row['job_title']}\n{row['raw_job_text']}"
        payload = parse_json_object(row["output_json"])
        for evidence in collect_evidence(payload):
            quote = text(evidence.get("quote"))
            if not quote:
                continue
            total += 1
            if quote in source:
                exact += 1
            elif len(misses) < 5:
                misses.append(f"job_id={row['id']} quote={quote[:80]}")
    if total == 0:
        return fail(f"{fixture.name}: evidence quotes", "no evidence quotes found")
    ratio = exact / total
    detail = f"exact={exact}/{total}, ratio={ratio:.4f}"
    if misses:
        detail = f"{detail}, miss_samples={misses}"
    if ratio < MIN_EVIDENCE_EXACT_RATIO:
        return warn(f"{fixture.name}: evidence quotes", detail)
    return ok(f"{fixture.name}: evidence quotes", detail)


def check_final_report(fixture: Fixture, final_report: dict[str, Any]) -> CheckResult:
    try:
        report = AIJobReport.model_validate(final_report)
    except Exception as exc:  # noqa: BLE001
        return fail(f"{fixture.name}: final report", f"schema error: {exc}")

    missing: list[str] = []
    if not text(report.role_profile.summary):
        missing.append("role_profile")
    if not report.learning_route:
        missing.append("learning_route")
    if not report.project_suggestions:
        missing.append("project_suggestions")

    new_shape = bool(
        report.technical_top15_interpretation
        or report.skill_layers.core
        or report.skill_layers.common
        or report.skill_layers.nice_to_have
        or report.resume_keywords
        or text(report.salary_and_threshold.summary) != "\u672a\u751f\u6210"
    )
    if new_shape:
        if not report.technical_top15_interpretation:
            missing.append("technical_top15_interpretation")
        if not (report.skill_layers.core or report.skill_layers.common or report.skill_layers.nice_to_have):
            missing.append("skill_layers")
        if text(report.salary_and_threshold.summary) == "\u672a\u751f\u6210":
            missing.append("salary_and_threshold")
        if not report.resume_keywords:
            missing.append("resume_keywords")
        if not report.job_search_advice:
            missing.append("job_search_advice")
        if not report.caveats:
            missing.append("caveats")
        shape_name = "enhanced"
    else:
        if not report.core_skills:
            missing.append("core_skills")
        if not report.ability_requirements:
            missing.append("ability_requirements")
        shape_name = "legacy"

    if missing:
        return fail(f"{fixture.name}: final report", "missing sections: " + ", ".join(missing))
    return ok(
        f"{fixture.name}: final report",
        (
            f"shape={shape_name}, title={report.report_title}, "
            f"tech_top15={len(report.technical_top15_interpretation)}, "
            f"core_skills={len(report.core_skills)}, learning_steps={len(report.learning_route)}, "
            f"projects={len(report.project_suggestions)}"
        ),
    )


def check_cached_extractions(conn: sqlite3.Connection, fixture: Fixture, job_ids: list[int]) -> CheckResult:
    model_name = resolve_model_name()
    rows = conn.execute(
        f"""
        SELECT
            jd.id,
            jd.raw_text_hash,
            jsr.query_city,
            jsr.query_keyword
        FROM job_details jd
        JOIN job_search_run_items sri ON sri.job_detail_id = jd.id
        JOIN job_search_runs jsr ON jsr.id = sri.search_run_id
        WHERE jsr.id = ?
          AND jd.id IN ({",".join("?" for _ in job_ids)})
        ORDER BY jd.id
        """,
        (fixture.search_run_id, *job_ids),
    ).fetchall()
    missing: list[int] = []
    for row in rows:
        input_hash = extraction_input_hash(
            model_name=model_name,
            job_id=int(row["id"]),
            raw_text_hash=text(row["raw_text_hash"]),
            query_city=text(row["query_city"]),
            query_keyword=text(row["query_keyword"]),
        )
        hit = conn.execute(
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
            (int(row["id"]), DEFAULT_EXTRACTOR_NAME, DEFAULT_SCHEMA_VERSION, input_hash),
        ).fetchone()
        if hit is None:
            missing.append(int(row["id"]))
    if missing:
        return fail(
            f"{fixture.name}: extraction cache",
            f"model={model_name}, missing_cached_job_ids={missing}",
        )
    return ok(f"{fixture.name}: extraction cache", f"all {len(rows)} fixture jobs are cached for model={model_name}")


def check_role_direction(fixture: Fixture, report_input: dict[str, Any], final_report: dict[str, Any]) -> CheckResult:
    haystack = json.dumps(report_input, ensure_ascii=False) + json.dumps(final_report, ensure_ascii=False)
    if fixture.name == "shenzhen_ai_app":
        expected_terms = ["Python", "RAG", "Dify", "Coze"]
    elif fixture.name == "hangzhou_slam":
        expected_terms = ["SLAM", "C++", "ROS", "VIO"]
    else:
        expected_terms = []
    hits = [term for term in expected_terms if term.lower() in haystack.lower()]
    if len(hits) < 2:
        return warn(f"{fixture.name}: role direction", f"hits={hits}, expected_terms={expected_terms}")
    return ok(f"{fixture.name}: role direction", f"hits={hits}")


def load_latest_extractions(conn: sqlite3.Connection, job_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not job_ids:
        return {}
    rows = conn.execute(
        f"""
        SELECT job_detail_id, output_json
        FROM job_extractions
        WHERE id IN (
            SELECT MAX(id)
            FROM job_extractions
            WHERE job_detail_id IN ({",".join("?" for _ in job_ids)})
              AND status = 'completed'
            GROUP BY job_detail_id
        )
        """,
        tuple(job_ids),
    ).fetchall()
    return {int(row["job_detail_id"]): parse_json_object(row["output_json"]) for row in rows}


def has_required_extraction_shape(payload: dict[str, Any]) -> bool:
    required_scalars = ["job_id", "role_intent", "normalized_role", "role_family"]
    required_lists = ["technical_stack", "tools_platforms", "business_domains", "ability_requirements"]
    required_objects = ["experience_requirements", "education_requirements", "graduate_friendliness"]
    for key in required_scalars:
        if key not in payload or text(payload.get(key)) == "":
            return False
    for key in required_lists:
        if key not in payload or not isinstance(payload.get(key), list):
            return False
    for key in required_objects:
        if key not in payload or not isinstance(payload.get(key), dict):
            return False
    return bool(payload.get("ability_requirements"))


def extraction_input_hash(
    model_name: str,
    job_id: int,
    raw_text_hash: str,
    query_city: str,
    query_keyword: str,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS_PER_JOB,
) -> str:
    import hashlib

    payload = {
        "model_name": model_name,
        "schema_version": DEFAULT_SCHEMA_VERSION,
        "job_id": job_id,
        "raw_text_hash": raw_text_hash,
        "query_city": query_city,
        "query_keyword": query_keyword,
        "max_text_chars": max_text_chars,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def resolve_model_name() -> str:
    env_model = os.getenv("OPENAI_MODEL")
    if env_model:
        return env_model
    secrets_path = Path(".streamlit") / "secrets.toml"
    if not secrets_path.exists():
        return "gpt-5.5"
    try:
        import tomllib

        secrets = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "gpt-5.5"
    return text(secrets.get("OPENAI_MODEL")) or "gpt-5.5"



def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"required file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return payload


def parse_json_object(value: object) -> dict[str, Any]:
    try:
        payload = json.loads(text(value) or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def find_keys(value: Any, target_keys: set[str], prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in target_keys:
                hits.append(path)
            hits.extend(find_keys(child, target_keys, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(find_keys(child, target_keys, f"{prefix}[{index}]"))
    return hits


def clean_spaces(value: str) -> str:
    return " ".join(value.split())


def ok(name: str, details: str) -> CheckResult:
    return CheckResult("PASS", name, details)


def warn(name: str, details: str) -> CheckResult:
    return CheckResult("WARN", name, details)


def fail(name: str, details: str) -> CheckResult:
    return CheckResult("FAIL", name, details)


def print_results(results: list[CheckResult]) -> None:
    print("JobUWant Analysis Harness\n")
    for result in results:
        print(f"[{result.status}] {result.name}: {result.details}")


def text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the JobUWant analysis pipeline fixtures.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--token-budget", type=int, default=0, help="Optional stricter report-input token limit.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
