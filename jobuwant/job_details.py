from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from jobuwant.config import OpenAISettings, QuerySpec
from jobuwant.models import JobLead, ParsedJobDetail, UsageSnapshot


MAX_RAW_TEXT_CHARS = 18000
MIN_JOB_TEXT_CHARS = 200

THIRD_PARTY_DOMAIN_MARKERS = {
    "zhipin.com",
    "liepin.com",
    "51job.com",
    "lagou.com",
    "nowcoder.com",
    "niuqizp.com",
    "bebee.com",
    "wondercv.com",
    "zhaopin.com",
    "yingjiesheng.com",
    "job.hdu.edu.cn",
    "career.nankai.edu.cn",
    "leetcode.cn",
    "teamedupchina.com",
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
}

NOISE_LINE_PATTERNS = [
    r"copyright\s*[©(c)]?",
    r"all rights reserved",
    r"版权所有",
    r"ICP备",
    r"公网安备",
    r"浙公网安备",
    r"中国大陆\s*/\s*简体中文",
    r"简体中文",
    r"English",
    r"登录|注册|分享|关注|扫码|微信|公众号",
    r"隐私政策|用户协议|法律声明",
]

JOB_MARKERS = [
    "岗位职责",
    "工作职责",
    "职位描述",
    "岗位描述",
    "工作内容",
    "任职要求",
    "职位要求",
    "岗位要求",
    "任职资格",
    "工作地点",
    "职位类别",
]


class JobDetailSchema(BaseModel):
    company_name: str = Field(default="")
    job_title: str = Field(default="")
    city: str = Field(default="")
    recruitment_stage: str = Field(default="")
    responsibilities: str = Field(default="")
    requirements: str = Field(default="")
    technical_keywords: list[str] = Field(default_factory=list)
    parse_confidence: str = Field(default="low")

    @field_validator("parse_confidence")
    @classmethod
    def _confidence_label(cls, value: str) -> str:
        normalized = (value or "low").strip().lower()
        if normalized not in {"high", "medium", "low"}:
            return "low"
        return normalized


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag.lower() in {"p", "br", "li", "div", "section", "h1", "h2", "h3", "tr"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "li", "div", "section", "tr"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        joined = " ".join(self._parts)
        joined = html.unescape(joined)
        joined = re.sub(r"[ \t\r\f\v]+", " ", joined)
        joined = re.sub(r"\n\s*\n+", "\n", joined)
        return joined.strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def base_domain(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = [part for part in host.split(".") if part]
    if len(parts) <= 2:
        return host
    compound_suffixes = {"com.cn", "net.cn", "org.cn", "edu.cn", "gov.cn", "co.jp", "com.hk"}
    suffix = ".".join(parts[-2:])
    if suffix in compound_suffixes and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_third_party_job_site(url: str) -> bool:
    domain = base_domain(url)
    host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    return any(marker in {domain, host} or host.endswith("." + marker) for marker in THIRD_PARTY_DOMAIN_MARKERS)


def same_base_domain(url: str, reference_url: str) -> bool:
    return bool(url and reference_url and base_domain(url) == base_domain(reference_url))


def infer_source_type(url: str, fallback: str = "unknown") -> str:
    if is_third_party_job_site(url):
        return "third_party_platform"
    lower = url.lower()
    official_markers = ["career", "careers", "campus", "jobs.", "job.", "join", "hr", "position"]
    if any(marker in lower for marker in official_markers):
        return "company_official"
    return fallback or "unknown"


def score_source_confidence(source_type: str, has_raw_text: bool) -> str:
    if source_type in {"company_official", "campus_official"} and has_raw_text:
        return "high"
    if source_type == "company_official":
        return "medium"
    if source_type == "third_party_platform":
        return "low"
    if source_type == "user_provided_text" and has_raw_text:
        return "medium"
    if source_type in {"search_summary", "openai_web_search"}:
        return "low"
    return "medium" if has_raw_text else "low"


def is_acceptable_official_url(url: str) -> bool:
    return url.startswith(("http://", "https://")) and not is_third_party_job_site(url)


def rule_extract_keywords(text: str) -> list[str]:
    keyword_map = {
        "SLAM": ["slam", "同步定位", "定位与建图"],
        "激光SLAM": ["激光slam", "laser slam", "lidar slam"],
        "视觉SLAM": ["视觉slam", "visual slam", "vslam"],
        "定位": ["定位", "localization"],
        "建图": ["建图", "mapping"],
        "导航": ["导航", "navigation"],
        "自主导航": ["自主导航", "autonomous navigation"],
        "路径规划": ["路径规划", "path planning"],
        "全局规划": ["全局规划", "global planning"],
        "局部规划": ["局部规划", "local planning"],
        "机器人": ["机器人", "robot", "robotics"],
        "ROS": ["ros"],
        "ROS2": ["ros2"],
        "C": [" c语言", " c ", " c/"],
        "C++": ["c++", "cpp"],
        "Python": ["python"],
        "OpenCV": ["opencv"],
        "PCL": ["pcl", "point cloud library"],
        "Eigen": ["eigen"],
        "Ceres": ["ceres"],
        "GTSAM": ["gtsam"],
        "Linux": ["linux"],
        "Git": ["git"],
        "Docker": ["docker"],
        "传感器融合": ["传感器融合", "sensor fusion", "多传感器融合"],
        "视觉": ["视觉", "vision", "camera"],
        "Camera": ["camera", "相机"],
        "激光雷达": ["激光雷达", "lidar", "laser"],
        "IMU": ["imu", "惯导"],
        "GNSS": ["gnss", "gps"],
        "轮速计": ["轮速计", "wheel odometry"],
        "里程计": ["里程计", "odometry"],
        "点云": ["点云", "point cloud"],
        "三维重建": ["三维重建", "3d reconstruction"],
        "地形重建": ["地形重建", "terrain reconstruction"],
        "高程图": ["高程图", "elevation map"],
        "标定": ["标定", "calibration"],
        "回环检测": ["回环", "loop closure"],
        "图优化": ["图优化", "graph optimization"],
        "卡尔曼滤波": ["kalman", "ekf", "ukf", "卡尔曼"],
        "粒子滤波": ["particle filter", "粒子滤波"],
        "深度学习": ["深度学习", "deep learning"],
        "PyTorch": ["pytorch"],
        "TensorFlow": ["tensorflow"],
    }
    normalized = f" {text.lower()} "
    found: list[str] = []
    for label, terms in keyword_map.items():
        if any(term in normalized for term in terms):
            found.append(label)
    return found


def rule_extract_city(text: str, default_city: str) -> str:
    if "杭州" in text or "hangzhou" in text.lower():
        return "杭州"
    if "浙江" in text or "zhejiang" in text.lower():
        return "浙江"
    return default_city


def fetch_public_page_text(url: str, timeout: int = 12) -> str:
    if not is_acceptable_official_url(url):
        return ""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 JobUWant local research tool",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("content-type", "")
            body = response.read(2_000_000)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""
    if "text/html" not in content_type and "text/plain" not in content_type:
        return ""
    encoding = "utf-8"
    match = re.search(r"charset=([^;]+)", content_type, re.I)
    if match:
        encoding = match.group(1).strip()
    raw = body.decode(encoding, errors="ignore")
    if "text/plain" in content_type:
        return focus_job_text(clean_job_text(raw))
    parser = _TextExtractor()
    parser.feed(raw)
    return focus_job_text(clean_job_text(parser.text()))


def clean_job_text(text: str) -> str:
    cleaned = html.unescape(text or "")
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in cleaned.splitlines():
        line = raw_line.strip(" \t|/-_")
        if not line:
            continue
        if len(line) <= 1:
            continue
        lowered = line.lower()
        if any(re.search(pattern, lowered, re.I) for pattern in NOISE_LINE_PATTERNS):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines).strip()[:MAX_RAW_TEXT_CHARS]


def focus_job_text(text: str) -> str:
    if not text:
        return ""
    marker_positions = [text.find(marker) for marker in JOB_MARKERS if marker in text]
    marker_positions = [position for position in marker_positions if position >= 0]
    if not marker_positions:
        return text[:MAX_RAW_TEXT_CHARS]
    start = max(0, min(marker_positions) - 1200)
    focused = text[start : start + MAX_RAW_TEXT_CHARS]
    return focused.strip()


def validate_job_page_text(raw_text: str, query: QuerySpec) -> dict[str, object]:
    cleaned = focus_job_text(clean_job_text(raw_text))
    lowered = cleaned.lower()
    notes: list[str] = []
    marker_count = sum(1 for marker in JOB_MARKERS if marker in cleaned)
    keyword_count = len(rule_extract_keywords(cleaned))
    target_terms = [
        query.role.lower(),
        query.city.lower(),
        "slam",
        "localization",
        "mapping",
        "navigation",
        "robotics",
        "杭州",
        "浙江",
        "校招",
        "应届",
        "提前批",
        "实习",
    ]
    target_hits = sum(1 for term in target_terms if term and term in lowered)
    list_like_terms = ["职位列表", "全部职位", "搜索职位", "岗位列表", "job list", "all jobs", "search jobs"]
    is_list_like = any(term in cleaned or term in lowered for term in list_like_terms)

    if len(cleaned) < 500:
        notes.append("raw text shorter than 500 chars")
    if marker_count == 0:
        notes.append("missing job-detail markers")
    if keyword_count == 0:
        notes.append("missing technical keywords")
    if target_hits == 0:
        notes.append("missing target role/city/stage signals")
    if is_list_like and marker_count < 2:
        notes.append("page looks like a job list or career home")

    ready = len(cleaned) >= 500 and marker_count >= 1 and keyword_count >= 1 and target_hits >= 1
    status = "ready_for_parse" if ready else "lead_only"
    return {
        "ready_for_parse": ready,
        "status": status,
        "text_chars": len(cleaned),
        "job_marker_count": marker_count,
        "technical_keyword_count": keyword_count,
        "target_signal_count": target_hits,
        "notes": "; ".join(notes) if notes else "page text passed quality checks",
    }


def parse_job_detail_with_rules(
    lead: JobLead,
    raw_text: str,
    query: QuerySpec,
    error_message: str = "",
) -> ParsedJobDetail:
    cleaned = focus_job_text(clean_job_text(raw_text))
    source_type = infer_source_type(lead.url, lead.source_type)
    has_raw_text = len(cleaned) >= MIN_JOB_TEXT_CHARS
    return ParsedJobDetail(
        company_name=lead.company_name,
        job_title=lead.job_title_guess or query.role,
        city=rule_extract_city(cleaned, query.city),
        recruitment_stage=query.hiring_stage,
        responsibilities="",
        requirements="",
        technical_keywords=rule_extract_keywords(cleaned),
        original_url=lead.url,
        raw_job_text=cleaned,
        source_type=source_type,
        source_confidence=score_source_confidence(source_type, has_raw_text),
        parse_confidence="low",
        content_hash=content_hash(cleaned or lead.url),
        status="needs_text" if not has_raw_text else "needs_model_parse",
        error_message=error_message,
    )


def parse_job_detail_with_openai(
    lead: JobLead,
    raw_text: str,
    query: QuerySpec,
    settings: OpenAISettings,
) -> tuple[ParsedJobDetail, UsageSnapshot, str, str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI parsing requires the `openai` package.") from exc

    cleaned = focus_job_text(clean_job_text(raw_text))
    if len(cleaned) < MIN_JOB_TEXT_CHARS:
        detail = parse_job_detail_with_rules(
            lead=lead,
            raw_text=cleaned,
            query=query,
            error_message="raw job text is too short for model parsing",
        )
        return detail, UsageSnapshot(), "{}", detail.error_message

    client_kwargs = {"api_key": settings.api_key}
    if settings.base_url:
        client_kwargs["base_url"] = settings.base_url
    client = OpenAI(**client_kwargs)

    prompt = _build_parse_prompt(lead=lead, raw_text=cleaned, query=query)
    response = client.responses.create(model=settings.model, input=prompt)
    text = getattr(response, "output_text", "") or ""
    output_json = _extract_json_text(text)
    validation_errors = ""
    try:
        schema = JobDetailSchema.model_validate_json(output_json)
    except ValidationError as exc:
        validation_errors = str(exc)
        rule_detail = parse_job_detail_with_rules(
            lead=lead,
            raw_text=cleaned,
            query=query,
            error_message=validation_errors,
        )
        usage = _usage_from_response(response, settings)
        return rule_detail, usage, output_json, validation_errors

    rule_keywords = rule_extract_keywords(cleaned)
    keywords = _merge_keywords(schema.technical_keywords, rule_keywords)
    source_type = infer_source_type(lead.url, lead.source_type)
    detail = ParsedJobDetail(
        company_name=schema.company_name.strip() or lead.company_name,
        job_title=schema.job_title.strip() or lead.job_title_guess or query.role,
        city=schema.city.strip() or rule_extract_city(cleaned, query.city),
        recruitment_stage=schema.recruitment_stage.strip() or query.hiring_stage,
        responsibilities=schema.responsibilities.strip(),
        requirements=schema.requirements.strip(),
        technical_keywords=keywords,
        original_url=lead.url,
        raw_job_text=cleaned,
        source_type=source_type,
        source_confidence=score_source_confidence(source_type, True),
        parse_confidence=schema.parse_confidence,
        content_hash=content_hash(cleaned),
        status="auto_parsed",
    )
    usage = _usage_from_response(response, settings)
    return detail, usage, output_json, validation_errors


def _build_parse_prompt(lead: JobLead, raw_text: str, query: QuerySpec) -> str:
    return f"""
You extract structured job details for a local job-search research tool.

Target query:
- Role: {query.role}
- City: {query.city}
- Hiring stage: {query.hiring_stage}
- Candidate status: {query.candidate_status}

Candidate lead:
- Company: {lead.company_name}
- Job title guess: {lead.job_title_guess}
- URL: {lead.url}

Rules:
- Use only the raw job text as evidence.
- Ignore page navigation, language selectors, copyright, ICP records, public security registration text, social links, and footer text.
- If the page contains multiple jobs, extract the job that best matches SLAM / localization / mapping / navigation / robotics algorithm.
- If a field is not present, return an empty string instead of inventing it.
- Responsibilities and requirements should preserve key original meaning.
- technical_keywords must be detailed and include all explicit technical terms, tools, algorithms, sensors, programming languages, libraries, robotics frameworks, math/optimization methods, and domain tasks found in the job text.
- parse_confidence must be high, medium, or low.
- Return JSON only. Do not wrap it in Markdown.

JSON schema:
{{
  "company_name": "company name",
  "job_title": "job title",
  "city": "city or location",
  "recruitment_stage": "campus|graduate|intern|junior|social|unknown or original wording",
  "responsibilities": "job responsibilities, preferably bullet-like text",
  "requirements": "candidate requirements, preferably bullet-like text",
  "technical_keywords": ["SLAM", "C++"],
  "parse_confidence": "high|medium|low"
}}

Raw job text:
{raw_text[:MAX_RAW_TEXT_CHARS]}
""".strip()


def _extract_json_text(text: str) -> str:
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


def _merge_keywords(model_keywords: list[str], rule_keywords: list[str]) -> list[str]:
    merged: list[str] = []
    for keyword in [*model_keywords, *rule_keywords]:
        cleaned = str(keyword).strip()
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    return merged[:60]


def _usage_from_response(response: Any, settings: OpenAISettings) -> UsageSnapshot:
    usage = getattr(response, "usage", None)
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    return UsageSnapshot(
        model_calls=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cny=settings.estimated_cny_per_call,
    )


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


def detail_to_json(detail: ParsedJobDetail) -> str:
    return json.dumps(detail.to_storage_dict(), ensure_ascii=True)


def verify_official_company_source(company_name: str, url: str, evidence_text: str = "") -> tuple[str, bool, str]:
    domain = base_domain(url)
    if not is_acceptable_official_url(url):
        return domain, False, "rejected: third-party or unsupported URL"
    lower_url = url.lower()
    lower_text = (evidence_text or "").lower()
    path = urllib.parse.urlparse(url).path.lower()
    official_path_markers = [
        "career",
        "careers",
        "campus",
        "job",
        "jobs",
        "join",
        "position",
        "recruit",
        "hr",
        "zhaopin",
    ]
    has_hiring_path = any(marker in lower_url or marker in path for marker in official_path_markers)
    compact_company = re.sub(r"[\s（）()股份有限公司科技集团有限责任公司]+", "", company_name.lower())
    company_tokens = [token for token in re.split(r"[\s/|,，、（）()]+", company_name.lower()) if len(token) >= 2]
    has_company_signal = bool(compact_company and compact_company in lower_text) or any(
        token in lower_text for token in company_tokens[:4]
    )
    if has_hiring_path and (has_company_signal or domain.replace(".", "") in lower_url.replace(".", "")):
        return domain, True, "verified: official-looking hiring path and company/domain signal"
    if has_hiring_path:
        return domain, True, "verified: official-looking hiring path; company signal weak"
    return domain, False, "rejected: URL is not clearly an official hiring page"
