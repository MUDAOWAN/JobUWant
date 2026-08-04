from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class QuerySpec:
    role: str
    city: str
    hiring_stage: str
    candidate_status: str

    def with_updates(self, **updates: str) -> "QuerySpec":
        return replace(self, **updates)


@dataclass(frozen=True)
class FirstRunBudget:
    max_candidate_sources: int = 20
    max_changed_records: int = 10
    max_model_calls: int = 10
    max_estimated_cny: float = 5.0


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str
    base_url: str | None = None
    model: str = "gpt-5.5"
    max_candidates: int = 10
    search_context_size: str = "low"
    estimated_cny_per_call: float = 0.1


DEFAULT_QUERY = QuerySpec(
    role="SLAM \u5de5\u7a0b\u5e08 / SLAM \u7b97\u6cd5\u5de5\u7a0b\u5e08",
    city="\u676d\u5dde",
    hiring_stage="\u6821\u62db\u79cb\u62db / \u63d0\u524d\u6279",
    candidate_status="\u5e94\u5c4a\u751f",
)
