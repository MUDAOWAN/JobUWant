from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from jobuwant.boss_pipeline import (
    DEFAULT_COLLECT_OUTPUT,
    DEFAULT_REPORT_INPUT,
    DEFAULT_REPORT_OUTPUT,
    DEFAULT_SOURCE_TYPE,
    build_and_store_report_input,
    collect_command,
    extract_next_batch,
    get_pipeline_stats,
    import_collection,
    load_collection_preview,
    score_source,
    write_final_report,
)
from jobuwant.config import DEFAULT_QUERY, FirstRunBudget, OpenAISettings
from jobuwant.db import connect, initialize_database
from jobuwant.harness import JobUWantHarness
from jobuwant.reports import render_html_report
from jobuwant.search import OpenAIWebSearchProvider, SampleSearchProvider


st.set_page_config(page_title="JobUWant", layout="wide")


def _build_openai_settings() -> OpenAISettings:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    base_url = st.secrets.get("OPENAI_BASE_URL", "")
    model = st.secrets.get("OPENAI_MODEL", "gpt-5.5")
    if not api_key:
        st.error("\u8bf7\u5148\u5728 .streamlit/secrets.toml \u91cc\u8bbe\u7f6e OPENAI_API_KEY\u3002")
        st.stop()
    return OpenAISettings(
        api_key=api_key,
        base_url=base_url or None,
        model=model,
    )


def _build_search_provider(provider_name: str):
    if provider_name == "openai_web_search":
        settings = _build_openai_settings()
        return OpenAIWebSearchProvider(settings=settings), settings
    return SampleSearchProvider(), None



def render_boss_pipeline_panel(conn) -> None:
    st.subheader("BOSS 实习岗位分阶段分析")
    st.caption("采集脚本仍在命令行执行；这里负责查看采集结果、导入、评分、分批结构化和生成报告。")

    source_type = st.text_input("source_type", DEFAULT_SOURCE_TYPE, key="boss-source-type")
    collect_output = Path(st.text_input("采集 JSON", str(DEFAULT_COLLECT_OUTPUT), key="boss-collect-output"))
    report_input_path = Path(st.text_input("报告输入 JSON", str(DEFAULT_REPORT_INPUT), key="boss-report-input"))
    report_output_path = Path(st.text_input("最终报告 JSON", str(DEFAULT_REPORT_OUTPUT), key="boss-report-output"))

    st.markdown("**采集命令**")
    col_a, col_b, col_c, col_d = st.columns(4)
    target_count = int(col_a.number_input("目标条数", min_value=1, max_value=100, value=40, key="boss-target-count"))
    page_size = int(col_b.number_input("每页数量", min_value=1, max_value=30, value=15, key="boss-page-size"))
    max_pages = int(col_c.number_input("最多页数", min_value=1, max_value=10, value=3, key="boss-max-pages"))
    detail_limit = int(col_d.number_input("详情上限", min_value=1, max_value=100, value=40, key="boss-detail-limit"))
    st.code(
        collect_command(
            output_path=collect_output,
            source_type=source_type,
            target_count=target_count,
            page_size=page_size,
            max_pages=max_pages,
            detail_limit=detail_limit,
        ),
        language="bash",
    )

    preview = load_collection_preview(collect_output)
    if preview.get("exists"):
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("采集岗位", int(preview.get("job_count") or 0))
        p2.metric("最短正文", int(preview.get("desc_len_min") or 0))
        p3.metric("过短正文", int(preview.get("desc_len_under_120") or 0))
        p4.metric("停止原因", str(preview.get("stop_reason") or "completed"))
    else:
        st.info("还没有找到采集 JSON。先在命令行运行上面的采集命令。")

    stats = get_pipeline_stats(conn, source_type)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("已入库岗位", stats.job_count)
    s2.metric("最新评分 run", stats.latest_run_id or 0)
    s3.metric("已结构化", stats.latest_run_extraction_count)
    s4.metric("最新报告", stats.latest_report_id or 0)
    if stats.latest_run_status_counts:
        st.json(stats.latest_run_status_counts)

    st.markdown("**阶段操作**")
    op1, op2, op3, op4 = st.columns(4)
    if op1.button("导入采集 JSON", key="boss-import-json"):
        try:
            st.json(import_collection(conn, collect_output))
        except Exception as exc:
            st.error(f"导入失败：{exc}")

    if op2.button("本地匹配评分", key="boss-score"):
        try:
            summary = score_source(
                conn=conn,
                source_type=source_type,
                city="杭州",
                keyword="Agent工程师",
                keywords=["Agent", "AI", "大模型", "智能体", "Python"],
                expected_intent="intern",
                allow_intern=True,
            )
            st.json(summary)
        except Exception as exc:
            st.error(f"评分失败：{exc}")

    run_id = int(st.number_input("用于后续分析的 search_run_id", min_value=0, value=stats.latest_run_id or 0, key="boss-run-id"))
    batch_size = int(st.number_input("每次结构化岗位数", min_value=1, max_value=20, value=10, key="boss-extract-batch"))
    if op3.button("结构化下一批", key="boss-extract-next"):
        if run_id <= 0:
            st.warning("请先完成本地匹配评分。")
        else:
            try:
                settings = _build_openai_settings()
                st.json(
                    extract_next_batch(
                        conn=conn,
                        search_run_id=run_id,
                        settings=settings,
                        match_statuses=["strong_match", "review"],
                        batch_size=batch_size,
                        budget_tier="1-10" if batch_size <= 10 else "11-30",
                        request_timeout=240.0,
                        max_output_tokens=6000,
                    )
                )
            except Exception as exc:
                st.error(f"结构化失败：{exc}")

    if op4.button("生成报告输入", key="boss-build-report-input"):
        if run_id <= 0:
            st.warning("请先选择 search_run_id。")
        else:
            try:
                st.json(
                    build_and_store_report_input(
                        conn=conn,
                        search_run_id=run_id,
                        source_type=source_type,
                        match_statuses=["strong_match", "review"],
                        output_path=report_input_path,
                    )
                )
            except Exception as exc:
                st.error(f"报告输入生成失败：{exc}")

    if st.button("生成最终报告", key="boss-write-final-report"):
        try:
            settings = _build_openai_settings()
            st.json(
                write_final_report(
                    conn=conn,
                    settings=settings,
                    input_path=report_input_path,
                    output_path=report_output_path,
                    request_timeout=300.0,
                    max_output_tokens=5000,
                )
            )
        except Exception as exc:
            st.error(f"最终报告生成失败：{exc}")
def main() -> None:
    st.title("JobUWant")

    st.sidebar.header("\u67e5\u8be2\u6761\u4ef6")
    role = st.sidebar.text_input("\u5c97\u4f4d\u65b9\u5411", DEFAULT_QUERY.role)
    city = st.sidebar.text_input("\u57ce\u5e02", DEFAULT_QUERY.city)
    hiring_stage = st.sidebar.text_input("\u62db\u8058\u9636\u6bb5", DEFAULT_QUERY.hiring_stage)
    candidate_status = st.sidebar.text_input(
        "\u5019\u9009\u4eba\u72b6\u6001", DEFAULT_QUERY.candidate_status
    )
    provider_name = st.sidebar.radio(
        "\u6570\u636e\u6765\u6e90",
        options=["sample", "openai_web_search"],
        format_func=lambda value: {
            "sample": "\u672c\u5730\u6837\u4f8b\u6570\u636e",
            "openai_web_search": "OpenAI \u771f\u5b9e\u641c\u7d22",
        }[value],
    )

    st.sidebar.header("\u9996\u6b21\u8fd0\u884c\u9884\u7b97")
    budget = FirstRunBudget(
        max_candidate_sources=st.sidebar.number_input(
            "\u5019\u9009\u6765\u6e90\u6570\u91cf", min_value=1, max_value=50, value=20
        ),
        max_changed_records=st.sidebar.number_input(
            "\u65b0\u589e\u6216\u53d8\u5316\u8bb0\u5f55\u6570", min_value=1, max_value=50, value=10
        ),
        max_model_calls=st.sidebar.number_input(
            "\u6a21\u578b\u8c03\u7528\u6b21\u6570", min_value=0, max_value=50, value=10
        ),
        max_estimated_cny=st.sidebar.number_input(
            "\u9884\u4f30\u8d39\u7528\uff08\u5143\uff09", min_value=0.0, max_value=100.0, value=5.0, step=0.5
        ),
    )

    st.sidebar.header("Phase 2")
    phase2_company_limit = st.sidebar.number_input(
        "\u81ea\u52a8\u5904\u7406\u516c\u53f8\u6570", min_value=1, max_value=2, value=2
    )
    phase2_leads_per_company = st.sidebar.number_input(
        "\u6bcf\u5bb6\u5019\u9009\u5c97\u4f4d\u6570", min_value=1, max_value=3, value=3
    )

    conn = connect()
    initialize_database(conn)
    search_provider, openai_settings = _build_search_provider(provider_name)
    harness = JobUWantHarness(
        conn=conn,
        budget=budget,
        search_provider=search_provider,
        openai_settings=openai_settings,
    )

    query = DEFAULT_QUERY.with_updates(
        role=role,
        city=city,
        hiring_stage=hiring_stage,
        candidate_status=candidate_status,
    )

    with st.expander("BOSS 实习岗位分阶段分析", expanded=False):
        render_boss_pipeline_panel(conn)
    st.divider()

    st.subheader("\u5019\u9009\u516c\u53f8\u53d1\u73b0")
    st.caption(
        "\u672c\u5730\u6837\u4f8b\u6a21\u5f0f\u4e0d\u8c03\u7528\u5916\u90e8\u670d\u52a1\uff1bOpenAI \u6a21\u5f0f\u4f1a\u8c03\u7528\u771f\u5b9e\u641c\u7d22\u548c\u6a21\u578b API\u3002"
    )

    if st.button("\u53d1\u73b0\u5019\u9009\u516c\u53f8"):
        try:
            result = harness.discover_candidates(query)
        except Exception as exc:
            st.error(f"\u5019\u9009\u516c\u53f8\u53d1\u73b0\u5931\u8d25\uff1a{exc}")
            st.stop()
        st.session_state["last_result"] = result
        st.session_state.pop("phase2_result", None)

    result = st.session_state.get("last_result")
    if not result:
        st.info("\u70b9\u51fb\u201c\u53d1\u73b0\u5019\u9009\u516c\u53f8\u201d\u9884\u89c8\u7b2c\u4e00\u7248 MVP \u6d41\u7a0b\u3002")
        saved_details = harness.saved_job_details()
        if saved_details:
            st.subheader("\u5df2\u4fdd\u5b58\u5c97\u4f4d\u8be6\u60c5")
            st.dataframe(saved_details, use_container_width=True)
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("\u5019\u9009\u6765\u6e90\u6570\u91cf", result.usage.candidate_sources)
    col2.metric("\u6a21\u578b\u8c03\u7528\u6b21\u6570", result.usage.model_calls)
    col3.metric("\u9884\u4f30\u8d39\u7528\uff08\u5143\uff09", f"{result.usage.estimated_cny:.2f}")
    col4.metric("\u603b\u8017\u65f6", f"{result.elapsed_seconds:.1f}s")

    st.subheader("\u5019\u9009\u516c\u53f8")
    st.dataframe(
        [candidate.to_display_dict() for candidate in result.candidates],
        use_container_width=True,
    )

    st.subheader("Phase 2 \u5c97\u4f4d\u8be6\u60c5\u81ea\u52a8\u91c7\u96c6")
    st.caption(
        "\u5f53\u524d\u9650\u5236\u6bcf\u6b21\u81ea\u52a8\u5904\u7406 1-2 \u5bb6\u516c\u53f8\uff1a\u5148\u627e\u5019\u9009\u5c97\u4f4d\u7ebf\u7d22\uff0c\u518d\u8bfb\u53d6\u516c\u5f00\u9875\u9762\u539f\u6587\u5e76\u505a\u8d28\u91cf\u5224\u65ad\uff0c\u53ea\u6709\u50cf\u5c97\u4f4d\u8be6\u60c5\u7684\u6b63\u6587\u624d\u8fdb\u5165\u7ed3\u6784\u5316\u89e3\u6790\u548c SQLite \u4fdd\u5b58\u3002"
    )
    if st.button("\u81ea\u52a8\u91c7\u96c6\u5c97\u4f4d\u8be6\u60c5"):
        try:
            phase2_result = harness.collect_job_details(
                companies=result.candidates,
                query=query,
                company_limit=int(phase2_company_limit),
                lead_limit_per_company=int(phase2_leads_per_company),
            )
        except Exception as exc:
            st.error(f"Phase 2 \u5c97\u4f4d\u8be6\u60c5\u91c7\u96c6\u5931\u8d25\uff1a{exc}")
            st.stop()
        st.session_state["phase2_result"] = phase2_result

    phase2_result = st.session_state.get("phase2_result")
    if phase2_result:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("\u5c97\u4f4d\u7ebf\u7d22", len(phase2_result.leads))
        c2.metric("\u5df2\u89e3\u6790\u8be6\u60c5", len(phase2_result.details))
        c3.metric("Phase 2 \u9884\u4f30\u8d39\u7528\uff08\u5143\uff09", f"{phase2_result.usage.estimated_cny:.2f}")
        c4.metric("Phase 2 \u603b\u8017\u65f6", f"{phase2_result.elapsed_seconds:.1f}s")

        if phase2_result.leads:
            st.markdown("**\u5019\u9009\u5c97\u4f4d\u7ebf\u7d22**")
            st.dataframe(
                [lead.to_display_dict() for lead in phase2_result.leads],
                use_container_width=True,
            )

        if phase2_result.details:
            st.markdown("**\u7ed3\u6784\u5316\u5c97\u4f4d\u8be6\u60c5**")
            st.dataframe(
                [detail.to_display_dict() for detail in phase2_result.details],
                use_container_width=True,
            )
            for detail in phase2_result.details:
                label = f"{detail.company_name} - {detail.job_title} - \u539f\u6587"
                with st.expander(label):
                    if detail.error_message:
                        st.warning(detail.error_message)
                    st.text_area(
                        "\u539f\u59cb\u5c97\u4f4d\u63cf\u8ff0",
                        value=detail.raw_job_text,
                        height=260,
                        key=f"raw-{detail.content_hash}",
                    )

    confirmed = st.button("\u786e\u8ba4\u5019\u9009\u516c\u53f8\u5e76\u751f\u6210\u9884\u89c8\u62a5\u544a")
    if confirmed:
        report_html = render_html_report(result)
        st.download_button(
            "\u4e0b\u8f7d HTML \u62a5\u544a",
            data=report_html,
            file_name="jobuwant_report.html",
            mime="text/html",
        )
        components.html(report_html, height=600, scrolling=True)

    saved_details = harness.saved_job_details()
    if saved_details:
        st.subheader("\u5df2\u4fdd\u5b58\u5c97\u4f4d\u8be6\u60c5")
        st.dataframe(saved_details, use_container_width=True)


if __name__ == "__main__":
    main()





