from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sqlite3
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from jobuwant.ai_job_insights import extract_json_text, usage_from_response
from jobuwant.config import OpenAISettings
from jobuwant.db import DB_PATH, connect, initialize_database


DEFAULT_SECRETS_PATH = Path(".streamlit") / "secrets.toml"
DEFAULT_REPORT_TYPE = "job_market_v1"
EMPTY_SUMMARIES = {"未生成", "n/a", "none", "null", "无", ""}


class EvidenceRef(BaseModel):
    topic: str = ""
    job_id: int
    quote: str = ""


class ReportSection(BaseModel):
    title: str
    summary: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_section(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"title": "分析结论", "summary": value}
        if isinstance(value, dict) and ("title" not in value or "summary" not in value):
            title = str(value.get("title") or value.get("name") or "分析结论")
            parts = []
            for key, item in value.items():
                if key in {"title", "name", "evidence_refs"}:
                    continue
                if isinstance(item, list):
                    parts.extend(str(part) for part in item)
                elif item:
                    parts.append(str(item))
            return {**value, "title": title, "summary": "；".join(parts) or title}
        return value

    @field_validator("title", "summary")
    @classmethod
    def text_required(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("section title and summary are required")
        return cleaned

    @field_validator("summary")
    @classmethod
    def summary_must_be_generated(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if cleaned.lower() in EMPTY_SUMMARIES:
            raise ValueError("section summary must be generated")
        return cleaned



class PriorityItem(BaseModel):
    name: str
    priority: str = Field(description="high|medium|low")
    reason: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_priority(cls, value: Any) -> Any:
        if isinstance(value, str):
            name = value.split("：", 1)[0].split(":", 1)[0][:40] or value[:40]
            return {"name": name, "priority": "medium", "reason": value}
        if isinstance(value, dict):
            name = value.get("name") or value.get("skill") or value.get("ability") or value.get("title")
            reason = value.get("reason") or value.get("summary") or value.get("description")
            if not reason:
                reason = "；".join(str(v) for k, v in value.items() if k not in {"name", "skill", "ability", "title", "priority", "evidence_refs"})
            return {**value, "name": str(name or reason or "未命名项")[:80], "priority": value.get("priority") or "medium", "reason": str(reason or name or "") }
        return value


class LearningStep(BaseModel):
    stage: str
    focus: list[str] = Field(default_factory=list)
    suggestion: str

    @model_validator(mode="before")
    @classmethod
    def coerce_step(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"stage": value[:40], "focus": [], "suggestion": value}
        if isinstance(value, dict):
            stage = value.get("stage") or value.get("name") or value.get("title") or "阶段"
            focus = value.get("focus") or value.get("skills") or []
            if isinstance(focus, str):
                focus = [focus]
            suggestion = value.get("suggestion") or value.get("description") or value.get("details") or value.get("summary")
            if not suggestion:
                suggestion = "；".join(str(v) for k, v in value.items() if k not in {"stage", "name", "title", "focus", "skills"})
            return {**value, "stage": str(stage), "focus": focus, "suggestion": str(suggestion or stage)}
        return value


class ProjectSuggestion(BaseModel):
    project_name: str
    stack: list[str] = Field(default_factory=list)
    data_or_input: str
    deliverable: str
    resume_value: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def coerce_project(cls, value: Any) -> Any:
        if isinstance(value, str):
            parsed = parse_project_suggestion_text(value)
            return {
                'project_name': parsed['project_name'],
                'stack': parsed['stack'],
                'data_or_input': parsed['data_or_input'],
                'deliverable': parsed['deliverable'],
                'resume_value': parsed['resume_value'],
            }
        if isinstance(value, dict):
            project_name = (
                value.get('project_name')
                or value.get('name')
                or value.get('title')
                or value.get('stage')
                or '作品项目'
            )
            stack = value.get('stack') or value.get('tech_stack') or value.get('focus') or value.get('skills') or []
            if isinstance(stack, str):
                stack = split_text_list(stack)
            suggestion = value.get('suggestion') or value.get('description') or value.get('summary') or ''
            parsed = parse_project_suggestion_text(str(suggestion)) if suggestion else {}
            return {
                **value,
                'project_name': str(project_name).strip(),
                'stack': stack or parsed.get('stack') or [],
                'data_or_input': str(value.get('data_or_input') or value.get('data_input') or value.get('data') or value.get('input') or parsed.get('data_or_input') or suggestion).strip(),
                'deliverable': str(value.get('deliverable') or value.get('output') or value.get('artifact') or parsed.get('deliverable') or suggestion).strip(),
                'resume_value': str(value.get('resume_value') or value.get('value') or value.get('reason') or parsed.get('resume_value') or suggestion).strip(),
            }
        return value

    @field_validator('project_name', 'data_or_input', 'deliverable', 'resume_value')
    @classmethod
    def project_text_required(cls, value: str) -> str:
        cleaned = (value or '').strip()
        if not cleaned:
            raise ValueError('project suggestion fields are required')
        return cleaned

    @field_validator('stack')
    @classmethod
    def clean_stack(cls, value: list[str]) -> list[str]:
        return [str(item).strip() for item in value if str(item).strip()]


class SkillLayers(BaseModel):
    core: list[PriorityItem] = Field(default_factory=list)
    common: list[PriorityItem] = Field(default_factory=list)
    nice_to_have: list[PriorityItem] = Field(default_factory=list)


class AIJobReport(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def coerce_report(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        output = dict(value)
        for key in ("core_skills", "ability_requirements", "technical_top15_interpretation"):
            item = output.get(key)
            if isinstance(item, dict):
                flattened = []
                for child in item.values():
                    if isinstance(child, list):
                        flattened.extend(child)
                    elif child:
                        flattened.append(child)
                output[key] = flattened
        for list_key in ("caveats", "job_search_advice"):
            if isinstance(output.get(list_key), str):
                output[list_key] = [output[list_key]]
        projects = output.get('project_suggestions')
        if isinstance(projects, dict):
            output['project_suggestions'] = list(projects.values())
        elif isinstance(projects, str):
            output['project_suggestions'] = [projects]
        if isinstance(output.get("resume_keywords"), str):
            output["resume_keywords"] = [part.strip() for part in output["resume_keywords"].replace("\uff0c", ",").split(",") if part.strip()]
        return output

    report_title: str
    audience_summary: str
    role_profile: ReportSection
    technical_top15_interpretation: list[PriorityItem] = Field(default_factory=list)
    skill_layers: SkillLayers = Field(default_factory=SkillLayers)
    core_skills: list[PriorityItem] = Field(default_factory=list)
    ability_requirements: list[PriorityItem] = Field(default_factory=list)
    salary_and_threshold: ReportSection
    experience_and_education: ReportSection
    graduate_friendliness: ReportSection
    learning_route: list[LearningStep] = Field(default_factory=list)
    project_suggestions: list[ProjectSuggestion] = Field(default_factory=list)
    resume_keywords: list[str] = Field(default_factory=list)
    job_search_advice: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


def load_report_input(conn: sqlite3.Connection, report_input_id: int, input_path: Path | None) -> tuple[int | None, dict[str, Any]]:
    initialize_database(conn)
    if input_path is not None:
        return None, json.loads(input_path.read_text(encoding="utf-8"))
    row = conn.execute(
        "SELECT id, input_json FROM job_report_inputs WHERE id = ?",
        (report_input_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"job_report_inputs id={report_input_id} not found")
    return int(row["id"]), json.loads(row["input_json"])


def write_report_with_openai(
    report_input: dict[str, Any],
    settings: OpenAISettings,
    request_timeout: float,
    max_output_tokens: int,
) -> tuple[AIJobReport, dict[str, int | float], str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI report writing requires the `openai` package.") from exc

    client_kwargs: dict[str, Any] = {"api_key": settings.api_key}
    if settings.base_url:
        client_kwargs["base_url"] = settings.base_url
    if request_timeout > 0:
        client_kwargs["timeout"] = request_timeout
    client = OpenAI(**client_kwargs)
    prompt = build_prompt(report_input)
    create_kwargs: dict[str, Any] = {"model": settings.model, "input": prompt}
    if max_output_tokens > 0:
        create_kwargs["max_output_tokens"] = max_output_tokens
    response = client.responses.create(**create_kwargs)
    output_json = extract_json_text(getattr(response, "output_text", "") or "")
    try:
        report_payload = normalize_report_payload(json.loads(output_json), report_input=report_input)
        report = AIJobReport.model_validate(report_payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"AI job report JSON failed validation: {exc}") from exc
    validate_report_evidence_refs(report=report, report_input=report_input)
    return report, usage_from_response(response, settings), output_json


def normalize_report_payload(payload: Any, report_input: dict[str, Any]) -> Any:
    if not isinstance(payload, dict):
        return payload
    output = dict(payload)
    aliases = {
        'new_graduate_friendliness': 'graduate_friendliness',
        'intern_friendliness': 'graduate_friendliness',
        'experience_education': 'experience_and_education',
        'experience_and_degree': 'experience_and_education',
        'salary_threshold': 'salary_and_threshold',
    }
    for source_key, target_key in aliases.items():
        if target_key not in output and source_key in output:
            output[target_key] = output[source_key]
    builders = {
        'salary_and_threshold': build_salary_section,
        'experience_and_education': build_experience_and_education_section,
        'graduate_friendliness': build_graduate_friendliness_section,
    }
    for key, builder in builders.items():
        if section_missing(output.get(key)):
            output[key] = builder(report_input)
    section_titles = {
        'salary_and_threshold': '薪资与门槛',
        'experience_and_education': '经验与学历门槛',
        'graduate_friendliness': '实习与应届友好度',
    }
    for key, title in section_titles.items():
        section = output.get(key)
        if isinstance(section, dict) and not str(section.get('title') or '').strip():
            section['title'] = title
    if not output.get('project_suggestions'):
        output['project_suggestions'] = build_fallback_project_suggestions(report_input)
    return output


def section_missing(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in EMPTY_SUMMARIES
    if not isinstance(value, dict):
        return True
    summary = str(value.get('summary') or '').strip()
    return summary.lower() in EMPTY_SUMMARIES


def build_salary_section(report_input: dict[str, Any]) -> dict[str, Any]:
    salary = report_input.get('salary_summary') or {}
    daily = salary.get('daily_cny') or {}
    raw_count = int(salary.get('raw_salary_count') or 0)
    parsed_count = int(salary.get('parsed_count') or 0)
    if int(daily.get('count') or 0):
        median = daily.get('median_mid')
        average_low = daily.get('average_low')
        average_high = daily.get('average_high')
        summary = f'样本中{raw_count}条有薪资字段，{parsed_count}条可解析为日薪；日薪中位中点为{median}元/天，平均下限{average_low}元/天，平均上限{average_high}元/天。薪资判断应结合实习周期、到岗天数、项目复杂度和经验/学历门槛一起看。'
    else:
        summary = '报告输入中缺少可稳定解析的薪资区间，薪资判断需要回到具体岗位逐条确认。'
    return {'title': '薪资与门槛', 'summary': summary, 'evidence_refs': first_evidence_refs(report_input, ['evidence_pack'], 2)}


def build_experience_and_education_section(report_input: dict[str, Any]) -> dict[str, Any]:
    experience = report_input.get('experience_summary') or {}
    education = report_input.get('education_summary') or {}
    exp_dist = format_distribution(experience.get('level_distribution') or [], 5) or '未形成单一集中项'
    edu_dist = format_distribution(education.get('level_distribution') or [], 5) or '未形成单一集中项'
    exp_common = format_text_items(experience.get('common_summaries') or [], 3) or '报告输入未给出高频表述'
    edu_common = format_text_items(education.get('common_summaries') or [], 3) or '报告输入未给出高频表述'
    summary = f'经验要求分布集中在：{exp_dist}；常见经验表述包括：{exp_common}。学历要求分布集中在：{edu_dist}；常见学历表述包括：{edu_common}。整体看，这批岗位更看重可展示的AI应用、Agent或RAG项目闭环，而不是只看年限。'
    return {'title': '经验与学历门槛', 'summary': summary, 'evidence_refs': first_evidence_refs(report_input, ['experience_summary', 'education_summary', 'evidence_pack'], 2)}


def build_graduate_friendliness_section(report_input: dict[str, Any]) -> dict[str, Any]:
    sample = report_input.get('sample') or {}
    total_jobs = int(sample.get('total_jobs') or 0)
    friendliness = format_distribution(sample.get('graduate_friendliness_distribution') or [], 4) or '未统计'
    role_intents = format_distribution(sample.get('role_intent_distribution') or [], 4) or '未统计'
    summary = f'{total_jobs}条样本的实习/应届友好度分布为：{friendliness}；岗位意图分布为：{role_intents}。这说明样本整体对在校或早期候选人较友好，但低友好度和偏工程正式岗的样本仍需要在投递前单独确认到岗周期、作品要求和面试深度。'
    return {'title': '实习与应届友好度', 'summary': summary, 'evidence_refs': first_evidence_refs(report_input, ['evidence_pack'], 2)}


def build_fallback_project_suggestions(report_input: dict[str, Any]) -> list[dict[str, Any]]:
    top_terms = report_input.get('technical_terms_top') or []
    term_names = [str(item.get('name') or '').strip() for item in top_terms if str(item.get('name') or '').strip()]
    total_jobs = int((report_input.get('sample') or {}).get('total_jobs') or 0)
    term_counts = {str(item.get('name') or '').strip(): int(item.get('count') or 0) for item in top_terms}

    def choose_stack(*wanted: str) -> list[str]:
        chosen = [term for term in wanted if term in term_names]
        for term in term_names:
            if len(chosen) >= 5:
                break
            if term not in chosen:
                chosen.append(term)
        return chosen[:5]

    def reason_for(items: list[str]) -> str:
        counts = [f'{name} {term_counts[name]}/{total_jobs}' for name in items if term_counts.get(name)]
        return '、'.join(counts) if counts else '高频技术项'

    rag_stack = choose_stack('Python', 'RAG', 'LangChain', 'LLM', 'Git')
    agent_stack = choose_stack('Python', '智能体', 'Prompt工程', 'LLM', 'API')
    full_stack = choose_stack('Python', 'JavaScript', 'MySQL', 'Redis', 'Git')
    return [
        {'project_name': '企业知识库RAG智能体', 'stack': rag_stack, 'data_or_input': '公开文档、课程笔记或自整理FAQ文档。', 'deliverable': '可运行问答Demo、README、检索与回答效果样例、Git提交记录。', 'resume_value': f'用于证明能把资料、检索、提示词和回答质量做成闭环，对应{reason_for(rag_stack)}。', 'evidence_refs': refs_for_topics(report_input, ['RAG', 'LangChain', 'LLM'], 2)},
        {'project_name': '业务流程Agent原型', 'stack': agent_stack, 'data_or_input': '任务清单、业务流程文本、工具调用接口样例。', 'deliverable': '能分解任务、调用工具、记录执行过程的Agent原型和演示说明。', 'resume_value': f'用于证明Agent工程落地能力，对应{reason_for(agent_stack)}。', 'evidence_refs': refs_for_topics(report_input, ['智能体', 'Prompt工程', 'LLM'], 2)},
        {'project_name': 'AI应用全栈演示', 'stack': full_stack, 'data_or_input': '用户需求表、对话记录样例、基础业务数据表。', 'deliverable': '包含前端交互、后端接口、数据存储和AI调用记录的完整Demo。', 'resume_value': f'用于展示从原型到可演示产品的工程能力，对应{reason_for(full_stack)}。', 'evidence_refs': refs_for_topics(report_input, ['Python', 'JavaScript', 'MySQL', 'Git'], 2)},
    ]


def format_distribution(items: list[Any], limit: int) -> str:
    parts = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if name:
            count = item.get('count')
            ratio = item.get('ratio')
            parts.append(f'{name} {count}条/{ratio}')
    return '，'.join(parts)


def format_text_items(items: list[Any], limit: int) -> str:
    return '；'.join(str(item).strip() for item in items[:limit] if str(item).strip())


def parse_project_suggestion_text(value: str) -> dict[str, Any]:
    cleaned = re.sub(r'[；;]?\s*\[\{.*$', '', value.strip())
    parts = [part.strip() for part in re.split(r'[；;]', cleaned) if part.strip()]
    stack: list[str] = []
    if parts and parts[0].startswith('['):
        try:
            parsed = ast.literal_eval(parts[0])
            if isinstance(parsed, list):
                stack = [str(item).strip() for item in parsed if str(item).strip()]
                parts = parts[1:]
        except (SyntaxError, ValueError):
            stack = split_text_list(parts[0])
            parts = parts[1:]
    summary = '；'.join(parts) or cleaned
    return {'project_name': parts[0][:40] if parts else '作品项目', 'stack': stack, 'data_or_input': parts[0] if len(parts) > 0 else summary, 'deliverable': parts[1] if len(parts) > 1 else summary, 'resume_value': parts[2] if len(parts) > 2 else summary}


def split_text_list(value: str) -> list[str]:
    return [part.strip() for part in re.split(r'[,，、/；;\s]+', value) if part.strip()]


def first_evidence_refs(report_input: dict[str, Any], preferred_sections: list[str], limit: int) -> list[dict[str, Any]]:
    items = collect_allowed_evidence_items(report_input)
    preferred = [item for item in items if item.get('_section') in preferred_sections]
    return evidence_items_to_refs((preferred or items)[:limit])


def refs_for_topics(report_input: dict[str, Any], topics: list[str], limit: int) -> list[dict[str, Any]]:
    items = collect_allowed_evidence_items(report_input)
    lowered_topics = [topic.lower() for topic in topics]
    matched = []
    for item in items:
        source = ' '.join(str(item.get(key) or '') for key in ('topic', 'name', 'field', 'source', 'quote', '_section')).lower()
        if any(topic in source for topic in lowered_topics):
            matched.append(item)
    return evidence_items_to_refs((matched or items)[:limit])


def evidence_items_to_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = []
    for item in items:
        job_id = int(item.get('job_id') or 0)
        quote = secret_text(item, 'quote')
        if job_id and quote:
            refs.append({'topic': secret_text(item, 'topic') or secret_text(item, 'field') or secret_text(item, 'source') or '样本证据', 'job_id': job_id, 'quote': quote})
    return refs


def build_prompt(report_input: dict[str, Any]) -> str:
    compact_input = json.dumps(report_input, ensure_ascii=False, separators=(",", ":"))
    instructions = [
        'Return compact JSON only. No Markdown.',
        'Write a practical job-market analysis report in Simplified Chinese for a Chinese job seeker.',
        'Use only report_input. Do not add numbers, companies, salaries, skills, or evidence absent from report_input.',
        'When describing a trend, cite the exact count/ratio from report_input, such as Python 3/3 or SLAM 5/5.',
        'Evidence refs must copy job_id and quote from report_input evidence objects only.',
        'Do not leave evidence_refs empty for role_profile, technical_top15_interpretation items, skill_layers items, salary_and_threshold, experience_and_education, graduate_friendliness, or project_suggestions.',
        'Each evidence_refs item shape is {topic:string, job_id:number, quote:string}; quote must be copied exactly from a report_input object that has both job_id and quote.',
        'Allowed evidence sources include evidence_pack, technical_terms_top[].evidence, experience_summary.evidence, education_summary.evidence, and frequency evidence arrays. Do not use representative_jobs or free text as evidence_refs.',
        'Use these exact top-level keys, no aliases: report_title, audience_summary, role_profile, technical_top15_interpretation, skill_layers, core_skills, ability_requirements, salary_and_threshold, experience_and_education, graduate_friendliness, learning_route, project_suggestions, resume_keywords, job_search_advice, caveats.',
        'role_profile is the job portrait. technical_top15_interpretation explains technical_terms_top in rank order, up to 15 items.',
        'For PriorityItem.name, use only the skill or topic name, for example Python or SLAM. Put rank, count, ratio, and explanation in reason only.',
        'skill_layers is {core:[...], common:[...], nice_to_have:[...]}; use technical_terms_layers to assign items.',
        'salary_and_threshold must use salary_summary plus experience_summary and education_summary.',
        'experience_and_education must summarize experience_summary and education_summary; never output 未生成.',
        'graduate_friendliness must summarize sample.graduate_friendliness_distribution and role_intent_distribution; never output 未生成.',
        'learning_route must give 3 stages tied to the core and common skills.',
        'project_suggestions must be an array of 2-3 objects, never strings. Each object keys: project_name, stack, data_or_input, deliverable, resume_value, evidence_refs.',
        'For project_suggestions, do not put arrays, dicts, or evidence_refs inside a text field. Keep stack as a string array and evidence_refs as its own array.',
        'resume_keywords must list searchable resume keywords that appear in report_input.',
        'job_search_advice must be specific to the query city, role, sample size, salary data, and preparation gap.',
        'caveats must describe sample size and evidence quality limits from report_input.',
        'Use concise Chinese. The user wants actionable guidance, not generic encouragement.',
        'Report input JSON:',
    ]
    return "\n".join(instructions) + "\n" + compact_input


def save_report(
    conn: sqlite3.Connection,
    report_input_id: int | None,
    report_input: dict[str, Any],
    report: AIJobReport,
    model_name: str,
    output_path: Path | None,
) -> int:
    query = report_input.get("query") or {}
    evidence = collect_evidence_refs(report.model_dump())
    cursor = conn.execute(
        """
        INSERT INTO job_reports (
            report_input_id,
            search_run_id,
            source_type,
            model_name,
            report_type,
            output_json,
            evidence_json,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')
        """,
        (
            report_input_id,
            query.get("search_run_id"),
            query.get("source_type") or "unknown",
            model_name,
            report_input.get("report_type") or DEFAULT_REPORT_TYPE,
            json.dumps(report.model_dump(), ensure_ascii=True),
            json.dumps(evidence, ensure_ascii=True),
        ),
    )
    conn.commit()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return int(cursor.lastrowid)


def collect_evidence_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "job_id" in value and "quote" in value:
            refs.append(value)
        for child in value.values():
            refs.extend(collect_evidence_refs(child))
    elif isinstance(value, list):
        for item in value:
            refs.extend(collect_evidence_refs(item))
    return refs


def validate_report_evidence_refs(report: AIJobReport, report_input: dict[str, Any]) -> None:
    allowed = collect_allowed_evidence_refs(report_input)
    refs = collect_evidence_refs(report.model_dump())
    if not refs:
        raise RuntimeError("AI job report missing evidence_refs")
    invalid = []
    for ref in refs:
        job_id = int(ref.get("job_id") or 0)
        quote = secret_text(ref, "quote")
        if (job_id, quote) not in allowed:
            invalid.append({"job_id": job_id, "quote": quote[:80]})
    if invalid:
        raise RuntimeError(f"AI job report has evidence_refs outside report_input: {invalid[:5]}")


def collect_allowed_evidence_refs(report_input: dict[str, Any]) -> set[tuple[int, str]]:
    refs: set[tuple[int, str]] = set()
    for item in collect_allowed_evidence_items(report_input):
        job_id = int(item.get('job_id') or 0)
        quote = secret_text(item, 'quote')
        if job_id and quote:
            refs.add((job_id, quote))
    return refs


def collect_allowed_evidence_items(report_input: dict[str, Any]) -> list[dict[str, Any]]:
    allowed_sections = (
        'evidence_pack',
        'technical_terms_top',
        'technical_stack_frequency',
        'tools_platforms_frequency',
        'business_domains_frequency',
        'ability_requirements_frequency',
        'experience_summary',
        'education_summary',
    )
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for section in allowed_sections:
        for item in collect_input_evidence(report_input.get(section)):
            job_id = int(item.get('job_id') or 0)
            quote = secret_text(item, 'quote')
            if not job_id or not quote:
                continue
            key = (section, job_id, quote)
            if key in seen:
                continue
            seen.add(key)
            enriched = dict(item)
            enriched['_section'] = section
            items.append(enriched)
    return items


def collect_input_evidence(value: Any) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "job_id" in value and "quote" in value:
            evidence.append(value)
        for child in value.values():
            evidence.extend(collect_input_evidence(child))
    elif isinstance(value, list):
        for item in value:
            evidence.extend(collect_input_evidence(item))
    return evidence


def store_usage(conn: sqlite3.Connection, model_name: str, usage: dict[str, int | float]) -> None:
    conn.execute(
        """
        INSERT INTO usage_events (
            stage,
            model_name,
            model_calls,
            input_tokens,
            output_tokens,
            estimated_cny
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "ai_report_writer",
            model_name,
            int(usage.get("model_calls", 0) or 0),
            int(usage.get("input_tokens", 0) or 0),
            int(usage.get("output_tokens", 0) or 0),
            float(usage.get("estimated_cny", 0.0) or 0.0),
        ),
    )
    conn.commit()


def load_settings(
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    secrets_path: Path,
    estimated_cny_per_call: float,
) -> OpenAISettings:
    secrets = load_secrets(secrets_path)
    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or secret_text(secrets, "OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY is required in the environment or .streamlit/secrets.toml")
    return OpenAISettings(
        api_key=resolved_api_key,
        base_url=base_url or os.getenv("OPENAI_BASE_URL") or secret_text(secrets, "OPENAI_BASE_URL") or None,
        model=model or os.getenv("OPENAI_MODEL") or secret_text(secrets, "OPENAI_MODEL") or "gpt-5.5",
        estimated_cny_per_call=estimated_cny_per_call,
    )


def load_secrets(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def secret_text(secrets: dict[str, Any], key: str) -> str:
    value = secrets.get(key)
    return "" if value is None else str(value).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a user-facing AI job report from a compact report input.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report-input-id", type=int, default=0)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--secrets", type=Path, default=DEFAULT_SECRETS_PATH)
    parser.add_argument("--estimated-cny-per-call", type=float, default=0.1)
    parser.add_argument("--request-timeout", type=float, default=180.0)
    parser.add_argument("--max-output-tokens", type=int, default=3500)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.report_input_id <= 0 and args.input is None:
        raise RuntimeError("--report-input-id or --input is required")
    conn = connect(args.db)
    report_input_id, report_input = load_report_input(conn, args.report_input_id, args.input)
    settings = load_settings(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        secrets_path=args.secrets,
        estimated_cny_per_call=args.estimated_cny_per_call,
    )
    report, usage, _raw_json = write_report_with_openai(
        report_input=report_input,
        settings=settings,
        request_timeout=args.request_timeout,
        max_output_tokens=args.max_output_tokens,
    )
    report_id = save_report(
        conn=conn,
        report_input_id=report_input_id,
        report_input=report_input,
        report=report,
        model_name=settings.model,
        output_path=args.output,
    )
    store_usage(conn, model_name=settings.model, usage=usage)
    print(
        json.dumps(
            {
                "report_id": report_id,
                "report_input_id": report_input_id,
                "title": report.report_title,
                "model_name": settings.model,
                "usage": usage,
                "output": str(args.output) if args.output else "",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
