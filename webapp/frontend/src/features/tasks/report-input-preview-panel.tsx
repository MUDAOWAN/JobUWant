"use client";

import { BarChart3, Code2, FileJson, ListChecks, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getReportInput, type AnalysisTask, type ReportInputPreview, type TechnicalTermItem } from "@/lib/api";
import { formatCount } from "@/lib/format";
import { EmptyState, ErrorBanner, MetricBlock, Panel, PanelHeader, secondaryButtonClass } from "@/components/ui/shell";

type LoadState = {
  payload: ReportInputPreview | null;
  loading: boolean;
  error: string;
};

type Dict = Record<string, unknown>;

const chartColors = ["#2364aa", "#2f9f7f", "#d88c2a", "#7c5cba", "#4f6f7f", "#b85c5c"];

export function ReportInputPreviewPanel({ task }: { task: AnalysisTask }) {
  const [state, setState] = useState<LoadState>({ payload: null, loading: true, error: "" });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await getReportInput(task.id);
      setState({ payload, loading: false, error: "" });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "报告输入加载失败",
      }));
    }
  }, [task.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const preview = state.payload;
  const sample = useMemo(() => preview?.sample ?? {}, [preview?.sample]);
  const salary = preview?.salary_summary ?? {};
  const evidence = useMemo(() => preview?.evidence_quality ?? {}, [preview?.evidence_quality]);

  const termChartData = useMemo(
    () =>
      (preview?.technical_terms_top ?? []).slice(0, 10).map((term) => ({
        name: String(term.name || term.key || "-"),
        count: numberValue(term.count),
        ratioLabel: percentValue(term.ratio),
      })),
    [preview],
  );

  const roleChartData = useMemo(
    () =>
      arrayOfDicts(sample.role_intent_distribution).slice(0, 8).map((item) => ({
        name: String(item.name || "-"),
        count: numberValue(item.count),
        ratioLabel: percentValue(item.ratio),
      })),
    [sample],
  );

  const qualityChartData = useMemo(() => {
    const total = numberValue(evidence.evidence_count);
    const hits = numberValue(evidence.exact_quote_hits);
    const missed = Math.max(total - hits, numberValue(evidence.miss_count));
    return [
      { name: "可直接引用", count: hits },
      { name: "需人工确认", count: missed },
    ].filter((item) => item.count > 0);
  }, [evidence]);

  if (state.loading && !preview) {
    return <EmptyState message="正在加载报告输入..." />;
  }

  if (state.error) {
    return <ErrorBanner message={`报告输入加载失败：${state.error}`} />;
  }

  if (!preview) {
    return <EmptyState message="暂无报告输入数据" />;
  }

  return (
    <section className="space-y-5">
      <Panel className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-[#2364aa]">报告输入预览</p>
            <h2 className="mt-1 text-xl font-semibold">最终报告生成前的数据包</h2>
            <p className="mt-2 max-w-3xl break-words text-sm leading-6 text-[#647086]">{preview.path}</p>
          </div>
          <button className={secondaryButtonClass} onClick={() => void load()} type="button">
            <RefreshCw className="h-4 w-4" />
            刷新输入
          </button>
        </div>

        <div className="mt-5 grid gap-4 border-t border-[#e8ecf2] pt-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricBlock icon={<ListChecks className="h-4 w-4" />} label="样本岗位" value={formatCount(numberValue(sample.total_jobs))} helper={`岗位编号 ${arrayValue(sample.job_ids).length} 个`} />
          <MetricBlock icon={<BarChart3 className="h-4 w-4" />} label="平均匹配分" value={fixedValue(sample.match_score_average)} helper="来自样本摘要" />
          <MetricBlock icon={<Code2 className="h-4 w-4" />} label="技术词数量" value={formatCount(preview.technical_terms_top.length)} helper="当前展示 Top 15" />
          <MetricBlock icon={<FileJson className="h-4 w-4" />} label="预估令牌" value={formatCount(preview.estimated_prompt_tokens)} helper="用于控制报告生成规模" />
        </div>
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <QueryPanel preview={preview} task={task} />
        <EvidencePanel evidence={evidence} qualityChartData={qualityChartData} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <ChartPanel data={termChartData} title="技术词 Top 10" />
        <SalaryPanel salary={salary} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <DistributionPanel data={roleChartData} title="角色意图分布" />
        <TopTermsPanel terms={preview.technical_terms_top} />
      </section>

      <JsonPreview raw={preview.raw} />
    </section>
  );
}

function QueryPanel({ preview, task }: { preview: ReportInputPreview; task: AnalysisTask }) {
  const query = preview.query;
  const rows = [
    ["任务", task.task_name],
    ["城市", String(query.city || task.city)],
    ["关键词", String(query.keyword || task.keyword)],
    ["求职类型", task.job_type],
    ["运行编号", String(query.search_run_id || task.search_run_id)],
    ["来源类型", String(query.source_type || task.source_type)],
    ["匹配范围", arrayValue(query.match_statuses).join(" / ") || "-"],
  ];
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="查询与样本边界" />
      <dl className="grid gap-3 px-5 py-4 text-sm">
        {rows.map(([label, value]) => (
          <div className="grid grid-cols-[90px_minmax(0,1fr)] gap-3" key={label}>
            <dt className="text-[#647086]">{label}</dt>
            <dd className="break-words font-medium text-[#172033]">{labelValue(label, value)}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

function EvidencePanel({ evidence, qualityChartData }: { evidence: Dict; qualityChartData: Array<{ name: string; count: number }> }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="证据质量" actions={<ShieldCheck className="h-4 w-4 text-[#2f9f7f]" />} />
      <div className="grid grid-cols-2 gap-3 px-5 py-4">
        <SmallMetric label="证据片段" value={formatCount(numberValue(evidence.evidence_count))} />
        <SmallMetric label="可引用率" value={percentValue(evidence.exact_quote_hit_ratio)} />
      </div>
      <div className="h-44 px-5 pb-5">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={qualityChartData} margin={{ left: -20, right: 8, top: 8 }}>
            <CartesianGrid stroke="#e8ecf2" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {qualityChartData.map((entry, index) => <Cell fill={chartColors[index % chartColors.length]} key={entry.name} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function ChartPanel({ data, title }: { data: Array<{ name: string; count: number; ratioLabel: string }>; title: string }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title={title} actions={<BarChart3 className="h-4 w-4 text-[#2364aa]" />} />
      <div className="h-72 px-5 py-4">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={data} layout="vertical" margin={{ bottom: 8, left: 34, right: 16, top: 8 }}>
            <CartesianGrid stroke="#e8ecf2" horizontal={false} />
            <XAxis allowDecimals={false} type="number" tick={{ fontSize: 12 }} />
            <YAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} type="category" width={86} />
            <Tooltip formatter={(value, _name, item) => [String(value), item.payload.ratioLabel]} />
            <Bar dataKey="count" fill="#2364aa" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function DistributionPanel({ data, title }: { data: Array<{ name: string; count: number; ratioLabel: string }>; title: string }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title={title} />
      <div className="space-y-3 px-5 py-4">
        {data.length === 0 ? <p className="text-sm text-[#647086]">暂无分布数据</p> : null}
        {data.map((item, index) => (
          <div className="space-y-1" key={item.name}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="min-w-0 truncate font-medium">{item.name}</span>
              <span className="shrink-0 text-[#647086]">{formatCount(item.count)} / {item.ratioLabel}</span>
            </div>
            <div className="h-2 rounded-full bg-[#edf1f6]">
              <div className="h-2 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length], width: item.ratioLabel === "-" ? "0%" : item.ratioLabel }} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function SalaryPanel({ salary }: { salary: Dict }) {
  const monthly = dictValue(salary.monthly_cny);
  const daily = dictValue(salary.daily_cny);
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="薪资摘要" />
      <div className="grid grid-cols-3 gap-3 px-5 py-4">
        <SmallMetric label="原始薪资" value={formatCount(numberValue(salary.raw_salary_count))} />
        <SmallMetric label="已解析" value={formatCount(numberValue(salary.parsed_count))} />
        <SmallMetric label="未解析" value={formatCount(numberValue(salary.unparsed_count))} />
      </div>
      <div className="grid gap-3 px-5 pb-5">
        <SalaryRange title="月薪 CNY" value={monthly} />
        <SalaryRange title="日薪 CNY" value={daily} />
      </div>
    </Panel>
  );
}

function SalaryRange({ title, value }: { title: string; value: Dict }) {
  if (Object.keys(value).length === 0) {
    return (
      <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3 text-sm">
        <div className="font-semibold">{title}</div>
        <p className="mt-2 text-[#647086]">暂无数据</p>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3 text-sm">
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold">{title}</span>
        <span className="text-[#647086]">{formatCount(numberValue(value.count))} 条</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[#647086]">
        <span>最低下限：{moneyValue(value.min_low)}</span>
        <span>最高上限：{moneyValue(value.max_high)}</span>
        <span>平均下限：{moneyValue(value.average_low)}</span>
        <span>平均上限：{moneyValue(value.average_high)}</span>
        <span className="col-span-2">中位数：{moneyValue(value.median_mid)}</span>
      </div>
    </div>
  );
}

function TopTermsPanel({ terms }: { terms: TechnicalTermItem[] }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="技术词证据" actions={<Code2 className="h-4 w-4 text-[#2364aa]" />} />
      <div className="space-y-3 px-5 py-4">
        {terms.slice(0, 6).map((term) => {
          const evidence = arrayOfDicts(term.evidence).at(0);
          return (
            <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3" key={String(term.key || term.name)}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{String(term.name || term.key || "-")}</span>
                <span className="rounded-full bg-[#e6f0ff] px-2 py-0.5 text-xs font-medium text-[#2364aa]">
                  {formatCount(numberValue(term.count))} 次 / {percentValue(term.ratio)}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-[#647086]">{evidence ? String(evidence.quote || "暂无证据摘录") : "暂无证据摘录"}</p>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function JsonPreview({ raw }: { raw: Dict }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="原始 JSON 预览" description="保留完整输入结构，便于核对报告生成前的数据包。" actions={<FileJson className="h-4 w-4 text-[#2364aa]" />} />
      <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap break-words bg-[#101828] px-5 py-4 text-xs leading-6 text-[#e6edf7]">
        {JSON.stringify(raw, null, 2)}
      </pre>
    </Panel>
  );
}

function SmallMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-3 py-3">
      <div className="text-xs text-[#647086]">{label}</div>
      <div className="mt-1 text-base font-semibold">{value}</div>
    </div>
  );
}

function numberValue(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function fixedValue(value: unknown) {
  const number = numberValue(value);
  return number ? number.toFixed(2) : "-";
}

function percentValue(value: unknown) {
  const number = numberValue(value);
  if (!number) {
    return "0%";
  }
  return `${Math.round(number * 100)}%`;
}

function moneyValue(value: unknown) {
  const number = numberValue(value);
  if (!number) {
    return "-";
  }
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(number);
}

function arrayValue(value: unknown) {
  return Array.isArray(value) ? value : [];
}

function arrayOfDicts(value: unknown) {
  return arrayValue(value).filter((item): item is Dict => Boolean(item) && typeof item === "object" && !Array.isArray(item));
}

function dictValue(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Dict) : {};
}

function labelValue(label: string, value: string) {
  if (label !== "求职类型") {
    return value || "-";
  }
  const labels: Record<string, string> = {
    intern: "实习",
    full_time: "全职",
    any: "不限",
  };
  return labels[value] ?? value ?? "-";
}

