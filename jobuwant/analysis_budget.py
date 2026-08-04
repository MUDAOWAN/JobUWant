from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisBudget:
    tier: str
    min_jobs: int
    max_jobs: int | None
    max_jobs_for_ai_extraction: int
    max_text_chars_per_job: int
    max_technical_stack_items: int
    max_tools_platforms_items: int
    max_business_domains_items: int
    max_ability_items: int
    evidence_per_item: int
    top_technical_stack: int
    top_ability_requirements: int
    max_report_evidence: int
    report_token_budget: int
    max_output_tokens: int
    sampling_strategy: str


BUDGET_TIERS: tuple[AnalysisBudget, ...] = (
    AnalysisBudget(
        tier="1-10",
        min_jobs=1,
        max_jobs=10,
        max_jobs_for_ai_extraction=10,
        max_text_chars_per_job=2600,
        max_technical_stack_items=12,
        max_tools_platforms_items=10,
        max_business_domains_items=8,
        max_ability_items=12,
        evidence_per_item=3,
        top_technical_stack=15,
        top_ability_requirements=12,
        max_report_evidence=36,
        report_token_budget=18000,
        max_output_tokens=6000,
        sampling_strategy="full",
    ),
    AnalysisBudget(
        tier="11-30",
        min_jobs=11,
        max_jobs=30,
        max_jobs_for_ai_extraction=30,
        max_text_chars_per_job=2000,
        max_technical_stack_items=10,
        max_tools_platforms_items=8,
        max_business_domains_items=6,
        max_ability_items=10,
        evidence_per_item=1,
        top_technical_stack=15,
        top_ability_requirements=10,
        max_report_evidence=24,
        report_token_budget=30000,
        max_output_tokens=9000,
        sampling_strategy="full",
    ),
    AnalysisBudget(
        tier="31-50",
        min_jobs=31,
        max_jobs=50,
        max_jobs_for_ai_extraction=50,
        max_text_chars_per_job=1400,
        max_technical_stack_items=8,
        max_tools_platforms_items=6,
        max_business_domains_items=5,
        max_ability_items=8,
        evidence_per_item=1,
        top_technical_stack=15,
        top_ability_requirements=8,
        max_report_evidence=20,
        report_token_budget=50000,
        max_output_tokens=12000,
        sampling_strategy="full",
    ),
    AnalysisBudget(
        tier="51-100",
        min_jobs=51,
        max_jobs=100,
        max_jobs_for_ai_extraction=80,
        max_text_chars_per_job=1000,
        max_technical_stack_items=6,
        max_tools_platforms_items=5,
        max_business_domains_items=4,
        max_ability_items=6,
        evidence_per_item=1,
        top_technical_stack=12,
        top_ability_requirements=8,
        max_report_evidence=16,
        report_token_budget=50000,
        max_output_tokens=14000,
        sampling_strategy="match_score_first",
    ),
    AnalysisBudget(
        tier="100+",
        min_jobs=101,
        max_jobs=None,
        max_jobs_for_ai_extraction=60,
        max_text_chars_per_job=900,
        max_technical_stack_items=5,
        max_tools_platforms_items=4,
        max_business_domains_items=3,
        max_ability_items=5,
        evidence_per_item=1,
        top_technical_stack=10,
        top_ability_requirements=6,
        max_report_evidence=12,
        report_token_budget=50000,
        max_output_tokens=14000,
        sampling_strategy="role_family_and_match_score",
    ),
)


def budget_for_job_count(job_count: int) -> AnalysisBudget:
    count = max(1, job_count)
    for budget in BUDGET_TIERS:
        if budget.max_jobs is None:
            return budget
        if budget.min_jobs <= count <= budget.max_jobs:
            return budget
    return BUDGET_TIERS[-1]


def budget_for_tier(tier: str) -> AnalysisBudget:
    normalized = tier.strip().lower()
    if normalized == "auto":
        raise ValueError("auto tier requires a job count")
    for budget in BUDGET_TIERS:
        if budget.tier.lower() == normalized:
            return budget
    allowed = ", ".join(["auto", *(budget.tier for budget in BUDGET_TIERS)])
    raise ValueError(f"unknown budget tier: {tier}; allowed: {allowed}")


def resolve_budget(tier: str, job_count: int) -> AnalysisBudget:
    if tier.strip().lower() == "auto":
        return budget_for_job_count(job_count)
    return budget_for_tier(tier)


def tier_names() -> list[str]:
    return ["auto", *(budget.tier for budget in BUDGET_TIERS)]
