"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { BookOpenText, BriefcaseBusiness, CheckCircle2, FileJson, Layers3, Lightbulb, RefreshCw, Route, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getFinalReport, type AnalysisTask, type FinalReportRead } from "@/lib/api";
import { formatCount } from "@/lib/format";
import { EmptyState, ErrorBanner, MetricBlock, Panel, PanelHeader, primaryButtonClass, secondaryButtonClass } from "@/components/ui/shell";

type LoadState = {
  payload: FinalReportRead | null;
  loading: boolean;
  error: string;
};

type Dict = Record<string, unknown>;

const chartColors = ["#2364aa", "#2f9f7f", "#d88c2a", "#7c5cba", "#4f6f7f", "#b85c5c"];
const layerLabels: Record<string, string> = {
  core: "核心层",
  common: "通用层",
  nice_to_have: "加分层",
};

export function FinalReportViewer({ task }: { task: AnalysisTask }) {
  const [state, setState] = useState<LoadState>({ payload: null, loading: true, error: "" });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await getFinalReport(task.id);
      setState({ payload, loading: false, error: "" });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "最终报告加载失败",
      }));
    }
  }, [task.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const report = state.payload;
  const sections = report?.sections ?? {};
  const roleProfile = dictValue(sections.role_profile);
  const salary = dictValue(sections.salary_and_threshold);
  const experience = dictValue(sections.experience_and_education);
  const graduate = dictValue(sections.graduate_friendliness);
  const skillLayers = dictValue(sections.skill_layers);
  const technicalItems = arrayOfDicts(sections.technical_top15_interpretation);
  const coreSkills = arrayOfDicts(sections.core_skills);
  const abilityItems = arrayOfDicts(sections.ability_requirements);
  const learningRoute = arrayOfDicts(sections.learning_route);
  const projectSuggestions = arrayOfDicts(sections.project_suggestions);
  const resumeKeywords = arrayOfStrings(sections.resume_keywords);
  const advice = arrayOfStrings(sections.job_search_advice);
  const caveats = arrayOfStrings(sections.caveats);

  const layerChartData = useMemo(() => {
    return ["core", "common", "nice_to_have"].map((key) => ({
      name: layerLabels[key],
      count: arrayOfDicts(skillLayers[key]).length,
    }));
  }, [skillLayers]);

  const priorityChartData = useMemo(() => {
    const counts = [...technicalItems, ...coreSkills, ...abilityItems].reduce<Record<string, number>>((acc, item) => {
      const key = String(item.priority || "未标注");
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts).map(([name, count]) => ({ name: priorityLabel(name), count }));
  }, [technicalItems, coreSkills, abilityItems]);

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
      <Panel className="p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-4xl">
            <p className="text-sm font-medium text-[#2364aa]">最终报告</p>
            <h2 className="mt-2 text-2xl font-semibold leading-tight">{report.report_title || task.task_name}</h2>
            <p className="mt-4 text-base leading-8 text-[#3d485c]">{report.audience_summary || "暂无摘要"}</p>
            <p className="mt-3 break-words text-xs leading-5 text-[#647086]">{report.path}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <button className={secondaryButtonClass} onClick={() => void load()} type="button">
              <RefreshCw className="h-4 w-4" />
              刷新报告
            </button>
            <Link className={primaryButtonClass} href={`/tasks/${task.id}/report-input`}>
              <FileJson className="h-4 w-4" />
              报告输入
            </Link>
          </div>
        </div>

        <div className="mt-6 grid gap-4 border-t border-[#e8ecf2] pt-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricBlock icon={<Lightbulb className="h-4 w-4" />} label="技术解释" value={formatCount(technicalItems.length)} />
          <MetricBlock icon={<CheckCircle2 className="h-4 w-4" />} label="核心技能" value={formatCount(coreSkills.length)} />
          <MetricBlock icon={<BriefcaseBusiness className="h-4 w-4" />} label="项目建议" value={formatCount(projectSuggestions.length)} />
          <MetricBlock icon={<FileJson className="h-4 w-4" />} label="简历关键词" value={formatCount(resumeKeywords.length)} />
        </div>
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <NarrativeSection icon={<BookOpenText className="h-4 w-4 text-[#2364aa]" />} item={roleProfile} title="岗位画像" />
        <ChartPanel data={layerChartData} title="技能层级" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <TechnicalInterpretation items={technicalItems} />
        <ChartPanel data={priorityChartData} title="优先级分布" />
      </section>

      <SkillLayerSection skillLayers={skillLayers} />

      <section className="grid gap-5 xl:grid-cols-3">
        <NarrativeSection icon={<BriefcaseBusiness className="h-4 w-4 text-[#2364aa]" />} item={salary} title="薪资与门槛" />
        <NarrativeSection icon={<CheckCircle2 className="h-4 w-4 text-[#2f9f7f]" />} item={experience} title="经验与学历" />
        <NarrativeSection icon={<Sparkles className="h-4 w-4 text-[#d88c2a]" />} item={graduate} title="应届友好度" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <LearningRouteSection items={learningRoute} />
        <KeywordPanel keywords={resumeKeywords} advice={advice} caveats={caveats} />
      </section>

      <ProjectSection items={projectSuggestions} />
    </article>
  );
}

function NarrativeSection({ icon, item, title }: { icon: ReactNode; item: Dict; title: string }) {
  return (
    <Panel className="p-5">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-base font-semibold">{String(item.title || title)}</h3>
      </div>
      <p className="mt-4 text-sm leading-7 text-[#3d485c]">{String(item.summary || "暂无内容")}</p>
      <EvidenceList refs={arrayOfDicts(item.evidence_refs)} />
    </Panel>
  );
}

function TechnicalInterpretation({ items }: { items: Dict[] }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="技术 Top 解释" actions={<Lightbulb className="h-4 w-4 text-[#d88c2a]" />} />
      <div className="divide-y divide-[#e8ecf2]">
        {items.length === 0 ? <p className="px-5 py-6 text-sm text-[#647086]">暂无技术解释</p> : null}
        {items.map((item, index) => (
          <div className="px-5 py-4" key={`${String(item.name || "item")}-${index}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#e6f0ff] text-xs font-semibold text-[#2364aa]">{index + 1}</span>
              <h4 className="text-sm font-semibold">{String(item.name || "未命名")}</h4>
              <Badge label={priorityLabel(String(item.priority || ""))} />
            </div>
            <p className="mt-3 text-sm leading-7 text-[#3d485c]">{String(item.reason || "暂无说明")}</p>
            <EvidenceList refs={arrayOfDicts(item.evidence_refs).slice(0, 1)} compact />
          </div>
        ))}
      </div>
    </Panel>
  );
}

function SkillLayerSection({ skillLayers }: { skillLayers: Dict }) {
  const layers = ["core", "common", "nice_to_have"];
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="技能层级" actions={<Layers3 className="h-4 w-4 text-[#2364aa]" />} />
      <div className="grid gap-4 px-5 py-4 xl:grid-cols-3">
        {layers.map((layer) => {
          const items = arrayOfDicts(skillLayers[layer]);
          return (
            <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3" key={layer}>
              <div className="flex items-center justify-between gap-3">
                <h4 className="text-sm font-semibold">{layerLabels[layer]}</h4>
                <span className="text-xs text-[#647086]">{formatCount(items.length)} 项</span>
              </div>
              <div className="mt-3 space-y-3">
                {items.length === 0 ? <p className="text-sm text-[#647086]">暂无</p> : null}
                {items.slice(0, 8).map((item) => (
                  <div className="text-sm" key={String(item.name)}>
                    <div className="font-medium">{String(item.name || "-")}</div>
                    <p className="mt-1 line-clamp-2 leading-6 text-[#647086]">{String(item.reason || "")}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function LearningRouteSection({ items }: { items: Dict[] }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="学习路线" actions={<Route className="h-4 w-4 text-[#2364aa]" />} />
      <div className="space-y-4 px-5 py-4">
        {items.length === 0 ? <p className="text-sm text-[#647086]">暂无学习路线</p> : null}
        {items.map((item, index) => (
          <div className="flex gap-3" key={`${String(item.stage)}-${index}`}>
            <div className="flex w-8 flex-col items-center">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#e8f7f2] text-sm font-semibold text-[#2f9f7f]">{index + 1}</span>
              {index + 1 < items.length ? <span className="mt-2 h-full w-px bg-[#e8ecf2]" /> : null}
            </div>
            <div className="min-w-0 flex-1 pb-2">
              <h4 className="text-sm font-semibold">{String(item.stage || `阶段 ${index + 1}`)}</h4>
              <ul className="mt-2 space-y-1 text-sm leading-6 text-[#3d485c]">
                {arrayOfStrings(item.focus).map((focus) => <li key={focus}>{focus}</li>)}
              </ul>
              <p className="mt-2 text-sm leading-6 text-[#647086]">{String(item.suggestion || "")}</p>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function ProjectSection({ items }: { items: Dict[] }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title="项目建议" />
      <div className="grid gap-4 px-5 py-4 xl:grid-cols-3">
        {items.length === 0 ? <p className="text-sm text-[#647086]">暂无项目建议</p> : null}
        {items.map((item) => (
          <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-4" key={String(item.project_name)}>
            <h4 className="text-sm font-semibold">{String(item.project_name || "未命名项目")}</h4>
            <ChipList values={arrayOfStrings(item.stack)} limit={8} />
            <InfoRow label="输入" value={String(item.data_or_input || "-")} />
            <InfoRow label="交付" value={String(item.deliverable || "-")} />
            <p className="mt-3 text-sm leading-6 text-[#3d485c]">{String(item.resume_value || "")}</p>
            <EvidenceList refs={arrayOfDicts(item.evidence_refs).slice(0, 2)} compact />
          </div>
        ))}
      </div>
    </Panel>
  );
}

function KeywordPanel({ keywords, advice, caveats }: { keywords: string[]; advice: string[]; caveats: string[] }) {
  return (
    <section className="space-y-5">
      <Panel className="overflow-hidden">
        <PanelHeader title="简历关键词" />
        <div className="px-5 pb-4">
          <ChipList values={keywords} limit={32} />
        </div>
      </Panel>
      <ListPanel items={advice} title="求职建议" />
      <ListPanel items={caveats} title="注意事项" tone="amber" />
    </section>
  );
}

function ChartPanel({ data, title }: { data: Array<{ name: string; count: number }>; title: string }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title={title} />
      <div className="h-56 px-5 py-4">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={data} margin={{ bottom: 8, left: -20, right: 8, top: 8 }}>
            <CartesianGrid stroke="#e8ecf2" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => <Cell fill={chartColors[index % chartColors.length]} key={entry.name} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function ListPanel({ items, title, tone = "blue" }: { items: string[]; title: string; tone?: "blue" | "amber" }) {
  return (
    <Panel className="overflow-hidden">
      <PanelHeader title={title} />
      <div className="space-y-3 px-5 py-4">
        {items.length === 0 ? <p className="text-sm text-[#647086]">暂无</p> : null}
        {items.map((item, index) => (
          <div className="flex gap-3 text-sm leading-6" key={`${title}-${index}`}>
            <span className={tone === "amber" ? "mt-1 h-2 w-2 shrink-0 rounded-full bg-[#d88c2a]" : "mt-1 h-2 w-2 shrink-0 rounded-full bg-[#2364aa]"} />
            <p className="text-[#3d485c]">{item}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function EvidenceList({ refs, compact = false }: { refs: Dict[]; compact?: boolean }) {
  if (refs.length === 0) {
    return null;
  }
  return (
    <div className={compact ? "mt-3 space-y-2" : "mt-4 space-y-2"}>
      {refs.map((ref, index) => (
        <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-3 py-2 text-xs leading-5 text-[#647086]" key={`${String(ref.topic)}-${String(ref.job_id)}-${index}`}>
          <span className="font-medium text-[#172033]">{String(ref.topic || "证据")}</span>
          {ref.job_id ? <span> · 岗位 {String(ref.job_id)}</span> : null}
          {ref.quote ? <p className="mt-1 text-[#3d485c]">{String(ref.quote)}</p> : null}
        </div>
      ))}
    </div>
  );
}

function ChipList({ values, limit }: { values: string[]; limit: number }) {
  const visible = values.slice(0, limit);
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {visible.length === 0 ? <p className="text-sm text-[#647086]">暂无</p> : null}
      {visible.map((value) => (
        <span className="rounded-full bg-[#e6f0ff] px-2.5 py-1 text-xs font-medium text-[#2364aa]" key={value}>{value}</span>
      ))}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="mt-3 grid grid-cols-[42px_minmax(0,1fr)] gap-2 text-sm leading-6">
      <span className="text-[#647086]">{label}</span>
      <span className="text-[#3d485c]">{value}</span>
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return <span className="rounded-full bg-[#f1f5f9] px-2 py-0.5 text-xs text-[#647086]">{label}</span>;
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

function priorityLabel(value: string) {
  const labels: Record<string, string> = {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级",
  };
  return labels[value] ?? (value || "未标注");
}

