"use client";

import { CheckCircle2, ChevronDown, ChevronRight, ExternalLink, ListChecks, Rows3, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { listJobs, saveSample, startStructuring, type AnalysisTask, type JobRow } from "@/lib/api";
import { formatCount, formatPercent } from "@/lib/format";
import { ErrorBanner } from "@/components/ui/shell";

type Filters = {
  matchStatus: string;
  roleIntent: string;
  companyKeyword: string;
  titleKeyword: string;
  selectedOnly: boolean;
};

type LoadState = {
  rows: JobRow[];
  total: number;
  loading: boolean;
  error: string;
};

const analysisCtaMotionStyles = `
  @keyframes jobuwant-analysis-cta-sweep {
    0% {
      transform: translateX(-160%) skewX(-18deg);
    }
    62% {
      transform: translateX(330%) skewX(-18deg);
    }
    100% {
      transform: translateX(330%) skewX(-18deg);
    }
  }

  .jobuwant-analysis-cta {
    isolation: isolate;
    border-color: transparent !important;
    background-image: linear-gradient(
      112deg,
      #f4fffb 0%,
      #e4fff7 24%,
      #cff7ec 46%,
      #afeedf 68%,
      #b7f1e5 100%
    ) !important;
  }

  .jobuwant-analysis-cta::before {
    content: "";
    position: absolute;
    inset: 1px;
    z-index: 1;
    border-radius: inherit;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0) 42%);
    pointer-events: none;
  }

  .jobuwant-analysis-cta::after {
    content: "";
    position: absolute;
    top: -28%;
    bottom: -28%;
    left: -48%;
    z-index: 2;
    width: 66%;
    border-radius: inherit;
    background: linear-gradient(
      102deg,
      rgba(255, 255, 255, 0) 0%,
      rgba(255, 255, 255, 0) 26%,
      rgba(255, 255, 255, 0.54) 41%,
      rgba(255, 255, 255, 1) 50%,
      rgba(255, 255, 255, 0.48) 59%,
      rgba(255, 255, 255, 0) 74%,
      rgba(255, 255, 255, 0) 100%
    );
    pointer-events: none;
    animation: jobuwant-analysis-cta-sweep 2.8s linear infinite;
  }

  .jobuwant-analysis-cta:hover::after,
  .jobuwant-analysis-cta:focus-visible::after {
    animation-duration: 2.8s;
  }

  .jobuwant-analysis-cta:hover .jobuwant-analysis-cta-icon,
  .jobuwant-analysis-cta:focus-visible .jobuwant-analysis-cta-icon {
    transform: translateX(4px);
  }

  .jobuwant-analysis-cta:disabled {
    border-color: #cbd5e1 !important;
    background: #eef2f7 !important;
    animation: none;
  }

  .jobuwant-analysis-cta:disabled::before,
  .jobuwant-analysis-cta:disabled::after {
    display: none;
  }

  .jobuwant-analysis-cta:disabled .jobuwant-analysis-cta-icon {
    transform: none;
  }
`;const defaultFilters: Filters = {
  matchStatus: "",
  roleIntent: "",
  companyKeyword: "",
  titleKeyword: "",
  selectedOnly: false,
};

export function SampleConfirmationPanel({ task, sampleConfirmed = false, onTaskChanged }: { task: AnalysisTask; sampleConfirmed?: boolean; onTaskChanged?: () => void }) {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [state, setState] = useState<LoadState>({ rows: [], total: 0, loading: true, error: "" });
  const [selectedById, setSelectedById] = useState<Record<number, boolean>>({});
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const router = useRouter();

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await listJobs(task.id, {
        match_status: filters.matchStatus,
        role_intent: filters.roleIntent,
        company_keyword: filters.companyKeyword.trim(),
        title_keyword: filters.titleKeyword.trim(),
        selected_only: filters.selectedOnly,
        limit: 200,
        offset: 0,
      });
      setState({ rows: payload.rows, total: payload.total, loading: false, error: "" });
      setSelectedById((current) => {
        const next = { ...current };
        payload.rows.forEach((row) => {
          if (next[row.job_id] === undefined) {
            next[row.job_id] = task.id.startsWith("task-") && !sampleConfirmed ? true : row.selected;
          }
        });
        return next;
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "岗位加载失败",
      }));
    }
  }, [filters, sampleConfirmed, task.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => {
    const visibleSelected = state.rows.filter((row) => selectedById[row.job_id]).length;
    const averageScore = state.rows.length ? state.rows.reduce((sum, row) => sum + row.match_score, 0) / state.rows.length : 0;
    return { visibleSelected, averageScore };
  }, [selectedById, state.rows]);

  function updateFilter<K extends keyof Filters>(key: K, value: Filters[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function toggleSelected(jobId: number) {
    setSelectedById((current) => ({ ...current, [jobId]: !current[jobId] }));
  }

  async function submitSample() {
    if (!task.id.startsWith("task-")) {
      return;
    }
    const selectedJobIds = Object.entries(selectedById).filter(([, selected]) => selected).map(([jobId]) => Number(jobId));
    const excludedJobIds = Object.entries(selectedById).filter(([, selected]) => !selected).map(([jobId]) => Number(jobId));
    setSaving(true);
    setSaveMessage("");
    setSaveError("");
    try {
      await saveSample(task.id, { selected_job_ids: selectedJobIds, excluded_job_ids: excludedJobIds, selection_note: "frontend live selection" });
      await startStructuring(task.id);
      window.sessionStorage.setItem(`jobuwant:auto-analysis:${task.id}`, "1");
      setSaveMessage("样本已确认，正在进入分析流程。");
      onTaskChanged?.();
      router.push(`/tasks/${task.id}/structure`);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "分析启动失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-5">
      <style>{analysisCtaMotionStyles}</style>
      <section className="rounded-[28px] border border-[#d8e1ec] bg-white/95 p-5 shadow-[0_22px_68px_rgba(14,23,38,0.12),inset_0_1px_0_rgba(255,255,255,0.98)]">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 lg:flex-1">
            <span className="inline-flex h-9 items-center gap-2 rounded-[16px] border border-[#bfe9dc] bg-[#f1fbf7] px-3 text-sm font-bold text-[#087a67]">
              <CheckCircle2 className="h-4 w-4" />
              查找完成
            </span>
            <h2 className="mt-3 text-3xl font-bold text-[#0b1220]">岗位查找已完成，在下方选择岗位后，即可进入岗位分析！</h2>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-[#607089]">默认保留当前任务的全部岗位；取消勾选不需要进入分析的岗位后，点击确定并开始分析。</p>
          </div>
          <div className="flex flex-wrap gap-2 lg:pt-[52px]">

            <button
              className="jobuwant-analysis-cta relative inline-flex h-[70px] w-[200px] cursor-pointer items-center justify-center gap-2.5 overflow-hidden rounded-full border border-transparent px-7 text-[17px] font-black text-[#064f47] shadow-[0_15px_24px_rgba(15,23,42,0.13),0_7px_16px_rgba(32,199,167,0.20),inset_0_1px_0_rgba(255,255,255,0.96),inset_0_-2px_5px_rgba(15,23,42,0.05)] transition duration-200 hover:-translate-y-1 hover:border-transparent hover:shadow-[0_20px_31px_rgba(15,23,42,0.15),0_9px_22px_rgba(32,199,167,0.28),inset_0_1px_0_rgba(255,255,255,0.98),inset_0_-2px_5px_rgba(15,23,42,0.04)] active:translate-y-0 active:shadow-[0_8px_14px_rgba(15,23,42,0.12),0_4px_10px_rgba(32,199,167,0.14),inset_0_1px_0_rgba(255,255,255,0.96)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-[#cbd5e1] disabled:bg-[#eef2f7] disabled:text-[#7a8799] disabled:shadow-none disabled:hover:translate-y-0"
              disabled={!task.id.startsWith("task-") || saving || summary.visibleSelected === 0}
              onClick={() => void submitSample()}
              type="button"
            >
              <span className="relative z-[3] flex items-center gap-2.5">
                <CheckCircle2 className="jobuwant-analysis-cta-icon h-5 w-5 text-[#087a67] transition-transform duration-200" />
                <span className="font-black">{saving ? "正在进入分析" : "确定并开始分析"}</span>
              </span>
            </button>
          </div>
        </div>

        <ErrorBanner message={saveError} />
        {saveMessage ? <div className="mt-4 rounded-[18px] border border-[#bde8d8] bg-[#f1fbf7] px-3 py-3 text-sm font-bold text-[#2f7d65]">{saveMessage}</div> : null}

        <div className="mt-5 grid gap-2 border-t border-[#edf2f7] pt-4 sm:grid-cols-2 xl:grid-cols-4">
          <SampleMetricPill icon={<ListChecks className="h-4 w-4" />} label="接口返回" value={formatCount(state.total)} />
          <SampleMetricPill icon={<Rows3 className="h-4 w-4" />} label="当前页岗位" value={formatCount(state.rows.length)} />
          <SampleMetricPill icon={<CheckCircle2 className="h-4 w-4" />} label="本地已选" value={formatCount(summary.visibleSelected)} helper={`${formatPercent(summary.visibleSelected, state.rows.length)} 当前页`} />
          <SampleMetricPill icon={<CheckCircle2 className="h-4 w-4" />} label="平均匹配分" value={summary.averageScore ? summary.averageScore.toFixed(1) : "-"} />
        </div>
      </section>

      <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
        <div className="grid gap-3 border-b border-[#edf2f7] bg-[#fbfdff] px-3 py-4 lg:grid-cols-[minmax(220px,1fr)_180px_180px_140px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#0b7466]" />
            <input
              aria-label="搜索公司"
              className="h-12 w-full rounded-[20px] border border-[#d8e1ec] bg-[#f8fafc] pl-10 pr-4 text-sm font-bold text-[#0b1220] outline-none transition placeholder:text-[#8b99ad] focus:border-[#20c7a7] focus:bg-white focus:ring-2 focus:ring-[#d5faf1]"
              onChange={(event) => updateFilter("companyKeyword", event.target.value)}
              placeholder="搜索公司"
              value={filters.companyKeyword}
            />
          </label>
          <FilterSelect ariaLabel="匹配状态筛选" onChange={(value) => updateFilter("matchStatus", value)} value={filters.matchStatus}>
            <option value="">全部匹配状态</option>
            <option value="strong_match">强匹配</option>
            <option value="review">待复核</option>
            <option value="weak_match">弱匹配</option>
          </FilterSelect>
          <FilterSelect ariaLabel="求职意图筛选" onChange={(value) => updateFilter("roleIntent", value)} value={filters.roleIntent}>
            <option value="">全部求职意图</option>
            <option value="intern">实习</option>
            <option value="full_time">全职</option>
            <option value="any">不限</option>
          </FilterSelect>
          <label className="inline-flex h-12 cursor-pointer items-center gap-2 rounded-[20px] border border-[#d8e1ec] bg-[#f8fafc] px-4 text-sm font-bold text-[#294256] transition hover:bg-white">
            <input
              aria-label="仅看已选岗位"
              checked={filters.selectedOnly}
              className="h-4 w-4 accent-[#20c7a7]"
              onChange={(event) => updateFilter("selectedOnly", event.target.checked)}
              type="checkbox"
            />
            仅看已选
          </label>
        </div>

        {state.error ? <div className="border-b border-[#f0b8b8] bg-[#fff7f7] px-3 py-3 text-sm font-bold text-[#b42318]">{state.error}</div> : null}

        <div className="overflow-hidden">
          <table aria-label="岗位样本确认列表" className="w-full table-fixed border-collapse text-sm">
            <colgroup>
              <col style={{ width: "6%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "5%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "14%" }} />
              <col style={{ width: "20%" }} />
              <col style={{ width: "8%" }} />
              <col style={{ width: "12%" }} />
              <col style={{ width: "9%" }} />
              <col style={{ width: "4%" }} />
              <col style={{ width: "6%" }} />
            </colgroup>
            <thead className="bg-[#f8fafc] text-left text-xs font-bold text-[#607089]">
              <tr>
                <th className="whitespace-nowrap py-3 pl-5 pr-3 text-center" scope="col">选择</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">匹配</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">分数</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">求职类型</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">公司</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">岗位名称</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">城市</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">薪资</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">经验</th>
                <th className="whitespace-nowrap px-3 py-3" scope="col">学历</th>
                <th className="whitespace-nowrap py-3 pl-2 pr-7 text-center" scope="col">详情</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#edf2f7]">
              {state.loading ? <TableMessage message="正在加载岗位..." /> : null}
              {!state.loading && state.rows.length === 0 ? <TableMessage message="没有符合条件的岗位" /> : null}
              {!state.loading
                ? state.rows.map((row) => (
                    <JobTableRows
                      expanded={expandedJobId === row.job_id}
                      key={row.job_id}
                      onExpand={() => setExpandedJobId((current) => (current === row.job_id ? null : row.job_id))}
                      onToggleSelected={() => toggleSelected(row.job_id)}
                      row={row}
                      selected={Boolean(selectedById[row.job_id])}
                    />
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

function SampleMetricPill({ icon, label, value, helper }: { icon: React.ReactNode; label: string; value: string; helper?: string }) {
  return (
    <div className="flex h-[70px] items-center gap-3 rounded-[22px] border border-[#d8e1ec] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)]">
      <span className="shrink-0 text-[#0b7466]">{icon}</span>
      <span className="min-w-0">
        <span className="block text-xs font-bold text-[#607089]">{label}</span>
        <span className="mt-1 flex min-w-0 items-baseline gap-2">
          <span className="block truncate text-xl font-bold text-[#0b1220]">{value}</span>
          {helper ? <span className="shrink-0 text-xs font-bold text-[#7a8799]">{helper}</span> : null}
        </span>
      </span>
    </div>
  );
}

function FilterSelect({ ariaLabel, value, onChange, children }: { ariaLabel: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <select
      aria-label={ariaLabel}
      className="h-12 rounded-[20px] border border-[#d8e1ec] bg-[#f8fafc] px-4 text-sm font-bold text-[#294256] outline-none transition focus:border-[#20c7a7] focus:bg-white focus:ring-2 focus:ring-[#d5faf1]"
      onChange={(event) => onChange(event.target.value)}
      value={value}
    >
      {children}
    </select>
  );
}
function JobTableRows({ row, selected, expanded, onToggleSelected, onExpand }: { row: JobRow; selected: boolean; expanded: boolean; onToggleSelected: () => void; onExpand: () => void }) {
  return (
    <>
      <tr className="bg-white align-top hover:bg-[#fbfcfe]">
        <td className="whitespace-nowrap py-4 pl-5 pr-3 text-center">
          <input aria-label={`${selected ? "取消选择" : "选择"}${row.job_title || "岗位"}`} checked={selected} className="h-4 w-4 accent-[#2364aa]" onChange={onToggleSelected} type="checkbox" />
        </td>
        <td className="whitespace-nowrap px-3 py-4"><Badge label={matchStatusLabel(row.match_status)} tone={row.match_status === "strong_match" ? "green" : row.match_status === "review" ? "amber" : "gray"} /></td>
        <td className="whitespace-nowrap px-3 py-4 font-semibold">{Math.round(row.match_score)}</td>
        <td className="whitespace-nowrap px-3 py-4">{roleIntentLabel(row.role_intent)}</td>
        <td className="px-3 py-4"><span className="block truncate" title={row.company_name || ""}>{row.company_name || "-"}</span></td>
        <td className="px-3 py-4 font-medium"><span className="block leading-6 [overflow-wrap:anywhere]">{row.job_title || "-"}</span></td>
        <td className="whitespace-nowrap px-3 py-4">{row.city || "-"}</td>
        <td className="whitespace-nowrap px-3 py-4">{row.salary || "-"}</td>
        <td className="whitespace-nowrap px-3 py-4">{row.experience || "-"}</td>
        <td className="px-2 py-4 leading-6 [overflow-wrap:anywhere]">{row.education || "-"}</td>
        <td className="whitespace-nowrap py-4 pl-2 pr-7 text-center">
          <button aria-expanded={expanded} className="inline-flex cursor-pointer items-center justify-center gap-1 whitespace-nowrap text-sm font-medium text-[#2364aa]" onClick={onExpand} type="button">
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            {expanded ? "收起" : "展开"}
          </button>
        </td>
      </tr>
      {expanded ? (
        <tr className="bg-[#fbfcfe]">
          <td className="px-3 py-4" colSpan={11}>
            <div className="grid gap-4 lg:grid-cols-2">
              <ReasonBlock title="匹配原因" values={row.match_reasons} />
              <ReasonBlock title="复核原因" values={row.review_reasons} empty="无复核原因" />
              <div className="rounded-md border border-[#e8ecf2] bg-white px-4 py-3 text-sm">
                <div className="font-semibold">岗位信息</div>
                <div className="mt-2 grid gap-2 text-[#647086] sm:grid-cols-3">
                  <span>描述长度：{row.description_length}</span>
                  <span>岗位编号：{row.job_id}</span>
                  <span>原始已选：{row.selected ? "是" : "否"}</span>
                </div>
              </div>
              <div className="rounded-md border border-[#e8ecf2] bg-white px-4 py-3 text-sm">
                <div className="font-semibold">来源链接</div>
                {row.original_url ? (
                  <a className="mt-2 inline-flex items-center gap-1 break-all text-[#2364aa]" href={row.original_url} rel="noreferrer" target="_blank">
                    {row.original_url}
                    <ExternalLink className="h-4 w-4 shrink-0" />
                  </a>
                ) : (
                  <p className="mt-2 text-[#647086]">暂无来源链接</p>
                )}
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function ReasonBlock({ title, values, empty = "暂无" }: { title: string; values: string[]; empty?: string }) {
  return (
    <div className="rounded-md border border-[#e8ecf2] bg-white px-4 py-3 text-sm">
      <div className="font-semibold">{title}</div>
      {values.length ? (
        <ul className="mt-2 space-y-1 text-[#647086]">
          {values.map((value) => <li key={value}>{value}</li>)}
        </ul>
      ) : (
        <p className="mt-2 text-[#647086]">{empty}</p>
      )}
    </div>
  );
}

function TableMessage({ message }: { message: string }) {
  return (
    <tr>
      <td className="px-5 py-8 text-center text-[#647086]" colSpan={11}>{message}</td>
    </tr>
  );
}

function Badge({ label, tone }: { label: string; tone: "green" | "amber" | "gray" }) {
  const styles = {
    green: "bg-[#e8f7f2] text-[#2f7d65]",
    amber: "bg-[#fff7e6] text-[#9a6700]",
    gray: "bg-[#f1f5f9] text-[#647086]",
  };
  return <span className={["inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-bold", styles[tone]].join(" ")}>{label}</span>;
}

function matchStatusLabel(value: string) {
  const labels: Record<string, string> = {
    strong_match: "强匹配",
    review: "待复核",
    weak_match: "弱匹配",
  };
  return labels[value] ?? value;
}

function roleIntentLabel(value: string) {
  const labels: Record<string, string> = {
    intern: "实习",
    full_time: "全职",
    engineering: "工程岗",
    partner_business: "商务合作",
    sales_solution: "销售方案",
    product: "产品",
    operations: "运营",
    other: "待确认",
    any: "不限",
  };
  return labels[value] ?? value;
}