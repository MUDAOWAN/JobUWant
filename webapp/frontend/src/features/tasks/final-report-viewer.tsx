"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardList,
  FileJson,
  Layers3,
  LineChart,
  PieChart,
  RefreshCw,
  Route,
  Sparkles,
  Target,
  WalletCards,
} from "lucide-react";
import {
  getFinalReport,
  getReportInput,
  type AnalysisTask,
  type FinalReportRead,
  type ReportInputPreview,
} from "@/lib/api";
import { formatCount } from "@/lib/format";
import { EmptyState, ErrorBanner, secondaryButtonClass } from "@/components/ui/shell";

type LoadState = {
  report: FinalReportRead | null;
  reportInput: ReportInputPreview | null;
  loading: boolean;
  error: string;
  reportInputError: string;
};

type Dict = Record<string, unknown>;

type DashboardData = {
  sampleCount: number;
  averageMatchScore: number;
  topRequirement: string;
  topRequirementHelper: string;
  salaryValue: string;
  salaryHelper: string;
  evidenceRatio: string;
  evidenceHelper: string;
  promptTokens: number;
  skillCount: number;
  layerSummary: string;
  roleDistributionCount: number;
  representativeJobCount: number;
  salaryParsedCount: number;
  educationBucketCount: number;
  experienceBucketCount: number;
  resumeKeywordCount: number;
  learningStageCount: number;
};

type SectionCard = {
  key: string;
  title: string;
  eyebrow: string;
  icon: ReactNode;
  description: string;
};

const sectionCards: SectionCard[] = [
  {
    key: "skills",
    title: "技能与能力分布",
    eyebrow: "市场需求地图",
    icon: <Layers3 className="h-4 w-4" />,
    description: "下一轮会把技能、工具、业务领域和通用能力统一成可比较的横向分布与层级矩阵。",
  },
  {
    key: "resume",
    title: "简历适配建议",
    eyebrow: "简历表达映射",
    icon: <ClipboardList className="h-4 w-4" />,
    description: "把市场要求转成简历表达、项目角度和可直接复用的措辞，目前先保留字段位置。",
  },
  {
    key: "job-structure",
    title: "岗位结构分析",
    eyebrow: "岗位构成",
    icon: <PieChart className="h-4 w-4" />,
    description: "后续接入岗位族群、角色方向、匹配状态与代表岗位表，解释这批样本的市场构成。",
  },
  {
    key: "salary",
    title: "薪资与门槛分析",
    eyebrow: "薪酬与门槛",
    icon: <WalletCards className="h-4 w-4" />,
    description: "后续展示薪资区间、学历分布和经验门槛；薪资不足时展示清晰的数据不足状态。",
  },
  {
    key: "learning",
    title: "学习路线与准备优先级",
    eyebrow: "准备路线",
    icon: <Route className="h-4 w-4" />,
    description: "后续把报告建议压缩成阶段路线和优先级矩阵，避免长篇学习计划。",
  },
];

export function FinalReportViewer({ task }: { task: AnalysisTask }) {
  const [state, setState] = useState<LoadState>({
    report: null,
    reportInput: null,
    loading: true,
    error: "",
    reportInputError: "",
  });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "", reportInputError: "" }));
    const [reportResult, inputResult] = await Promise.allSettled([
      getFinalReport(task.id),
      getReportInput(task.id),
    ]);

    if (reportResult.status === "rejected") {
      setState((current) => ({
        ...current,
        loading: false,
        error: reportResult.reason instanceof Error ? reportResult.reason.message : "最终报告加载失败",
      }));
      return;
    }

    setState({
      report: reportResult.value,
      reportInput: inputResult.status === "fulfilled" ? inputResult.value : null,
      loading: false,
      error: "",
      reportInputError: inputResult.status === "rejected"
        ? inputResult.reason instanceof Error
          ? inputResult.reason.message
          : "报告输入加载失败"
        : "",
    });
  }, [task.id]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const report = state.report;
  const reportInput = state.reportInput;
  const dashboard = useMemo(() => buildDashboardData(task, report, reportInput), [task, report, reportInput]);

  if (state.loading && !report) {
    return <EmptyState message="正在加载最终报告..." />;
  }

  if (state.error) {
    return <ErrorBanner message={`最终报告加载失败：${state.error}`} />;
  }

  if (!report) {
    return <EmptyState message="暂无最终报告数据" />;
  }

  return (
    <article className="space-y-5">
      <ReportSummaryHero
        dashboard={dashboard}
        onRefresh={() => void load()}
        report={report}
        reportInputError={state.reportInputError}
        task={task}
        usage={reportUsage(report)}
      />

      <CoreMetricsBar dashboard={dashboard} task={task} />

      <section className="space-y-5">
        {sectionCards.map((section) => (
          <ReportModuleShell dashboard={dashboard} key={section.key} section={section} />
        ))}
      </section>
    </article>
  );
}

function ReportSummaryHero({ dashboard, report, reportInputError, task, usage, onRefresh }: { dashboard: DashboardData; report: FinalReportRead; reportInputError: string; task: AnalysisTask; usage: ReportUsage; onRefresh: () => void }) {
  return (
    <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 p-4 shadow-[0_24px_74px_rgba(14,23,38,0.13),inset_0_1px_0_rgba(255,255,255,0.98)] backdrop-blur sm:p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <span className="inline-flex h-9 items-center gap-2 rounded-[16px] border border-[#bfe9dc] bg-[#f1fbf7] px-3 text-sm font-bold text-[#087a67] shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
            <span className="h-2 w-2 rounded-full bg-current" />
            分析报告
          </span>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <h2 className="max-w-full flex-none break-words text-3xl font-bold tracking-normal text-[#0b1220]">
              {report.report_title || task.task_name}
            </h2>
            <div className="flex max-w-full flex-none flex-wrap items-center gap-2 text-sm">
              <ReportQueryChip label="城市" value={cityLabel(task.city)} />
              <ReportQueryChip label="岗位" value={keywordLabel(task.keyword)} />
              <ReportQueryChip label="类型" value={jobTypeLabel(task.job_type)} />
              <ReportQueryChip label="样本" value={`${formatCount(dashboard.sampleCount)} 个`} />
            </div>
          </div>
          <p className="mt-4 max-w-5xl whitespace-pre-line text-sm font-medium leading-7 text-[#607089]">
            {report.audience_summary || "暂无摘要"}
          </p>
        </div>

        <div className="flex w-full shrink-0 flex-col items-stretch gap-3 lg:w-auto lg:items-end">
          <div className="flex flex-wrap justify-start gap-2 lg:justify-end">
            <button className={secondaryButtonClass} onClick={onRefresh} type="button">
              <RefreshCw className="h-4 w-4" />
              刷新报告
            </button>
            <Link className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#c8e7e1] bg-[#f2fbf8] px-3 text-sm font-bold text-[#0b7466] shadow-sm transition hover:border-[#20c7a7] hover:bg-[#e8fbf5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-2" href={`/tasks/${task.id}/report-input`}>
              <FileJson className="h-4 w-4" />
              报告输入
            </Link>
          </div>
          <HeroTokenUsagePanel usage={usage} />
        </div>
      </div>

      {reportInputError ? (
        <div className="mt-4 rounded-[18px] border border-[#f0d3a2] bg-[#fffaf0] px-4 py-3 text-sm font-medium leading-6 text-[#875514]">
          报告输入暂时不可用：{reportInputError}。当前页面会先展示最终报告文本和可用占位。
        </div>
      ) : null}

    </section>
  );
}

function HeroTokenUsagePanel({ usage }: { usage: ReportUsage }) {
  return (
    <div className="w-full rounded-[22px] border border-[#d8e1ec] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] lg:w-[376px]">
      <div className="flex items-center gap-2 text-[#294256]">
        <FileJson className="h-4 w-4 text-[#0b7466]" />
        <span className="text-xs font-bold text-[#607089]">AI token 消耗量</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <TokenUsageCell label="输入" value={usage.recorded ? formatCount(usage.inputTokens) : "-"} />
        <TokenUsageCell label="输出" value={usage.recorded ? formatCount(usage.outputTokens) : "-"} />
        <TokenUsageCell label="费用" value={usage.estimatedCny ? `¥${usage.estimatedCny.toFixed(4)}` : "-"} />
        <TokenUsageCell label="模型" value={usage.modelName || "-"} />
      </div>
    </div>
  );
}

function TokenUsageCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-[14px] border border-[#e5ecf4] bg-white px-3 py-2">
      <span className="block text-[11px] font-bold text-[#8a97aa]">{label}</span>
      <span className="mt-1 block truncate text-sm font-black text-[#0b1220]">{value}</span>
    </div>
  );
}
function CoreMetricsBar({ dashboard, task }: { dashboard: DashboardData; task: AnalysisTask }) {
  const metrics = [
    {
      label: "样本岗位",
      value: formatCount(dashboard.sampleCount),
      helper: `目标 ${formatCount(task.expected_job_count)} 条`,
      icon: <BriefcaseBusiness className="h-4 w-4" />,
    },
    {
      label: "强匹配岗位",
      value: "-",
      helper: "等待匹配状态分布字段",
      icon: <CheckCircle2 className="h-4 w-4" />,
    },
    {
      label: "平均匹配分",
      value: dashboard.averageMatchScore ? dashboard.averageMatchScore.toFixed(1) : "-",
      helper: "来自样本摘要",
      icon: <LineChart className="h-4 w-4" />,
    },
    {
      label: "高频要求",
      value: dashboard.topRequirement,
      helper: dashboard.topRequirementHelper,
      icon: <Sparkles className="h-4 w-4" />,
    },
    {
      label: "薪资中位",
      value: dashboard.salaryValue,
      helper: dashboard.salaryHelper,
      icon: <WalletCards className="h-4 w-4" />,
    },
    {
      label: "证据命中率",
      value: dashboard.evidenceRatio,
      helper: dashboard.evidenceHelper,
      icon: <Target className="h-4 w-4" />,
    },
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      {metrics.map((metric) => (
        <div className="min-h-[128px] rounded-[20px] border border-[#d8e1ec] bg-white px-4 py-4 shadow-[0_10px_26px_rgba(17,24,39,0.06)]" key={metric.label}>
          <div className="flex items-center gap-2 text-[#0b7466]">
            {metric.icon}
            <span className="text-xs font-bold uppercase tracking-[0.11em] text-[#607089]">{metric.label}</span>
          </div>
          <div className="mt-4 min-h-[34px] break-words text-2xl font-black leading-8 text-[#0b1220]">{metric.value}</div>
          <p className="mt-2 text-xs font-medium leading-5 text-[#607089]">{metric.helper}</p>
        </div>
      ))}
    </section>
  );
}

function ReportModuleShell({ dashboard, section }: { dashboard: DashboardData; section: SectionCard }) {
  const facts = moduleFacts(section.key, dashboard);
  return (
    <section className="overflow-hidden rounded-[24px] border border-[#d8e1ec] bg-white shadow-[0_12px_34px_rgba(17,24,39,0.07)]">
      <div className="grid gap-4 px-5 py-5 md:grid-cols-[minmax(0,1fr)_260px] md:items-start">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[#0b7466]">
            {section.icon}
            <span className="text-xs font-bold uppercase tracking-[0.14em] text-[#607089]">{section.eyebrow}</span>
          </div>
          <h3 className="mt-2 text-xl font-black leading-7 text-[#0b1220]">{section.title}</h3>
          <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-[#607089]">{section.description}</p>
        </div>
        <div className="rounded-[18px] border border-dashed border-[#cbd7e5] bg-[#f8fafc] px-4 py-3">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#607089]">数据预览</p>
          <div className="mt-3 grid gap-2">
            {facts.map((fact) => (
              <div className="flex items-center justify-between gap-3 text-sm" key={fact.label}>
                <span className="text-[#607089]">{fact.label}</span>
                <span className="min-w-0 break-words text-right font-bold text-[#0b1220]">{fact.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function ReportQueryChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex min-h-9 max-w-full min-w-0 flex-wrap items-center rounded-[14px] border border-[#d8e1ec] bg-[#f8fafc] px-3 py-1.5 text-sm font-bold leading-6 text-[#294256]">
      <span className="shrink-0 text-[#607089]">{label}：</span>
      <span className="min-w-0 break-words [overflow-wrap:anywhere]">{value || "-"}</span>
    </span>
  );
}

type ReportUsage = {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  estimatedCny: number;
  modelName: string;
  recorded: boolean;
};

function buildDashboardData(task: AnalysisTask, report: FinalReportRead | null, reportInput: ReportInputPreview | null): DashboardData {
  const raw = dictValue(reportInput?.raw);
  const sample = firstDict(reportInput?.sample, raw.sample);
  const salary = firstDict(reportInput?.salary_summary, raw.salary_summary);
  const evidence = firstDict(reportInput?.evidence_quality, raw.evidence_quality);
  const terms = firstArray(reportInput?.technical_terms_top, raw.technical_terms_top);
  const layers = dictValue(raw.technical_terms_layers);
  const representativeJobs = firstArray(raw.representative_jobs);
  const educationSummary = dictValue(raw.education_summary);
  const experienceSummary = dictValue(raw.experience_summary);
  const sections = report?.sections ?? {};
  const resumeKeywords = arrayOfStrings(sections.resume_keywords);
  const learningRoute = arrayOfDicts(sections.learning_route);
  const topTerm = dictValue(terms[0]);
  const roleDistribution = firstArray(
    sample.role_family_distribution,
    sample.normalized_role_distribution,
    sample.role_intent_distribution,
  );
  const salaryChoice = selectSalary(salary, task.job_type);
  const coreLayerCount = arrayOfDicts(layers.core).length;
  const commonLayerCount = arrayOfDicts(layers.common).length;

  return {
    sampleCount: firstPositiveNumber(sample.total_jobs, task.analysis_ready_count, task.collected_count),
    averageMatchScore: numberValue(sample.match_score_average),
    topRequirement: String(topTerm.name || topTerm.key || "暂无"),
    topRequirementHelper: topTerm.count
      ? `${formatCount(numberValue(topTerm.count))} 次 / ${percentValue(topTerm.ratio)}`
      : "等待高频要求数据",
    salaryValue: salaryChoice.value,
    salaryHelper: salaryChoice.helper,
    evidenceRatio: percentValue(evidence.exact_quote_hit_ratio),
    evidenceHelper: evidence.evidence_count
      ? `${formatCount(numberValue(evidence.exact_quote_hits))}/${formatCount(numberValue(evidence.evidence_count))} 条证据`
      : "等待证据统计",
    promptTokens: firstPositiveNumber(reportInput?.estimated_prompt_tokens, raw.estimated_prompt_tokens),
    skillCount: terms.length,
    layerSummary: coreLayerCount || commonLayerCount ? `核心 ${coreLayerCount} / 通用 ${commonLayerCount}` : "",
    roleDistributionCount: roleDistribution.length,
    representativeJobCount: representativeJobs.length,
    salaryParsedCount: numberValue(salary.parsed_count),
    educationBucketCount: arrayOfDicts(educationSummary.level_distribution).length,
    experienceBucketCount: arrayOfDicts(experienceSummary.level_distribution).length,
    resumeKeywordCount: resumeKeywords.length,
    learningStageCount: learningRoute.length,
  };
}

function moduleFacts(key: string, dashboard: DashboardData) {
  if (key === "skills") {
    return [
      { label: "Top 要求", value: formatCount(dashboard.skillCount) },
      { label: "层级矩阵", value: dashboard.layerSummary || "待整理" },
    ];
  }
  if (key === "resume") {
    return [
      { label: "简历关键词", value: formatCount(dashboard.resumeKeywordCount) },
      { label: "表达映射", value: "待新增" },
    ];
  }
  if (key === "job-structure") {
    return [
      { label: "角色分布", value: formatCount(dashboard.roleDistributionCount) },
      { label: "代表岗位", value: formatCount(dashboard.representativeJobCount) },
    ];
  }
  if (key === "salary") {
    return [
      { label: "已解析薪资", value: formatCount(dashboard.salaryParsedCount) },
      { label: "学历/经验桶", value: `${dashboard.educationBucketCount}/${dashboard.experienceBucketCount}` },
    ];
  }
  return [
    { label: "学习阶段", value: formatCount(dashboard.learningStageCount) },
    { label: "优先级矩阵", value: "待新增" },
  ];
}

function selectSalary(salary: Dict, jobType: string) {
  const daily = dictValue(salary.daily_cny);
  const monthly = dictValue(salary.monthly_cny);
  const preferred = jobType === "intern" ? daily : monthly;
  const fallback = jobType === "intern" ? monthly : daily;
  const preferredLabel = jobType === "intern" ? "日薪中位" : "月薪中位";
  const fallbackLabel = jobType === "intern" ? "月薪中位" : "日薪中位";
  const preferredValue = moneyValue(preferred.median_mid);
  if (preferredValue !== "-") {
    return { value: preferredValue, helper: `${preferredLabel}，${formatCount(numberValue(preferred.count))} 条样本` };
  }
  const fallbackValue = moneyValue(fallback.median_mid);
  if (fallbackValue !== "-") {
    return { value: fallbackValue, helper: `${fallbackLabel}，${formatCount(numberValue(fallback.count))} 条样本` };
  }
  return { value: "-", helper: "薪资样本不足" };
}

function reportUsage(report: FinalReportRead): ReportUsage {
  const raw = dictValue(report.raw);
  const usage = firstDict(raw.usage, raw.usage_summary, raw.model_usage, raw.token_usage, raw.metadata, raw.report_usage);
  const inputTokens = firstPositiveNumber(raw.input_tokens, usage.input_tokens, usage.prompt_tokens, usage.inputTokens);
  const outputTokens = firstPositiveNumber(raw.output_tokens, usage.output_tokens, usage.completion_tokens, usage.outputTokens);
  const totalTokens = firstPositiveNumber(raw.total_tokens, usage.total_tokens, usage.totalTokens, inputTokens + outputTokens);
  const estimatedCny = firstPositiveNumber(raw.estimated_cny, usage.estimated_cny, usage.estimatedCny, usage.cost_cny);
  const modelName = firstString(raw.model_name, usage.model_name, usage.model, usage.modelName);
  return {
    inputTokens,
    outputTokens,
    totalTokens,
    estimatedCny,
    modelName,
    recorded: totalTokens > 0 || inputTokens > 0 || outputTokens > 0 || estimatedCny > 0 || Boolean(modelName),
  };
}

function firstDict(...values: unknown[]) {
  for (const value of values) {
    const dict = dictValue(value);
    if (Object.keys(dict).length > 0) {
      return dict;
    }
  }
  return {};
}

function firstArray(...values: unknown[]) {
  for (const value of values) {
    if (Array.isArray(value) && value.length > 0) {
      return value;
    }
  }
  return [];
}

function firstPositiveNumber(...values: unknown[]) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number) && number > 0) {
      return number;
    }
  }
  return 0;
}

function numberValue(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
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

function firstString(...values: unknown[]) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text) {
      return text;
    }
  }
  return "";
}

function dictValue(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Dict) : {};
}

function arrayOfDicts(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is Dict => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}

function arrayOfStrings(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item)).filter(Boolean);
}

function cityLabel(value: string) {
  const labels: Record<string, string> = {
    Hangzhou: "杭州",
    Guangzhou: "广州",
  };
  return labels[value] ?? value;
}

function keywordLabel(value: string) {
  const labels: Record<string, string> = {
    "Agent engineer": "Agent 工程师",
    GIS: "GIS",
  };
  return labels[value] ?? value;
}

function jobTypeLabel(value: string) {
  const labels: Record<string, string> = {
    intern: "实习",
    full_time: "全职",
    any: "不限",
  };
  return labels[value] ?? value;
}