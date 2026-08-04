"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,

  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  Database,
  FileJson,
  FileText,
  ListChecks,
  Play,
  RefreshCw,
  Rows3,
  Settings2,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  buildReportInput,
  getHealth,
  getStructuringStatus,
  getTaskDetail,
  getTaskEvents,
  listTasks,
  runStructuringBatches,
  startCollection,
  startScoring,
  startStructuring,
  writeFinalReport,
  type AnalysisTask,
  type StructuringStatus,
  type TaskDetail,
  type TaskEvent,
} from "@/lib/api";
import { formatCount, formatPercent, statusLabel } from "@/lib/format";
import {
  AppShell,
  EmptyState,
  ErrorBanner,
  MetricBlock,
  PageBody,
  Panel,
  PanelHeader,
  StatusPill,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/components/ui/shell";
import { FinalReportViewer } from "@/features/tasks/final-report-viewer";
import { ReportInputPreviewPanel } from "@/features/tasks/report-input-preview-panel";
import { SampleConfirmationPanel } from "@/features/tasks/sample-confirmation-panel";

export type TaskView = "tasks" | "overview" | "sample" | "structure" | "reportInput" | "report";

type LoadState = {
  health: string;
  tasks: AnalysisTask[];
  selectedTaskId: string;
  detail: TaskDetail | null;
  events: TaskEvent[];
  loading: boolean;
  error: string;
};

type TaskWorkspaceProps = {
  activeView: TaskView;
  initialTaskId?: string;
};

const initialState: LoadState = {
  health: "检查中",
  tasks: [],
  selectedTaskId: "",
  detail: null,
  events: [],
  loading: true,
  error: "",
};

const viewLabels: Record<TaskView, string> = {
  tasks: "任务列表",
  overview: "任务详情",
  sample: "样本确认",
  structure: "AI 结构化",
  reportInput: "报告输入",
  report: "最终报告",
};

export function TaskWorkspace({ activeView, initialTaskId = "" }: TaskWorkspaceProps) {
  const [state, setState] = useState<LoadState>(initialState);
  const router = useRouter();
  const pathname = usePathname();

  const load = useCallback(
    async (selectedTaskId?: string) => {
      setState((current) => ({ ...current, loading: true, error: "" }));
      try {
        const [health, tasks] = await Promise.all([getHealth(), listTasks()]);
        const nextTaskId = selectedTaskId || initialTaskId || tasks[0]?.id || "";
        const [detail, events] = nextTaskId
          ? await Promise.all([getTaskDetail(nextTaskId), getTaskEvents(nextTaskId)])
          : [null, []];
        setState({
          health: health.status === "ok" ? "正常" : health.status,
          tasks,
          selectedTaskId: nextTaskId,
          detail,
          events,
          loading: false,
          error: "",
        });
      } catch (error) {
        setState((current) => ({
          ...current,
          loading: false,
          error: error instanceof Error ? error.message : "加载失败",
        }));
      }
    },
    [initialTaskId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const selectedTask = state.detail?.task;
  const shouldPoll = Boolean(state.selectedTaskId && selectedTask?.id.startsWith("task-") && state.detail?.stages.some((stage) => stage.status === "running"));

  useEffect(() => {
    if (!shouldPoll) {
      return;
    }
    const timer = window.setInterval(() => {
      void load(state.selectedTaskId);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [load, shouldPoll, state.selectedTaskId]);

  const chartData = useMemo(() => {
    const counts = state.detail?.match_status_counts ?? {};
    return Object.entries(counts).map(([name, count]) => ({ name: matchStatusLabel(name), count }));
  }, [state.detail]);

  function selectTask(taskId: string) {
    const destination = activeView === "tasks" ? `/tasks/${taskId}` : routeFor(taskId, activeView);
    router.push(destination);
  }

  return (
    <AppShell
      actions={
        <>
          <StatusPill label="后端" value={state.health} />
          <button className={secondaryButtonClass} onClick={() => void load(state.selectedTaskId)} type="button">
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        </>
      }
      title={viewLabels[activeView]}
    >
      <PageBody className="grid gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <Panel className="overflow-hidden">
            <PanelHeader title="已验证任务" />
            <div className="divide-y divide-[#e8ecf2]">
              {state.tasks.map((task) => (
                <button
                  aria-pressed={task.id === state.selectedTaskId}
                  className={[
                    "block w-full px-4 py-4 text-left transition",
                    task.id === state.selectedTaskId ? "bg-[#eef6f4]" : "bg-white hover:bg-[#f8fafc]",
                  ].join(" ")}
                  key={task.id}
                  onClick={() => selectTask(task.id)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{task.task_name}</p>
                      <p className="mt-1 text-xs text-[#647086]">
                        {cityLabel(task.city)} / {keywordLabel(task.keyword)} / {jobTypeLabel(task.job_type)}
                      </p>
                    </div>
                    <span className="rounded-full bg-[#e6f0ff] px-2 py-1 text-xs font-medium text-[#2364aa]">
                      {statusLabel(task.status)}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[#647086]">
                    <span>岗位 {formatCount(task.collected_count)}</span>
                    <span>样本 {formatCount(task.analysis_ready_count)}</span>
                    <span>运行 {task.search_run_id}</span>
                    <span>批量 {task.batch_size}</span>
                  </div>
                </button>
              ))}
            </div>
          </Panel>

          {selectedTask ? <TaskNav taskId={selectedTask.id} pathname={pathname} /> : null}
        </aside>

        <section className="space-y-5">
          <ErrorBanner message={state.error} />

          {selectedTask ? (
            <>
              <TaskSummary detail={state.detail} />
              {activeView === "overview" ? <TaskDetailHome chartData={chartData} detail={state.detail} events={state.events} onTaskChanged={() => void load(selectedTask.id)} /> : null}
              {activeView === "tasks" ? <TaskDetailHome chartData={chartData} detail={state.detail} events={state.events} onTaskChanged={() => void load(selectedTask.id)} /> : null}
              {activeView === "sample" ? <SampleConfirmationPanel onTaskChanged={() => void load(selectedTask.id)} task={selectedTask} /> : null}
              {activeView === "structure" ? <StructuringPanel onTaskChanged={() => void load(selectedTask.id)} task={selectedTask} /> : null}
              {activeView === "reportInput" ? <ReportInputPreviewPanel task={selectedTask} /> : null}
              {activeView === "report" ? <FinalReportViewer task={selectedTask} /> : null}
            </>
          ) : (
            <EmptyState message={state.loading ? "正在加载任务..." : "暂无任务"} />
          )}
        </section>
      </PageBody>
    </AppShell>
  );
}

function TaskSummary({ detail }: { detail: TaskDetail | null }) {
  const task = detail?.task;
  if (!task) {
    return null;
  }
  return (
    <Panel className="p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-medium text-[#647086]">当前任务</p>
          <h2 className="mt-1 text-xl font-semibold">{task.task_name}</h2>
          <p className="mt-2 max-w-3xl break-words text-sm leading-6 text-[#647086]">{task.source_type}</p>
        </div>
        <span className="inline-flex h-8 items-center rounded-full bg-[#e8f7f2] px-3 text-sm font-medium text-[#2f9f7f]">
          {statusLabel(task.status)}
        </span>
      </div>

      <div className="mt-5 grid gap-4 border-t border-[#e8ecf2] pt-5 sm:grid-cols-2 xl:grid-cols-4">
        <MetricBlock icon={<Database className="h-4 w-4" />} label="采集岗位" value={formatCount(task.collected_count)} />
        <MetricBlock icon={<CheckCircle2 className="h-4 w-4" />} label="入选样本" value={formatCount(task.analysis_ready_count)} />
        <MetricBlock icon={<Activity className="h-4 w-4" />} label="样本占比" value={formatPercent(task.analysis_ready_count, task.collected_count)} />
        <MetricBlock icon={<FileText className="h-4 w-4" />} label="报告状态" value={detail?.artifact_paths.report ? "可查看" : "未生成"} />
      </div>
    </Panel>
  );
}

function TaskDetailHome({ detail, events, chartData, onTaskChanged }: { detail: TaskDetail | null; events: TaskEvent[]; chartData: Array<{ name: string; count: number }>; onTaskChanged: () => void }) {
  const task = detail?.task;
  if (!task) {
    return null;
  }
  return (
    <>
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <StageTimeline detail={detail} />
        <NextActionPanel detail={detail} onDone={onTaskChanged} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <ArtifactPanel taskId={task.id} artifactPaths={detail?.artifact_paths ?? {}} />
        <MatchDistributionPanel chartData={chartData} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <EventPanel events={events} />
        <TaskMetaPanel task={task} />
      </section>
    </>
  );
}

function StageTimeline({ detail }: { detail: TaskDetail | null }) {
  return (
    <Panel className="p-5">
      <h3 className="text-base font-semibold">阶段进度</h3>
      <div className="mt-4 space-y-3">
        {detail?.stages.map((stage, index) => (
          <div className="flex gap-3" key={stage.stage_name}>
            <div className="flex w-8 flex-col items-center">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#e8f7f2] text-sm font-semibold text-[#2f9f7f]">
                {index + 1}
              </span>
              {index + 1 < (detail?.stages.length ?? 0) ? <span className="mt-2 h-full w-px bg-[#e8ecf2]" /> : null}
            </div>
            <div className="min-w-0 flex-1 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold">{stageNameLabel(stage.stage_name)}</p>
                <span className="rounded-full bg-[#f1f5f9] px-2 py-0.5 text-xs text-[#647086]">{statusLabel(stage.status)}</span>
              </div>
              <p className="mt-1 break-words text-sm leading-6 text-[#647086]">{stage.message}</p>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function NextActionPanel({ detail, onDone }: { detail: TaskDetail | null; onDone: () => void }) {
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const task = detail?.task;
  const stages = detail?.stages ?? [];
  const live = Boolean(task?.id.startsWith("task-"));
  const stageMap = Object.fromEntries(stages.map((stage) => [stage.stage_name, stage.status]));
  const running = stages.some((stage) => stage.status === "running");
  const next = task ? nextActionFor(stageMap) : null;

  async function runAction(action: string) {
    if (!task) {
      return;
    }
    setBusyAction(action);
    setError("");
    try {
      if (action === "start-collection") await startCollection(task.id);
      if (action === "start-scoring") await startScoring(task.id);
      if (action === "start-structuring") await startStructuring(task.id);
      if (action === "run-structuring-batches") await runStructuringBatches(task.id);
      if (action === "build-report-input") await buildReportInput(task.id);
      if (action === "write-final-report") await writeFinalReport(task.id);
      onDone();
    } catch (error) {
      setError(error instanceof Error ? error.message : "动作执行失败");
    } finally {
      setBusyAction("");
    }
  }

  const secondaryLinks = task
    ? [
        { href: `/tasks/${task.id}/sample`, label: "样本", enabled: stageMap.score_jobs === "completed" },
        { href: `/tasks/${task.id}/structure`, label: "结构化", enabled: stageMap.confirm_sample === "completed" || stageMap.ai_structuring !== "pending" },
        { href: `/tasks/${task.id}/report-input`, label: "报告输入", enabled: Boolean(detail?.artifact_paths.report_input) },
        { href: `/tasks/${task.id}/report`, label: "最终报告", enabled: Boolean(detail?.artifact_paths.report) },
      ]
    : [];

  return (
    <Panel className="p-5">
      <h3 className="text-base font-semibold">下一步动作</h3>
      {!live ? <p className="mt-2 text-sm leading-6 text-[#647086]">样本任务为只读预览；live 任务会在这里显示可执行按钮。</p> : null}
      {live && running ? <p className="mt-2 text-sm leading-6 text-[#647086]">当前有阶段运行中，页面会自动刷新状态和事件。</p> : null}
      {live && !running && next ? <p className="mt-2 text-sm leading-6 text-[#647086]">当前可继续：{next.description}</p> : null}
      {live && !running && !next ? <p className="mt-2 text-sm leading-6 text-[#647086]">当前没有可直接执行的后台动作，请查看阶段状态或产物入口。</p> : null}
      {error ? <div className="mt-3"><ErrorBanner message={error} /></div> : null}
      <div className="mt-4 space-y-3">
        {live && next ? (
          next.href ? (
            <Link className="flex items-start gap-3 rounded-md border border-[#2364aa] bg-[#f4f8ff] px-4 py-3 transition hover:bg-[#eef6ff]" href={next.href === "sample" && task ? `/tasks/${task.id}/sample` : next.href ?? "#"}>
              <Rows3 className="mt-0.5 h-4 w-4 text-[#2364aa]" />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold">{next.label}</span>
                <span className="mt-1 block text-xs leading-5 text-[#647086]">{next.description}</span>
              </span>
              <ArrowRight className="h-4 w-4 text-[#647086]" />
            </Link>
          ) : (
            <button
              className="flex w-full items-start gap-3 rounded-md border border-[#2364aa] bg-[#f4f8ff] px-4 py-3 text-left transition hover:bg-[#eef6ff] disabled:cursor-not-allowed disabled:border-[#d9dee8] disabled:bg-[#f8fafc]"
              disabled={Boolean(busyAction) || running}
              onClick={() => void runAction(next.action)}
              type="button"
            >
              <Play className="mt-0.5 h-4 w-4 text-[#2364aa]" />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold">{busyAction ? "处理中" : next.label}</span>
                <span className="mt-1 block text-xs leading-5 text-[#647086]">{next.description}</span>
              </span>
            </button>
          )
        ) : null}

        {secondaryLinks.map((link) => (
          <Link
            className={["flex items-center justify-between gap-3 rounded-md border px-4 py-3 text-sm transition", link.enabled ? "border-[#e8ecf2] bg-white hover:bg-[#fbfcfe]" : "pointer-events-none border-[#eef1f5] bg-[#f8fafc] text-[#9aa4b4]"].join(" ")}
            href={link.href}
            key={link.href}
          >
            <span>{link.label}</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        ))}
      </div>
    </Panel>
  );
}

type NextAction = {
  action: string;
  label: string;
  description: string;
  href?: string;
};

function nextActionFor(stageMap: Record<string, string>): NextAction | null {
  if (stageMap.collect_jobs === "pending") return { action: "start-collection", label: "开始采集", description: "启动岗位采集执行器，接口会立即返回并进入后台运行。" };
  if (stageMap.collect_jobs === "completed" && stageMap.score_jobs === "pending") return { action: "start-scoring", label: "开始本地评分", description: "对采集结果进行本地匹配评分，不涉及模型工作。" };
  if (stageMap.score_jobs === "completed" && stageMap.confirm_sample === "pending") return { action: "save-sample", label: "确认岗位样本", description: "进入样本页选择岗位并保存样本版本。", href: "sample" };
  if (stageMap.confirm_sample === "completed" && stageMap.ai_structuring === "pending") return { action: "start-structuring", label: "生成结构化批次", description: "基于确认样本创建待处理批次，不进行模型工作。" };
  if (stageMap.ai_structuring === "waiting_for_user") return { action: "run-structuring-batches", label: "执行结构化批次", description: "开始处理已计划的结构化批次。" };
  if (stageMap.ai_structuring === "completed" && stageMap.build_report_input === "pending") return { action: "build-report-input", label: "生成报告输入", description: "汇总结构化结果并生成最终报告输入。" };
  if (stageMap.build_report_input === "completed" && stageMap.write_final_report === "pending") return { action: "write-final-report", label: "生成最终报告", description: "根据报告输入生成最终报告。" };
  return null;
}
function ArtifactPanel({ taskId, artifactPaths }: { taskId: string; artifactPaths: Record<string, string> }) {
  const artifacts = [
    { key: "report_input", label: "报告输入", href: `/tasks/${taskId}/report-input`, icon: FileJson },
    { key: "report", label: "最终报告", href: `/tasks/${taskId}/report`, icon: FileText },
    { key: "timing", label: "时间记录", href: `/tasks/${taskId}`, icon: Clock3 },
  ];
  return (
    <Panel className="p-5">
      <h3 className="text-base font-semibold">产物入口</h3>
      <div className="mt-4 space-y-3">
        {artifacts.map((artifact) => {
          const Icon = artifact.icon;
          const path = artifactPaths[artifact.key] || "";
          return (
            <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3" key={artifact.key}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <Icon className="h-4 w-4 text-[#2364aa]" />
                  <span className="text-sm font-semibold">{artifact.label}</span>
                </div>
                {path ? <Link className="text-sm font-medium text-[#2364aa]" href={artifact.href}>打开</Link> : <span className="text-xs text-[#647086]">暂无</span>}
              </div>
              <p className="mt-2 break-words text-xs leading-5 text-[#647086]">{path || "当前 fixture 未提供该产物。"}</p>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function MatchDistributionPanel({ chartData }: { chartData: Array<{ name: string; count: number }> }) {
  return (
    <Panel className="p-5">
      <h3 className="text-base font-semibold">匹配分布</h3>
      <div className="mt-4 h-64">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={chartData} margin={{ left: -24, right: 8, top: 8 }}>
            <CartesianGrid stroke="#e8ecf2" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" fill="#2364aa" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function EventPanel({ events }: { events: TaskEvent[] }) {
  return (
    <Panel className="p-5">
      <h3 className="text-base font-semibold">事件记录</h3>
      <div className="mt-4 space-y-3">
        {events.length === 0 ? <p className="text-sm text-[#647086]">暂无事件记录</p> : null}
        {events.map((event) => (
          <div className="rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3" key={event.id}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-[#e6f0ff] px-2 py-0.5 text-xs font-medium text-[#2364aa]">{eventTypeLabel(event.event_type)}</span>
              <span className="text-xs text-[#647086]">{event.created_at || "fixture"}</span>
            </div>
            <p className="mt-2 break-words text-sm leading-6 text-[#647086]">{event.message}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function TaskMetaPanel({ task }: { task: AnalysisTask }) {
  const rows = [
    ["城市", cityLabel(task.city)],
    ["城市编码", task.city_code || "-"],
    ["岗位关键词", keywordLabel(task.keyword)],
    ["求职类型", jobTypeLabel(task.job_type)],
    ["预期岗位数", formatCount(task.expected_job_count)],
    ["AI 批大小", formatCount(task.batch_size)],
    ["运行编号", String(task.search_run_id)],
    ["创建时间", task.created_at || "-"],
    ["更新时间", task.updated_at || "-"],
  ];
  return (
    <Panel className="p-5">
      <h3 className="text-base font-semibold">任务元信息</h3>
      <dl className="mt-4 grid gap-3 text-sm">
        {rows.map(([label, value]) => (
          <div className="grid grid-cols-[90px_minmax(0,1fr)] gap-3" key={label}>
            <dt className="text-[#647086]">{label}</dt>
            <dd className="break-words font-medium text-[#172033]">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

function TaskNav({ taskId, pathname }: { taskId: string; pathname: string }) {
  const items = [
    { href: `/tasks/${taskId}`, label: "任务详情", icon: ListChecks },
    { href: `/tasks/${taskId}/sample`, label: "样本确认", icon: Rows3 },
    { href: `/tasks/${taskId}/structure`, label: "AI 结构化", icon: Settings2 },
    { href: `/tasks/${taskId}/report-input`, label: "报告输入", icon: FileJson },
    { href: `/tasks/${taskId}/report`, label: "最终报告", icon: BarChart3 },
  ];
  return (
    <nav className="rounded-lg border border-[#d9dee8] bg-white p-2 shadow-[0_6px_18px_rgba(23,32,51,0.06)]">
      {items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            className={[
              "flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium transition",
              active ? "bg-[#e6f0ff] text-[#2364aa]" : "text-[#647086] hover:bg-[#f8fafc] hover:text-[#172033]",
            ].join(" ")}
            aria-current={active ? "page" : undefined}
            href={item.href}
            key={item.href}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

function StructuringPanel({ task, onTaskChanged }: { task: AnalysisTask; onTaskChanged: () => void }) {
  const [status, setStatus] = useState<StructuringStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const live = task.id.startsWith("task-");

  const loadStatus = useCallback(async () => {
    if (!live) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload = await getStructuringStatus(task.id);
      setStatus(payload);
    } catch (error) {
      setError(error instanceof Error ? error.message : "结构化状态加载失败");
    } finally {
      setLoading(false);
    }
  }, [live, task.id]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadStatus]);

  const stageCounts = useMemo(() => {
    return (status?.batches ?? []).reduce<Record<string, number>>((acc, batch) => {
      acc[batch.status] = (acc[batch.status] ?? 0) + 1;
      return acc;
    }, {});
  }, [status]);

  async function run(action: "start" | "run") {
    setBusyAction(action);
    setError("");
    try {
      if (action === "start") await startStructuring(task.id);
      if (action === "run") await runStructuringBatches(task.id);
      await loadStatus();
      onTaskChanged();
    } catch (error) {
      setError(error instanceof Error ? error.message : "结构化动作失败");
    } finally {
      setBusyAction("");
    }
  }

  if (!live) {
    return <RoutePlaceholder title="AI 结构化" description="样本任务为只读预览；live 任务会在这里展示批次状态。" api="GET /api/tasks/{task_id}/structure" />;
  }

  return (
    <section className="space-y-5">
      <Panel className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium text-[#2364aa]">AI 结构化</p>
            <h2 className="mt-1 text-xl font-semibold">批次状态</h2>
            <p className="mt-2 text-sm leading-6 text-[#647086]">先生成批次计划，再手动执行批次处理。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className={secondaryButtonClass} onClick={() => void loadStatus()} type="button">
              <RefreshCw className="h-4 w-4" />
              刷新
            </button>
            <button className={secondaryButtonClass} disabled={Boolean(busyAction)} onClick={() => void run("start")} type="button">
              <Settings2 className="h-4 w-4" />
              {busyAction === "start" ? "处理中" : "生成批次"}
            </button>
            <button className={primaryButtonClass} disabled={Boolean(busyAction) || !status?.batches.length} onClick={() => void run("run")} type="button">
              <Play className="h-4 w-4" />
              {busyAction === "run" ? "处理中" : "执行批次"}
            </button>
          </div>
        </div>

        {error ? <div className="mt-4"><ErrorBanner message={error} /></div> : null}

        <div className="mt-5 grid gap-4 border-t border-[#e8ecf2] pt-5 sm:grid-cols-2 xl:grid-cols-4">
          <MetricBlock icon={<Rows3 className="h-4 w-4" />} label="样本版本" value={status?.sample_version ? String(status.sample_version) : "-"} />
          <MetricBlock icon={<CheckCircle2 className="h-4 w-4" />} label="入选岗位" value={formatCount(status?.selected_count ?? 0)} />
          <MetricBlock icon={<ListChecks className="h-4 w-4" />} label="批次数" value={formatCount(status?.total_batches ?? 0)} />
          <MetricBlock icon={<Activity className="h-4 w-4" />} label="已完成" value={formatCount(stageCounts.completed ?? 0)} />
        </div>
      </Panel>

      <Panel className="overflow-hidden">
        <PanelHeader
          description="批次计划生成后会显示每批岗位、处理状态、用量和费用估算。"
          title="批次列表"
        />
        <div className="overflow-x-auto">
          <table aria-label="结构化批次列表" className="w-full min-w-[900px] border-collapse text-sm">
            <thead className="bg-[#f8fafc] text-left text-xs font-semibold text-[#647086]">
              <tr>
                <th className="px-5 py-3" scope="col">批次</th>
                <th className="px-4 py-3" scope="col">状态</th>
                <th className="px-4 py-3" scope="col">岗位</th>
                <th className="px-4 py-3" scope="col">模型</th>
                <th className="px-4 py-3" scope="col">输入</th>
                <th className="px-4 py-3" scope="col">输出</th>
                <th className="px-4 py-3" scope="col">费用</th>
                <th className="px-5 py-3" scope="col">错误</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e8ecf2]">
              {loading ? <BatchTableMessage message="正在加载批次..." /> : null}
              {!loading && !status?.batches.length ? <BatchTableMessage message="暂无批次" /> : null}
              {!loading
                ? status?.batches.map((batch) => (
                    <tr className="bg-white align-top hover:bg-[#fbfcfe]" key={batch.batch_id}>
                      <td className="px-5 py-4 font-semibold">#{batch.batch_index}</td>
                      <td className="px-4 py-4">{statusLabel(batch.status)}</td>
                      <td className="max-w-[220px] break-words px-4 py-4">{batch.job_ids.join(", ") || "-"}</td>
                      <td className="px-4 py-4">{batch.model_name || "-"}</td>
                      <td className="px-4 py-4">{formatCount(batch.input_tokens)}</td>
                      <td className="px-4 py-4">{formatCount(batch.output_tokens)}</td>
                      <td className="px-4 py-4">{batch.estimated_cny ? batch.estimated_cny.toFixed(4) : "-"}</td>
                      <td className="max-w-[240px] break-words px-5 py-4 text-[#647086]">{batch.error_message || "-"}</td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>
      </Panel>
    </section>
  );
}

function BatchTableMessage({ message }: { message: string }) {
  return (
    <tr>
      <td className="px-5 py-8 text-center text-[#647086]" colSpan={8}>{message}</td>
    </tr>
  );
}

function RoutePlaceholder({ title, description, api }: { title: string; description: string; api: string }) {
  return (
    <Panel className="p-5">
      <p className="text-sm font-medium text-[#2364aa]">页面骨架已建立</p>
      <h3 className="mt-1 text-lg font-semibold">{title}</h3>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[#647086]">{description}</p>
      <div className="mt-4 rounded-md border border-[#e8ecf2] bg-[#fbfcfe] px-4 py-3 text-sm text-[#647086]">
        数据接口：<span className="font-medium text-[#172033]">{api}</span>
      </div>
    </Panel>
  );
}

function routeFor(taskId: string, view: TaskView) {
  const routes: Record<TaskView, string> = {
    tasks: "/tasks",
    overview: `/tasks/${taskId}`,
    sample: `/tasks/${taskId}/sample`,
    structure: `/tasks/${taskId}/structure`,
    reportInput: `/tasks/${taskId}/report-input`,
    report: `/tasks/${taskId}/report`,
  };
  return routes[view];
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

function stageNameLabel(value: string) {
  const labels: Record<string, string> = {
    collect_jobs: "采集岗位",
    score_jobs: "本地评分",
    confirm_sample: "确认样本",
    ai_structuring: "AI 结构化",
    build_report_input: "生成报告输入",
    write_final_report: "生成最终报告",
  };
  return labels[value] ?? value;
}

function matchStatusLabel(value: string) {
  const labels: Record<string, string> = {
    strong_match: "强匹配",
    review: "待复核",
    weak_match: "弱匹配",
  };
  return labels[value] ?? value;
}

function eventTypeLabel(value: string) {
  const labels: Record<string, string> = {
    fixture_bound: "绑定样本",
    report_input_ready: "报告输入就绪",
    report_ready: "最终报告就绪",
    timing_ready: "时间记录就绪",
  };
  return labels[value] ?? value;
}



