from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateSource:
    title: str
    url: str
    snippet: str
    source_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_type": self.source_type,
        }

    def to_display_dict(self) -> dict[str, str]:
        return {
            "\u6807\u9898": self.title,
            "\u94fe\u63a5": self.url,
            "\u6458\u8981": self.snippet,
            "\u6765\u6e90\u7c7b\u578b": self.source_type,
        }


@dataclass(frozen=True)
class CandidateCompany:
    company_name: str
    possible_category: str
    related_direction: str
    evidence_url: str
    matched_keywords: str
    confidence_label: str
    official_domain: str = ""
    official_domain_verified: bool = False
    verification_notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "company_name": self.company_name,
            "possible_category": self.possible_category,
            "related_direction": self.related_direction,
            "evidence_url": self.evidence_url,
            "matched_keywords": self.matched_keywords,
            "confidence_label": self.confidence_label,
            "official_domain": self.official_domain,
            "official_domain_verified": int(self.official_domain_verified),
            "verification_notes": self.verification_notes,
        }

    def to_display_dict(self) -> dict[str, object]:
        return {
            "\u516c\u53f8": self.company_name,
            "\u7c7b\u522b": self.possible_category,
            "\u76f8\u5173\u65b9\u5411": self.related_direction,
            "\u8bc1\u636e\u94fe\u63a5": self.evidence_url,
            "\u5339\u914d\u5173\u952e\u8bcd": self.matched_keywords,
            "\u7f6e\u4fe1\u5ea6": self.confidence_label,
            "\u5b98\u65b9\u57df\u540d": self.official_domain,
            "\u5b98\u65b9\u9a8c\u8bc1": "yes" if self.official_domain_verified else "no",
            "\u9a8c\u8bc1\u8bf4\u660e": self.verification_notes,
        }


@dataclass(frozen=True)
class JobLead:
    company_name: str
    job_title_guess: str
    url: str
    snippet: str
    source_type: str
    source_confidence: str
    status: str = "candidate"

    def to_dict(self) -> dict[str, str]:
        return {
            "company_name": self.company_name,
            "job_title_guess": self.job_title_guess,
            "url": self.url,
            "snippet": self.snippet,
            "source_type": self.source_type,
            "source_confidence": self.source_confidence,
            "status": self.status,
        }

    def to_display_dict(self) -> dict[str, str]:
        return {
            "\u516c\u53f8": self.company_name,
            "\u5c97\u4f4d\u7ebf\u7d22": self.job_title_guess,
            "\u94fe\u63a5": self.url,
            "\u6458\u8981": self.snippet,
            "\u6765\u6e90\u7c7b\u578b": self.source_type,
            "\u6765\u6e90\u53ef\u4fe1\u5ea6": self.source_confidence,
            "\u72b6\u6001": self.status,
        }


@dataclass(frozen=True)
class ParsedJobDetail:
    company_name: str
    job_title: str
    city: str
    recruitment_stage: str
    responsibilities: str
    requirements: str
    technical_keywords: list[str]
    original_url: str
    raw_job_text: str
    source_type: str
    source_confidence: str
    parse_confidence: str
    content_hash: str
    status: str = "parsed"
    error_message: str = ""

    def to_storage_dict(self) -> dict[str, object]:
        return {
            "company_name": self.company_name,
            "job_title": self.job_title,
            "city": self.city,
            "recruitment_stage": self.recruitment_stage,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "technical_keywords": self.technical_keywords,
            "original_url": self.original_url,
            "raw_job_text": self.raw_job_text,
            "source_type": self.source_type,
            "source_confidence": self.source_confidence,
            "parse_confidence": self.parse_confidence,
            "content_hash": self.content_hash,
            "status": self.status,
            "error_message": self.error_message,
        }

    def to_display_dict(self) -> dict[str, object]:
        return {
            "\u516c\u53f8": self.company_name,
            "\u5c97\u4f4d": self.job_title,
            "\u57ce\u5e02": self.city,
            "\u62db\u8058\u9636\u6bb5": self.recruitment_stage,
            "\u6280\u672f\u5173\u952e\u8bcd": ", ".join(self.technical_keywords),
            "\u6765\u6e90\u7c7b\u578b": self.source_type,
            "\u6765\u6e90\u53ef\u4fe1\u5ea6": self.source_confidence,
            "\u89e3\u6790\u7f6e\u4fe1\u5ea6": self.parse_confidence,
            "\u72b6\u6001": self.status,
            "\u94fe\u63a5": self.original_url,
        }


@dataclass(frozen=True)
class UsageSnapshot:
    candidate_sources: int = 0
    changed_records: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cny: float = 0.0

    def plus(self, other: "UsageSnapshot") -> "UsageSnapshot":
        return UsageSnapshot(
            candidate_sources=self.candidate_sources + other.candidate_sources,
            changed_records=self.changed_records + other.changed_records,
            model_calls=self.model_calls + other.model_calls,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            estimated_cny=self.estimated_cny + other.estimated_cny,
        )


@dataclass(frozen=True)
class DiscoveryResult:
    candidates: list[CandidateCompany]
    sources: list[CandidateSource]
    usage: UsageSnapshot
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class JobDetailCollectionResult:
    leads: list[JobLead] = field(default_factory=list)
    details: list[ParsedJobDetail] = field(default_factory=list)
    usage: UsageSnapshot = field(default_factory=UsageSnapshot)
    elapsed_seconds: float = 0.0

