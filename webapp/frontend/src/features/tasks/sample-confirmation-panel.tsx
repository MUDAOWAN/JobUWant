"use client";

import { CheckCircle2, ChevronDown, ChevronRight, ExternalLink, ListChecks, RefreshCw, Rows3, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { listJobs, saveSample, type AnalysisTask, type JobRow } from "@/lib/api";
import { formatCount, formatPercent } from "@/lib/format";
import { ErrorBanner, MetricBlock, Panel, primaryButtonClass, secondaryButtonClass } from "@/components/ui/shell";

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

const defaultFilters: Filters = {
  matchStatus: "",
  roleIntent: "",
  companyKeyword: "",
  titleKeyword: "",
  selectedOnly: false,
};

export function SampleConfirmationPanel({ task, onTaskChanged }: { task: AnalysisTask; onTaskChanged?: () => void }) {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [state, setState] = useState<LoadState>({ rows: [], total: 0, loading: true, error: "" });
  const [selectedById, setSelectedById] = useState<Record<number, boolean>>({});
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await listJobs(task.id, {
        match_status: filters.matchStatus,
        role_intent: filters.roleIntent,
        company_keyword: filters.companyKeyword.trim(),
        title_keyword: filters.titleKeyword.trim(),
        selected_only: filters.selectedOnly,
        limit: 100,
        offset: 0,
      });
      setState({ rows: payload.rows, total: payload.total, loading: false, error: "" });
      setSelectedById((current) => {
        const next = { ...current };
        payload.rows.forEach((row) => {
          if (next[row.job_id] === undefined) {
            next[row.job_id] = row.selected;
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
  }, [filters, task.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => {
    const visibleSelected = state.rows.filter((row) => selectedById[row.job_id]).length;
    const fixtureSelected = state.rows.filter((row) => row.selected).length;
    return { visibleSelected, fixtureSelected };
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
      setSaveMessage("样本已保存。");
      await load();
      onTaskChanged?.();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "样本保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-5">
      <Panel className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-[#2364aa]">样本确认</p>
            <h2 className="mt-1 text-xl font-semibold">岗位样本表</h2>
            <p className="mt-2 text-sm leading-6 text-[#647086]">live 任务可以保存当前选择；样本任务保持只读预览。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className={secondaryButtonClass}
              onClick={() => void load()}
              type="button"
            >
              <RefreshCw className="h-4 w-4" />
              刷新岗位
            </button>
            <button
              className={primaryButtonClass}
              disabled={!task.id.startsWith("task-") || saving || summary.visibleSelected === 0}
              onClick={() => void submitSample()}
              type="button"
            >
              <CheckCircle2 className="h-4 w-4" />
              {saving ? "保存中" : "保存样本"}
            </button>
          </div>
        </div>

        <ErrorBanner message={saveError} />
        {saveMessage ? <div className="mt-4 rounded-md border border-[#bde8d8] bg-[#f1fbf7] px-3 py-2 text-sm text-[#2f7d65]">{saveMessage}</div> : null}

        <div className="mt-5 grid gap-4 border-t border-[#e8ecf2] pt-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricBlock icon={<ListChecks className="h-4 w-4" />} label="接口返回" value={formatCount(state.total)} />
          <MetricBlock icon={<Rows3 className="h-4 w-4" />} label="当前页岗位" value={formatCount(state.rows.length)} />
          <MetricBlock icon={<CheckCircle2 className="h-4 w-4" />} label="本地已选" value={formatCount(summary.visibleSelected)} helper={`${formatPercent(summary.visibleSelected, state.rows.length)} 当前页`} />
          <MetricBlock icon={<CheckCircle2 className="h-4 w-4" />} label="原始已选" value={formatCount(summary.fixtureSelected)} />
        </div>
      </Panel>

      <Panel className="overflow-hidden">
        <div className="grid gap-3 border-b border-[#e8ecf2] px-5 py-4 lg:grid-cols-[1fr_180px_180px_140px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#647086]" />
            <input
              aria-label="搜索岗位标题"
              className="h-10 w-full rounded-md border border-[#d9dee8] bg-white pl-9 pr-3 text-sm outline-none transition placeholder:text-[#9aa4b4] focus:border-[#2364aa]"
              onChange={(event) => updateFilter("titleKeyword", event.target.value)}
              placeholder="搜索岗位标题"
              value={filters.titleKeyword}
            />
          </label>
          <select
            aria-label="匹配状态筛选"
            className="h-10 rounded-md border border-[#d9dee8] bg-white px-3 text-sm outline-none focus:border-[#2364aa]"
            onChange={(event) => updateFilter("matchStatus", event.target.value)}
            value={filters.matchStatus}
          >
            <option value="">全部匹配状态</option>
            <option value="strong_match">强匹配</option>
            <option value="review">待复核</option>
            <option value="weak_match">弱匹配</option>
          </select>
          <select
            aria-label="求职意图筛选"
            className="h-10 rounded-md border border-[#d9dee8] bg-white px-3 text-sm outline-none focus:border-[#2364aa]"
            onChange={(event) => updateFilter("roleIntent", event.target.value)}
            value={filters.roleIntent}
          >
            <option value="">全部求职意图</option>
            <option value="intern">实习</option>
            <option value="full_time">全职</option>
            <option value="any">不限</option>
          </select>
          <label className="inline-flex h-10 items-center gap-2 rounded-md border border-[#d9dee8] px-3 text-sm text-[#172033]">
            <input
              aria-label="仅看已选岗位"
              checked={filters.selectedOnly}
              className="h-4 w-4 accent-[#2364aa]"
              onChange={(event) => updateFilter("selectedOnly", event.target.checked)}
              type="checkbox"
            />
            仅看已选
          </label>
          <label className="relative block lg:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#647086]" />
            <input
              aria-label="搜索公司"
              className="h-10 w-full rounded-md border border-[#d9dee8] bg-white pl-9 pr-3 text-sm outline-none transition placeholder:text-[#9aa4b4] focus:border-[#2364aa]"
              onChange={(event) => updateFilter("companyKeyword", event.target.value)}
              placeholder="搜索公司"
              value={filters.companyKeyword}
            />
          </label>
        </div>

        {state.error ? <div className="border-b border-[#f0b8b8] bg-[#fff7f7] px-5 py-3 text-sm text-[#b42318]">{state.error}</div> : null}

        <div className="overflow-x-auto">
          <table aria-label="岗位样本确认列表" className="w-full min-w-[1180px] border-collapse text-sm">
            <thead className="bg-[#f8fafc] text-left text-xs font-semibold text-[#647086]">
              <tr>
                <th className="px-5 py-3" scope="col">选择</th>
                <th className="px-4 py-3" scope="col">匹配</th>
                <th className="px-4 py-3" scope="col">分数</th>
                <th className="px-4 py-3" scope="col">意图</th>
                <th className="px-4 py-3" scope="col">公司</th>
                <th className="px-4 py-3" scope="col">岗位</th>
                <th className="px-4 py-3" scope="col">城市</th>
                <th className="px-4 py-3" scope="col">薪资</th>
                <th className="px-4 py-3" scope="col">经验</th>
                <th className="px-4 py-3" scope="col">学历</th>
                <th className="px-5 py-3" scope="col">详情</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e8ecf2]">
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
      </Panel>
    </section>
  );
}

function JobTableRows({ row, selected, expanded, onToggleSelected, onExpand }: { row: JobRow; selected: boolean; expanded: boolean; onToggleSelected: () => void; onExpand: () => void }) {
  return (
    <>
      <tr className="bg-white align-top hover:bg-[#fbfcfe]">
        <td className="px-5 py-4">
          <input aria-label={`${selected ? "取消选择" : "选择"}${row.job_title || "岗位"}`} checked={selected} className="h-4 w-4 accent-[#2364aa]" onChange={onToggleSelected} type="checkbox" />
        </td>
        <td className="px-4 py-4"><Badge label={matchStatusLabel(row.match_status)} tone={row.match_status === "strong_match" ? "green" : row.match_status === "review" ? "amber" : "gray"} /></td>
        <td className="px-4 py-4 font-semibold">{Math.round(row.match_score)}</td>
        <td className="px-4 py-4">{roleIntentLabel(row.role_intent)}</td>
        <td className="px-4 py-4">{row.company_name || "-"}</td>
        <td className="max-w-[260px] px-4 py-4 font-medium"><span className="line-clamp-2">{row.job_title || "-"}</span></td>
        <td className="px-4 py-4">{row.city || "-"}</td>
        <td className="px-4 py-4">{row.salary || "-"}</td>
        <td className="px-4 py-4">{row.experience || "-"}</td>
        <td className="px-4 py-4">{row.education || "-"}</td>
        <td className="px-5 py-4">
          <button aria-expanded={expanded} className="inline-flex items-center gap-1 text-sm font-medium text-[#2364aa]" onClick={onExpand} type="button">
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            {expanded ? "收起" : "展开"}
          </button>
        </td>
      </tr>
      {expanded ? (
        <tr className="bg-[#fbfcfe]">
          <td className="px-5 py-4" colSpan={11}>
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
  return <span className={["inline-flex rounded-full px-2 py-1 text-xs font-medium", styles[tone]].join(" ")}>{label}</span>;
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
    any: "不限",
  };
  return labels[value] ?? value;
}

