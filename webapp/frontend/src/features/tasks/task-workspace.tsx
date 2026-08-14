"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import type { ReactNode } from "react";
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
  Square,
  Rows3,
  Settings2,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  buildReportInput,
  cancelTask,
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
  type TaskStageRun,
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
  const [autoScoring, setAutoScoring] = useState(false);
  const [autoScoreAttemptedTaskId, setAutoScoreAttemptedTaskId] = useState("");
  const [autoFlowError, setAutoFlowError] = useState("");
  const [autoAnalysisAction, setAutoAnalysisAction] = useState("");
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
  const selectedStageMap = useMemo(() => Object.fromEntries(state.detail?.stages.map((stage) => [stage.stage_name, stage.status]) ?? []), [state.detail]);
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
  useEffect(() => {
    const detail = state.detail;
    const task = detail?.task;
    if (!detail || !task?.id.startsWith("task-") || activeView !== "overview" || autoScoring || autoScoreAttemptedTaskId === task.id) {
      return;
    }
    const stageMap = Object.fromEntries(detail.stages.map((stage) => [stage.stage_name, stage.status]));
    if (stageMap.collect_jobs !== "completed" || stageMap.score_jobs !== "pending") {
      return;
    }
    setAutoScoring(true);
    setAutoScoreAttemptedTaskId(task.id);
    setAutoFlowError("");
    void startScoring(task.id)
      .then(() => load(task.id))
      .catch((error) => {
        setAutoFlowError(error instanceof Error ? error.message : "本地评分启动失败");
      })
      .finally(() => setAutoScoring(false));
  }, [activeView, autoScoreAttemptedTaskId, autoScoring, load, router, state.detail]);

  useEffect(() => {
    const detail = state.detail;
    const task = detail?.task;
    if (!detail || !task?.id.startsWith("task-") || activeView !== "structure" || autoAnalysisAction) {
      return;
    }
    const storageKey = `jobuwant:auto-analysis:${task.id}`;
    if (window.sessionStorage.getItem(storageKey) !== "1") {
      return;
    }
    const stageMap = Object.fromEntries(detail.stages.map((stage) => [stage.stage_name, stage.status]));
    const failedStage = detail.stages.find((stage) => stage.status === "failed" || stage.status === "canceled");
    if (failedStage) {
      window.sessionStorage.removeItem(storageKey);
      setAutoFlowError(`${stageNameLabel(failedStage.stage_name)}未完成，请查看阶段状态。`);
      return;
    }
    if (detail.artifact_paths.report || stageMap.write_final_report === "completed") {
      window.sessionStorage.removeItem(storageKey);
      router.push(`/tasks/${task.id}/report`);
      return;
    }
    async function runNextStep() {
      if (!task) {
        return;
      }
      try {
        if (stageMap.ai_structuring === "waiting_for_user") {
          setAutoAnalysisAction("执行结构化批次");
          await runStructuringBatches(task.id);
        } else if (stageMap.ai_structuring === "completed" && stageMap.build_report_input === "pending") {
          setAutoAnalysisAction("生成报告输入");
          await buildReportInput(task.id);
        } else if (stageMap.build_report_input === "completed" && stageMap.write_final_report === "pending") {
          setAutoAnalysisAction("生成最终报告");
          await writeFinalReport(task.id);
        } else {
          return;
        }
        await load(task.id);
      } catch (error) {
        setAutoFlowError(error instanceof Error ? error.message : "分析流程推进失败");
      } finally {
        setAutoAnalysisAction("");
      }
    }
    void runNextStep();
  }, [activeView, autoAnalysisAction, load, router, state.detail]);
  const chartData = useMemo(() => {
    const counts = state.detail?.match_status_counts ?? {};
    return Object.entries(counts).map(([name, count]) => ({ name: matchStatusLabel(name), count }));
  }, [state.detail]);

  function selectTask(taskId: string) {
    const destination = activeView === "tasks" ? `/tasks/${taskId}` : routeFor(taskId, activeView);
    router.push(destination);
  }

  const livePrimaryFlow = Boolean(selectedTask?.id.startsWith("task-") && (activeView === "overview" || activeView === "sample"));
  const liveAnalysisFlow = Boolean(selectedTask?.id.startsWith("task-") && activeView === "structure");
  const liveReportFlow = Boolean(selectedTask?.id.startsWith("task-") && activeView === "report");

  if (livePrimaryFlow) {
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
        title="查找岗位"
      >
        <PageBody className="space-y-5 py-5">
          <ErrorBanner message={state.error || autoFlowError} />
          {selectedTask ? (
            <LiveFindFlowPage
              autoScoring={autoScoring}
              detail={state.detail}
              events={state.events}
              onTaskChanged={() => void load(selectedTask.id)}
            />
          ) : (
            <EmptyState message={state.loading ? "正在加载任务..." : "暂无任务"} />
          )}
        </PageBody>
      </AppShell>
    );
  }

  if (liveAnalysisFlow) {
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
        title="分析岗位"
      >
        <PageBody className="space-y-5 py-5">
          <ErrorBanner message={state.error || autoFlowError} />
          {autoAnalysisAction ? (
            <Panel className="border-[#b9d3f2] bg-[#f4f8ff] px-4 py-3 text-sm text-[#2364aa]">
              正在{autoAnalysisAction}，页面会自动刷新并在完成后打开最终报告。
            </Panel>
          ) : null}
          {selectedTask ? (
            <LiveAnalysisFlowPage
              autoAnalysisAction={autoAnalysisAction}
              detail={state.detail}
              events={state.events}
              onTaskChanged={() => void load(selectedTask.id)}
            />
          ) : (
            <EmptyState message={state.loading ? "正在加载任务..." : "暂无任务"} />
          )}
        </PageBody>
      </AppShell>
    );
  }

  if (liveReportFlow) {
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
        title="岗位分析报告"
      >
        <PageBody className="space-y-5 py-5">
          <ErrorBanner message={state.error || autoFlowError} />
          {selectedTask ? <FinalReportViewer task={selectedTask} /> : <EmptyState message={state.loading ? "正在加载任务..." : "暂无任务"} />}
        </PageBody>
      </AppShell>
    );
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
          <ErrorBanner message={state.error || autoFlowError} />
          {autoAnalysisAction ? (
            <Panel className="border-[#b9d3f2] bg-[#f4f8ff] px-4 py-3 text-sm text-[#2364aa]">
              正在{autoAnalysisAction}，页面会自动刷新并在完成后打开最终报告。
            </Panel>
          ) : null}

          {selectedTask ? (
            <>
              <TaskSummary detail={state.detail} />
              {activeView === "overview" ? <TaskDetailHome autoScoring={autoScoring} chartData={chartData} detail={state.detail} events={state.events} onTaskChanged={() => void load(selectedTask.id)} /> : null}
              {activeView === "tasks" ? <TaskDetailHome autoScoring={autoScoring} chartData={chartData} detail={state.detail} events={state.events} onTaskChanged={() => void load(selectedTask.id)} /> : null}
              {activeView === "sample" ? <SampleConfirmationPanel onTaskChanged={() => void load(selectedTask.id)} sampleConfirmed={selectedStageMap.confirm_sample === "completed"} task={selectedTask} /> : null}
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

function LiveFindFlowPage({ detail, events, autoScoring, onTaskChanged }: { detail: TaskDetail | null; events: TaskEvent[]; autoScoring: boolean; onTaskChanged: () => void }) {
  const [canceling, setCanceling] = useState(false);
  const [error, setError] = useState("");
  const task = detail?.task;
  if (!task) {
    return null;
  }

  const taskId = task.id;
  const metrics = detail?.metrics;
  const stages = detail?.stages ?? [];
  const stageMap = Object.fromEntries(stages.map((stage) => [stage.stage_name, stage.status]));
  const collecting = stageMap.collect_jobs === "running";
  const scoring = stageMap.collect_jobs === "completed" && stageMap.score_jobs === "pending";
  const running = stages.some((stage) => stage.status === "running") || autoScoring;
  const resultReady = stageMap.score_jobs === "completed";
  const canceled = task.status === "canceled" || stages.some((stage) => stage.status === "canceled");
  const failed = task.status === "failed" || stages.some((stage) => stage.status === "failed");
  const failedStage = stages.find((stage) => stage.status === "failed");
  const elapsedSeconds = stages
    .filter((stage) => stage.stage_name === "collect_jobs" || stage.stage_name === "score_jobs")
    .reduce((sum, stage) => sum + stage.elapsed_seconds, 0);
  const sampleConfirmed = stageMap.confirm_sample === "completed";
  const loginEvent = latestCollectionLoginEvent(events);
  const preparingLogin = collecting && !loginEvent && !resultReady && !canceled && !failed;
  const waitingForLogin = Boolean(loginEvent && ["collection_login_opening", "collection_login_checking", "collection_login_required", "collection_login_waiting"].includes(loginEvent.event_type) && !resultReady && !canceled && !failed);
  const loginTimedOut = Boolean(loginEvent?.event_type === "collection_login_timeout");
  const phase = findPhase({ resultReady, canceled, failed, loginTimedOut, preparingLogin, waitingForLogin, scoring: scoring || autoScoring, collecting });
  const statusTitle = findStatusTitle({ resultReady, canceled, failed, loginTimedOut, preparingLogin, waitingForLogin, scoring: scoring || autoScoring, collecting }, loginEvent);
  const statusDescription = findStatusDescription({ resultReady, canceled, failed, loginTimedOut, preparingLogin, waitingForLogin, scoring: scoring || autoScoring, collecting }, loginEvent, failedStage);

  async function cancelCurrentTask() {
    setCanceling(true);
    setError("");
    try {
      await cancelTask(taskId);
      onTaskChanged();
    } catch (error) {
      setError(error instanceof Error ? error.message : "中断失败");
    } finally {
      setCanceling(false);
    }
  }

  return (
    <section className="space-y-5">
      <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 p-4 shadow-[0_24px_74px_rgba(14,23,38,0.13),inset_0_1px_0_rgba(255,255,255,0.98)] backdrop-blur">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <FindStatusBadge phase={phase} />
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
              <h2 className="max-w-full flex-none truncate text-3xl font-bold tracking-normal text-[#0b1220]">{task.task_name}</h2>
              <div className="flex max-w-full flex-none flex-wrap items-center gap-2 text-sm">
                <FindQueryChip label="城市" value={cityLabel(task.city)} />
                <FindQueryChip label="岗位" value={keywordLabel(task.keyword)} />
                <FindQueryChip label="类型" value={jobTypeLabel(task.job_type)} />
                <FindQueryChip label="目标" value={`${formatCount(task.expected_job_count)} 条`} />
              </div>
            </div>
          </div>
          {!resultReady && !canceled && !failed ? (
            <button
              className="inline-flex h-11 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-[18px] border border-[#f0b8b8] bg-[#fff7f7] px-4 text-sm font-bold text-[#b42318] shadow-[inset_0_1px_0_rgba(255,255,255,0.95)] transition hover:-translate-y-0.5 hover:bg-[#fff1f1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f0b8b8] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
              disabled={!running || canceling}
              onClick={() => void cancelCurrentTask()}
              type="button"
            >
              <Square className="h-4 w-4" />
              {canceling ? "正在中断" : "中断查找"}
            </button>
          ) : null}
        </div>

        {error ? <div className="mt-4"><ErrorBanner message={error} /></div> : null}

        <div className="mt-5 grid gap-2 border-t border-[#edf2f7] pt-4 sm:grid-cols-2 xl:grid-cols-4">
          <FindMetricPill icon={<Clock3 className="h-4 w-4" />} label="查找用时" value={metrics?.collection_seconds ? formatDuration(metrics.collection_seconds) : elapsedSeconds ? formatDuration(elapsedSeconds) : running ? "进行中" : "-"} />
          <FindMetricPill icon={<Database className="h-4 w-4" />} label="岗位数量" value={formatCount(task.collected_count)} />
          <FindMetricPill icon={<CheckCircle2 className="h-4 w-4" />} label="入选数量" value={formatCount(task.analysis_ready_count)} />
          <FindMetricPill icon={<BarChart3 className="h-4 w-4" />} label="平均匹配分" value={formatMetricScore(metrics?.average_match_score)} />
        </div>
      </section>

      {!resultReady ? (
        <EventPanel description={statusDescription} events={events} phase={phase} title={statusTitle} />
      ) : (
        <SampleConfirmationPanel onTaskChanged={onTaskChanged} sampleConfirmed={sampleConfirmed} task={task} />
      )}
    </section>
  );
}

type FindPhase = "opening" | "login" | "collecting" | "scoring" | "done" | "canceled" | "failed";

function findPhase(state: { resultReady: boolean; canceled: boolean; failed: boolean; loginTimedOut: boolean; preparingLogin: boolean; waitingForLogin: boolean; scoring: boolean; collecting: boolean }): FindPhase {
  if (state.resultReady) return "done";
  if (state.canceled) return "canceled";
  if (state.failed || state.loginTimedOut) return "failed";
  if (state.preparingLogin) return "opening";
  if (state.waitingForLogin) return "login";
  if (state.scoring) return "scoring";
  if (state.collecting) return "collecting";
  return "opening";
}

function findStatusTitle(state: { resultReady: boolean; canceled: boolean; failed: boolean; loginTimedOut: boolean; preparingLogin: boolean; waitingForLogin: boolean; scoring: boolean; collecting: boolean }, loginEvent?: TaskEvent) {
  if (state.resultReady) return "查找完成";
  if (state.canceled) return "查找已中断";
  if (state.failed) return "查找失败";
  if (state.loginTimedOut) return "登录等待超时";
  if (state.preparingLogin) return "正在打开 BOSS 窗口";
  if (state.waitingForLogin) return loginFlowTitle(loginEvent);
  if (state.scoring) return "正在进行本地评分";
  if (state.collecting) return "正在查找岗位";
  return "等待查找";
}

function findStatusDescription(state: { resultReady: boolean; canceled: boolean; failed: boolean; loginTimedOut: boolean; preparingLogin: boolean; waitingForLogin: boolean; scoring: boolean; collecting: boolean }, loginEvent?: TaskEvent, failedStage?: { message: string }) {
  if (state.resultReady) return "已完成岗位信息收集和本地评分，请确认要保留哪些岗位。";
  if (state.canceled) return "本次查找已中断，未完成结果不会进入后续流程。";
  if (state.failed) return failedStage?.message || "查找没有完成，请查看事件记录后重新开始。";
  if (state.loginTimedOut) return "等待扫码登录超时，请重新开始查找。";
  if (state.preparingLogin || state.waitingForLogin) return loginFlowDescription(loginEvent);
  if (state.scoring) return "岗位信息已返回，正在进行本地匹配评分。";
  if (state.collecting) return "系统正在收集岗位信息，为避免采集过快导致采集失败，请您稍候片刻！\n采集完成后会自动进入本地评分，在此过程中，请勿关闭 BOSS 页面，可以最小化。";
  return "当前任务还没有进入查找阶段。";
}

function FindStatusBadge({ phase }: { phase: FindPhase }) {
  const label = {
    opening: "准备中",
    login: "等待扫码",
    collecting: "正在查找",
    scoring: "本地评分",
    done: "已完成",
    canceled: "已中断",
    failed: "需处理",
  }[phase];
  const className = phase === "failed" || phase === "canceled"
    ? "border-[#f0d3a2] bg-[#fffaf0] text-[#875514]"
    : phase === "done"
      ? "border-[#bfe9dc] bg-[#f1fbf7] text-[#087a67]"
      : "border-[#c8e7e1] bg-[#f2fbf8] text-[#0b7466]";
  return (
    <span className={`${className} inline-flex h-9 items-center gap-2 rounded-[16px] border px-3 text-sm font-bold shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]`}>
      <span className="h-2 w-2 rounded-full bg-current" />
      {label}
    </span>
  );
}

function FindQueryChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex h-9 items-center rounded-[16px] border border-[#d8e1ec] bg-[#f8fafc] px-3 text-sm font-bold text-[#294256] shadow-[inset_0_1px_0_rgba(255,255,255,0.96)]">
      <span className="text-[#607089]">{label}：</span>{value || "-"}
    </span>
  );
}

function FindMetricPill({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex min-h-[70px] items-center gap-3 rounded-[22px] border border-[#d8e1ec] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)]">
      <span className="shrink-0 text-[#0b7466]">{icon}</span>
      <span className="min-w-0">
        <span className="block text-xs font-bold text-[#607089]">{label}</span>
        <span className="mt-1 block truncate text-xl font-bold text-[#0b1220]">{value}</span>
      </span>
    </div>
  );
}

function latestCollectionLoginEvent(events: TaskEvent[]) {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.event_type.startsWith('collection_login_')) {
      return event;
    }
  }
  return undefined;
}

function loginFlowTitle(event?: TaskEvent) {
  if (!event || event.event_type === 'collection_login_opening') {
    return '正在打开 BOSS 窗口';
  }
  if (event.event_type === 'collection_login_checking') {
    return '正在确认登录状态';
  }
  return '等待扫码登录';
}

function loginFlowDescription(event?: TaskEvent) {
  if (!event || event.event_type === 'collection_login_opening' || event.event_type === 'collection_login_checking') {
    return '正在打开 BOSS 窗口；如果出现扫码登录，请完成扫码，系统会自动继续。请勿关闭 BOSS 页面，可以最小化。';
  }
  return '请在弹出的 BOSS 窗口完成扫码登录。登录成功后页面会继续轮询，并自动进入岗位查找。请勿关闭 BOSS 页面，可以最小化。';
}

function LiveAnalysisFlowPage({ detail, events, autoAnalysisAction, onTaskChanged }: { detail: TaskDetail | null; events: TaskEvent[]; autoAnalysisAction: string; onTaskChanged: () => void }) {
  const [canceling, setCanceling] = useState(false);
  const [error, setError] = useState("");
  const task = detail?.task;
  if (!task) {
    return null;
  }

  const taskId = task.id;
  const stages = detail?.stages ?? [];
  const stageMap = Object.fromEntries(stages.map((stage) => [stage.stage_name, stage.status]));
  const running = stages.some((stage) => stage.status === "running") || Boolean(autoAnalysisAction);
  const canceled = task.status === "canceled" || stages.some((stage) => stage.status === "canceled");
  const failed = task.status === "failed" || stages.some((stage) => stage.status === "failed");
  const reportReady = Boolean(detail?.artifact_paths.report) || stageMap.write_final_report === "completed";
  const activeStage = stages.find((stage) => stage.status === "running" || stage.status === "waiting_for_user");
  const elapsedSeconds = stages
    .filter((stage) => stage.stage_name === "ai_structuring" || stage.stage_name === "build_report_input" || stage.stage_name === "write_final_report")
    .reduce((sum, stage) => sum + stage.elapsed_seconds, 0);
  const analysisStages = stages.filter((stage) => stage.stage_name === "ai_structuring" || stage.stage_name === "build_report_input" || stage.stage_name === "write_final_report");
  const analysisPhase = analysisPhaseFor(stageMap, { reportReady, canceled, failed });
  const statusTitle = reportReady ? "分析完成" : canceled ? "分析已中断" : failed ? "分析未完成" : activeStage ? `正在${stageNameLabel(activeStage.stage_name)}` : autoAnalysisAction ? `正在${autoAnalysisAction}` : "正在准备分析";
  const statusDescription = reportReady
    ? "最终报告已生成，可以查看完整分析结果。"
    : canceled
      ? "本次分析已中断，未完成结果不会进入后续流程。"
      : failed
        ? "分析流程未完成，请查看进度和通知后重新处理。"
        : "系统正在把已选岗位样本转成结构化结论，并继续生成报告输入和最终报告。页面会自动刷新。";

  async function cancelCurrentTask() {
    setCanceling(true);
    setError("");
    try {
      await cancelTask(taskId);
      window.sessionStorage.removeItem(`jobuwant:auto-analysis:${taskId}`);
      onTaskChanged();
    } catch (error) {
      setError(error instanceof Error ? error.message : "中断失败");
    } finally {
      setCanceling(false);
    }
  }

  return (
    <section className="space-y-5">
      <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 p-5 shadow-[0_24px_74px_rgba(14,23,38,0.13),inset_0_1px_0_rgba(255,255,255,0.98)] backdrop-blur">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <AnalysisStatusBadge phase={analysisPhase} />
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
              <h2 className="max-w-full flex-none truncate text-3xl font-bold tracking-normal text-[#0b1220]">{task.task_name}</h2>
              <div className="flex max-w-full flex-none flex-wrap items-center gap-2 text-sm">
                <FindQueryChip label="城市" value={cityLabel(task.city)} />
                <FindQueryChip label="岗位" value={keywordLabel(task.keyword)} />
                <FindQueryChip label="类型" value={jobTypeLabel(task.job_type)} />
                <FindQueryChip label="样本" value={`${formatCount(task.analysis_ready_count)} 个`} />
              </div>
            </div>
            <p className="mt-3 max-w-3xl whitespace-pre-line text-sm font-medium leading-6 text-[#607089]">{statusDescription}</p>
          </div>
          {!reportReady && !canceled && !failed ? (
            <button
              className="inline-flex h-11 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-[18px] border border-[#f0b8b8] bg-[#fff7f7] px-4 text-sm font-bold text-[#b42318] shadow-[inset_0_1px_0_rgba(255,255,255,0.95)] transition hover:-translate-y-0.5 hover:bg-[#fff1f1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f0b8b8] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
              disabled={canceling || (!running && stageMap.ai_structuring !== "waiting_for_user")}
              onClick={() => void cancelCurrentTask()}
              type="button"
            >
              <Square className="h-4 w-4" />
              {canceling ? "正在中断" : "中断分析"}
            </button>
          ) : null}
        </div>

        {error ? <div className="mt-4"><ErrorBanner message={error} /></div> : null}

        <AnalysisFlowProgress phase={analysisPhase} title={statusTitle} />

        <div className="mt-5 grid gap-2 border-t border-[#edf2f7] pt-4 sm:grid-cols-2 xl:grid-cols-4">
          <FindMetricPill icon={<Activity className="h-4 w-4" />} label="当前阶段" value={activeStage ? stageNameLabel(activeStage.stage_name) : reportReady ? "最终报告" : "等待中"} />
          <FindMetricPill icon={<Rows3 className="h-4 w-4" />} label="入选岗位" value={formatCount(task.analysis_ready_count)} />
          <FindMetricPill icon={<Clock3 className="h-4 w-4" />} label="分析用时" value={elapsedSeconds ? formatDuration(elapsedSeconds) : running ? "进行中" : "-"} />
          <FindMetricPill icon={<FileText className="h-4 w-4" />} label="报告状态" value={reportReady ? "可查看" : "生成中"} />
        </div>
      </section>

      <StructuringPanel onTaskChanged={onTaskChanged} showActions={false} task={task} />

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <AnalysisStagePanel stages={analysisStages} />
        <EventPanel events={events} />
      </section>

      {reportReady ? (
        <Link className="jobuwant-analysis-report-cta relative inline-flex h-14 w-fit cursor-pointer items-center justify-center gap-2.5 overflow-hidden rounded-[19px] border border-[#8edfd1] bg-[#d4f8ef] px-7 text-base font-black text-[#044b43] shadow-[0_16px_24px_rgba(15,23,42,0.13),0_7px_16px_rgba(32,199,167,0.18),inset_0_1px_0_rgba(255,255,255,1),inset_0_-2px_5px_rgba(15,23,42,0.045)] transition duration-200 hover:-translate-y-1 hover:border-[#20c7a7] hover:shadow-[0_21px_32px_rgba(15,23,42,0.15),0_9px_22px_rgba(32,199,167,0.25),inset_0_1px_0_rgba(255,255,255,1),inset_0_-2px_5px_rgba(15,23,42,0.035)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-2" href={`/tasks/${task.id}/report`}>
          <span className="absolute inset-0 bg-[linear-gradient(110deg,#f4fffb_0%,#d4f8ef_24%,#eafff8_42%,#a9eadb_58%,#e1fff6_74%,#f4fffb_100%)] bg-[length:300%_300%] [animation:jobuwant-live-cta-fill_6.1s_ease-in-out_infinite]" />
          <span className="relative z-10 flex items-center gap-2.5">
            <FileText className="h-4 w-4" />
            查看最终报告
          </span>
        </Link>
      ) : null}
    </section>
  );
}
type AnalysisPhase = "structuring" | "report-input" | "final-report" | "done" | "canceled" | "failed";

function analysisPhaseFor(stageMap: Record<string, string>, flags: { reportReady: boolean; canceled: boolean; failed: boolean }): AnalysisPhase {
  if (flags.reportReady) return "done";
  if (flags.canceled) return "canceled";
  if (flags.failed) return "failed";
  if (stageMap.write_final_report === "running") return "final-report";
  if (stageMap.build_report_input === "running") return "report-input";
  return "structuring";
}

function AnalysisStatusBadge({ phase }: { phase: AnalysisPhase }) {
  const labels: Record<AnalysisPhase, string> = {
    structuring: "正在分析",
    "report-input": "整理输入",
    "final-report": "生成报告",
    done: "分析完成",
    canceled: "已中断",
    failed: "需处理",
  };
  const className = phase === "failed" || phase === "canceled"
    ? "border-[#f0d3a2] bg-[#fffaf0] text-[#875514]"
    : phase === "done"
      ? "border-[#bfe9dc] bg-[#f1fbf7] text-[#087a67]"
      : "border-[#c8e7e1] bg-[#f2fbf8] text-[#0b7466]";
  return (
    <span className={`${className} inline-flex h-9 items-center gap-2 rounded-[16px] border px-3 text-sm font-bold shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]`}>
      <span className="h-2 w-2 rounded-full bg-current" />
      {labels[phase]}
    </span>
  );
}

function AnalysisFlowProgress({ phase, title }: { phase: AnalysisPhase; title: string }) {
  const steps: Array<{ phase: AnalysisPhase; label: string }> = [
    { phase: "structuring", label: "AI 结构化" },
    { phase: "report-input", label: "报告输入" },
    { phase: "final-report", label: "最终报告" },
    { phase: "done", label: "查看报告" },
  ];
  const activeIndex = analysisFlowIndex(phase);
  const progressWidth = `${(Math.max(0, activeIndex) / (steps.length - 1)) * 100}%`;
  const interrupted = phase === "failed" || phase === "canceled";
  const complete = phase === "done";

  return (
    <div className="mt-6 overflow-hidden rounded-[24px] border border-[#dce5ef] bg-[#fbfdff] px-3 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] sm:px-4">
      <div className="overflow-x-auto pb-1">
        <div className="relative mx-auto min-w-[620px] max-w-none px-2 pt-1">
          <div className="absolute left-[10%] right-[10%] top-[28px] h-2 rounded-full bg-[#e7eef6]">
            <div className={["h-full rounded-full transition-all duration-700", interrupted ? "bg-[#e7b96c]" : "bg-[#20c7a7]"].join(" ")} style={{ width: progressWidth }} />
          </div>
          <div className="relative grid grid-cols-4 gap-2">
            {steps.map((step, index) => {
              const active = index === activeIndex;
              const passed = index < activeIndex && !interrupted;
              return <FindFlowStep active={active} interrupted={interrupted && active} key={step.phase} label={step.label} passed={passed} />;
            })}
          </div>
        </div>
      </div>

      <div className="mx-auto mt-6 max-w-2xl pb-6 text-center">
        <span className={["mx-auto inline-flex h-10 min-w-10 items-center justify-center rounded-[16px] px-2", interrupted ? "border border-[#f0d3a2] bg-[#fffaf0] text-[#875514]" : complete ? "border border-[#bfe9dc] bg-[#f1fbf7] text-[#087a67]" : "bg-transparent text-[#13a989]"].join(" ")}>
          {complete ? <CheckCircle2 className="h-5 w-5" /> : interrupted ? <Activity className="h-5 w-5" /> : <LoadingBars />}
        </span>
        <h4 className="mt-3 text-xl font-black text-[#0b1220]">{title}</h4>
        <p className="mt-2 text-sm font-semibold leading-6 text-[#607089]">正在处理样本、提炼要求，并将结果组织成可阅读的岗位分析报告。</p>
      </div>
    </div>
  );
}

function analysisFlowIndex(phase: AnalysisPhase) {
  if (phase === "done") return 3;
  if (phase === "final-report") return 2;
  if (phase === "report-input") return 1;
  if (phase === "failed" || phase === "canceled") return 1;
  return 0;
}

function AnalysisStagePanel({ stages }: { stages: TaskStageRun[] }) {
  return (
    <section className="rounded-[28px] border border-[#d8e1ec] bg-white/95 p-5 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-[#0b1220]">分析进度</h3>
          <p className="mt-1 text-sm font-medium text-[#607089]">聚焦报告生成链路的三个阶段。</p>
        </div>
        <span className="rounded-[16px] border border-[#d8e1ec] bg-[#f8fafc] px-3 py-1.5 text-xs font-bold text-[#607089]">{formatCount(stages.length)} stages</span>
      </div>
      <div className="mt-5 grid gap-3">
        {stages.map((stage) => <AnalysisStageRow key={stage.stage_name} stage={stage} />)}
        {stages.length === 0 ? <p className="rounded-[18px] border border-dashed border-[#d8e1ec] bg-[#f8fafc] px-4 py-5 text-center text-sm font-medium text-[#607089]">暂无分析阶段记录</p> : null}
      </div>
    </section>
  );
}

function AnalysisStageRow({ stage }: { stage: TaskStageRun }) {
  const tone = stageTone(stage.status);
  return (
    <article className="grid gap-3 rounded-[22px] border border-[#e0e7ef] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] transition hover:-translate-y-0.5 hover:border-[#c7d3df] hover:bg-white hover:shadow-[0_14px_30px_rgba(14,23,38,0.08)] sm:grid-cols-[40px_minmax(0,1fr)_auto] sm:items-center">
      <span className={["flex h-10 w-10 items-center justify-center rounded-[16px] border", tone.badge].join(" ")}>{stage.status === "running" ? <LoadingRing /> : stage.status === "completed" ? <CheckCircle2 className="h-5 w-5" /> : <Activity className="h-5 w-5" />}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="text-sm font-bold text-[#0b1220]">{stageNameLabel(stage.stage_name)}</h4>
          <span className={["rounded-full border px-2.5 py-1 text-xs font-bold", tone.pill].join(" ")}>{statusLabel(stage.status)}</span>
        </div>
        <p className="mt-1 break-words text-sm font-medium leading-6 text-[#607089]">{stage.message || analysisStageDescription(stage.stage_name)}</p>
      </div>
      <span className="rounded-full border border-[#d8e1ec] bg-white px-3 py-1.5 text-xs font-bold text-[#607089]">{stage.elapsed_seconds ? formatDuration(stage.elapsed_seconds) : "-"}</span>
    </article>
  );
}

function analysisStageDescription(stageName: string) {
  const descriptions: Record<string, string> = {
    ai_structuring: "提取岗位要求、技术栈和能力信号。",
    build_report_input: "汇总结构化结果，形成最终报告输入。",
    write_final_report: "生成可阅读的岗位分析报告。",
  };
  return descriptions[stageName] ?? "等待阶段更新";
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
        <MetricBlock icon={<Database className="h-4 w-4" />} label="收集岗位" value={formatCount(task.collected_count)} />
        <MetricBlock icon={<CheckCircle2 className="h-4 w-4" />} label="入选样本" value={formatCount(task.analysis_ready_count)} />
        <MetricBlock icon={<Activity className="h-4 w-4" />} label="样本占比" value={formatPercent(task.analysis_ready_count, task.collected_count)} />
        <MetricBlock icon={<FileText className="h-4 w-4" />} label="报告状态" value={detail?.artifact_paths.report ? "可查看" : "未生成"} />
      </div>
    </Panel>
  );
}

function TaskDetailHome({ detail, events, chartData, autoScoring, onTaskChanged }: { detail: TaskDetail | null; events: TaskEvent[]; chartData: Array<{ name: string; count: number }>; autoScoring: boolean; onTaskChanged: () => void }) {
  const task = detail?.task;
  if (!task) {
    return null;
  }
  return (
    <>
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <StageTimeline detail={detail} />
        <NextActionPanel autoScoring={autoScoring} detail={detail} onDone={onTaskChanged} />
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
  const stages = detail?.stages ?? [];
  return (
    <section className="rounded-[28px] border border-[#d8e1ec] bg-white/95 p-5 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-[#0b1220]">阶段进度</h3>
          <p className="mt-1 text-sm font-medium text-[#607089]">实时查看当前任务从岗位查找到样本确认的执行状态。</p>
        </div>
        <span className="rounded-[16px] border border-[#d8e1ec] bg-[#f8fafc] px-3 py-1.5 text-xs font-bold text-[#607089]">{formatCount(stages.length)} stages</span>
      </div>
      <div className="mt-5 grid gap-3">
        {stages.map((stage, index) => (
          <StageCard key={stage.stage_name} index={index} stage={stage} />
        ))}
        {stages.length === 0 ? <p className="rounded-[18px] border border-dashed border-[#d8e1ec] bg-[#f8fafc] px-4 py-5 text-center text-sm font-medium text-[#607089]">暂无阶段记录</p> : null}
      </div>
    </section>
  );
}

function StageCard({ stage, index }: { stage: TaskStageRun; index: number }) {
  const tone = stageTone(stage.status);
  return (
    <article className="grid gap-3 rounded-[22px] border border-[#e0e7ef] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] transition hover:-translate-y-0.5 hover:border-[#c7d3df] hover:bg-white hover:shadow-[0_14px_30px_rgba(14,23,38,0.08)] sm:grid-cols-[44px_minmax(0,1fr)_auto] sm:items-center">
      <span className={["flex h-10 w-10 items-center justify-center rounded-[16px] border text-sm font-bold", tone.badge].join(" ")}>{index + 1}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="text-sm font-bold text-[#0b1220]">{stageNameLabel(stage.stage_name)}</h4>
          <span className={["rounded-full border px-2.5 py-1 text-xs font-bold", tone.pill].join(" ")}>{statusLabel(stage.status)}</span>
        </div>
        <p className="mt-1 break-words text-sm font-medium leading-6 text-[#607089]">{stage.message || "等待阶段更新"}</p>
      </div>
      <span className="rounded-full border border-[#d8e1ec] bg-white px-3 py-1.5 text-xs font-bold text-[#607089]">{stage.elapsed_seconds ? formatDuration(stage.elapsed_seconds) : "-"}</span>
    </article>
  );
}

function stageTone(status: string) {
  if (status === "completed") {
    return { badge: "border-[#bfe9dc] bg-[#e8fbf5] text-[#087a67]", pill: "border-[#bfe9dc] bg-[#f1fbf7] text-[#087a67]" };
  }
  if (status === "running" || status === "waiting_for_user") {
    return { badge: "border-[#c8e7e1] bg-[#f2fbf8] text-[#0b7466]", pill: "border-[#c8e7e1] bg-[#f2fbf8] text-[#0b7466]" };
  }
  if (status === "failed" || status === "canceled") {
    return { badge: "border-[#f0d3a2] bg-[#fffaf0] text-[#875514]", pill: "border-[#f0d3a2] bg-[#fffaf0] text-[#875514]" };
  }
  return { badge: "border-[#d8e1ec] bg-white text-[#607089]", pill: "border-[#d8e1ec] bg-white text-[#607089]" };
}
function NextActionPanel({ detail, autoScoring, onDone }: { detail: TaskDetail | null; autoScoring: boolean; onDone: () => void }) {
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const task = detail?.task;
  const stages = detail?.stages ?? [];
  const live = Boolean(task?.id.startsWith("task-"));
  const stageMap = Object.fromEntries(stages.map((stage) => [stage.stage_name, stage.status]));
  const running = stages.some((stage) => stage.status === "running");
  const collecting = stageMap.collect_jobs === "running";
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

  async function cancelCurrentTask() {
    if (!task) {
      return;
    }
    setBusyAction("cancel");
    setError("");
    try {
      await cancelTask(task.id);
      onDone();
    } catch (error) {
      setError(error instanceof Error ? error.message : "中断失败");
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
      {live && collecting ? <p className="mt-2 text-sm leading-6 text-[#647086]">正在收集岗位信息，页面会自动刷新进度。请勿关闭 BOSS 页面，可以最小化。中断后，本次未完成结果不会进入后续流程。</p> : null}
      {live && !collecting && running ? <p className="mt-2 text-sm leading-6 text-[#647086]">当前有阶段运行中，页面会自动刷新状态和事件。</p> : null}
      {live && autoScoring ? <p className="mt-2 text-sm leading-6 text-[#647086]">岗位信息收集完成，正在进行本地评分。</p> : null}
      {live && !running && !autoScoring && next ? <p className="mt-2 text-sm leading-6 text-[#647086]">当前可继续：{next.description}</p> : null}
      {live && !running && !autoScoring && !next ? <p className="mt-2 text-sm leading-6 text-[#647086]">当前没有可直接执行的后台动作，请查看阶段状态或产物入口。</p> : null}
      {error ? <div className="mt-3"><ErrorBanner message={error} /></div> : null}
      <div className="mt-4 space-y-3">
        {live && collecting ? (
          <button
            className="flex w-full items-start gap-3 rounded-md border border-[#f0b8b8] bg-[#fff7f7] px-4 py-3 text-left text-[#b42318] transition hover:bg-[#fff1f1] disabled:cursor-not-allowed disabled:opacity-60"
            disabled={busyAction === "cancel"}
            onClick={() => void cancelCurrentTask()}
            type="button"
          >
            <Square className="mt-0.5 h-4 w-4" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold">{busyAction === "cancel" ? "正在中断" : "中断查找"}</span>
              <span className="mt-1 block text-xs leading-5">停止本次岗位信息收集，并返回可重新开始的状态。</span>
            </span>
          </button>
        ) : null}

        {live && next && !collecting ? (
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
  if (stageMap.collect_jobs === "pending") return { action: "start-collection", label: "开始查找", description: "启动岗位信息收集，页面会继续显示进度。" };
  if (stageMap.collect_jobs === "completed" && stageMap.score_jobs === "pending") return { action: "start-scoring", label: "开始本地评分", description: "对收集结果进行本地匹配评分，不涉及模型工作。" };
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

function EventPanel({ events, phase, title, description }: { events: TaskEvent[]; phase?: FindPhase; title?: string; description?: string }) {
  const latestEvents = events.slice(-8).reverse();
  const flow = phase && title && description ? { phase, title, description } : null;
  return (
    <section className="rounded-[28px] border border-[#d8e1ec] bg-white/95 p-5 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-[#0b1220]">通知</h3>
          <p className="mt-1 text-sm font-medium text-[#607089]">当前流程和最近状态会在这里实时更新。</p>
        </div>
        <span className="rounded-[16px] border border-[#d8e1ec] bg-[#f8fafc] px-3 py-1.5 text-xs font-bold text-[#607089]">{formatCount(events.length)} 条通知</span>
      </div>

      {flow ? <FindFlowProgress description={flow.description} phase={flow.phase} title={flow.title} /> : null}

      <div className={["grid gap-2", flow ? "mt-5 border-t border-[#edf2f7] pt-4" : "mt-5"].join(" ")}>
        {latestEvents.length === 0 ? <p className="rounded-[18px] border border-dashed border-[#d8e1ec] bg-[#f8fafc] px-4 py-5 text-center text-sm font-medium text-[#607089]">暂无通知</p> : null}
        {latestEvents.map((event) => (
          <article className="rounded-[22px] border border-[#e0e7ef] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] transition hover:border-[#c7d3df] hover:bg-white" key={event.id}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
                <span className="shrink-0 rounded-full border border-[#c8e7e1] bg-[#f2fbf8] px-2.5 py-1 text-xs font-bold text-[#0b7466]">{eventTypeLabel(event.event_type)}</span>
                <p className="min-w-[220px] flex-1 break-words text-sm font-medium leading-6 text-[#294256]">{event.message}</p>
              </div>
              <span className="shrink-0 font-mono text-xs font-medium text-[#7a8799]">{formatEventTime(event.created_at)}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function FindFlowProgress({ phase, title, description }: { phase: FindPhase; title: string; description: string }) {
  const steps: Array<{ phase: FindPhase; label: string }> = [
    { phase: "opening", label: "打开窗口" },
    { phase: "login", label: "确认登录" },
    { phase: "collecting", label: "查找岗位" },
    { phase: "scoring", label: "本地评分" },
    { phase: "done", label: "确认岗位" },
  ];
  const activeIndex = flowIndexForPhase(phase, title);
  const progressWidth = `${(Math.max(0, activeIndex) / (steps.length - 1)) * 100}%`;
  const interrupted = phase === "failed" || phase === "canceled";
  const complete = phase === "done";

  return (
    <div className="mt-6 overflow-hidden rounded-[24px] border border-[#dce5ef] bg-[#fbfdff] px-3 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] sm:px-4">
      <div className="overflow-x-auto pb-1">
        <div className="relative mx-auto min-w-[720px] max-w-none px-2 pt-1">
          <div className="absolute left-[7%] right-[7%] top-[28px] h-2 rounded-full bg-[#e7eef6]">
            <div className={["h-full rounded-full transition-all duration-700", interrupted ? "bg-[#e7b96c]" : "bg-[#20c7a7]"].join(" ")} style={{ width: progressWidth }} />
          </div>
          <div className="relative grid grid-cols-5 gap-2">
            {steps.map((step, index) => {
              const active = index === activeIndex;
              const passed = index < activeIndex && !interrupted;
              return <FindFlowStep active={active} interrupted={interrupted && active} key={step.phase} label={step.label} passed={passed} />;
            })}
          </div>
        </div>
      </div>

      <div className="mx-auto mt-6 max-w-2xl pb-8 text-center">
        <span className={["mx-auto inline-flex h-10 min-w-10 items-center justify-center rounded-[16px] px-2", interrupted ? "border border-[#f0d3a2] bg-[#fffaf0] text-[#875514]" : complete ? "border border-[#bfe9dc] bg-[#f1fbf7] text-[#087a67]" : "bg-transparent text-[#13a989]"].join(" ")}>
          {complete ? <CheckCircle2 className="h-5 w-5" /> : interrupted ? <Activity className="h-5 w-5" /> : <LoadingBars />}
        </span>
        <h4 className="mt-3 text-xl font-black text-[#0b1220]">{title}</h4>
        <p className="mt-2 whitespace-pre-line text-sm font-semibold leading-6 text-[#607089]">{description}</p>
      </div>
    </div>
  );
}

function FindFlowStep({ label, active, passed, interrupted }: { label: string; active: boolean; passed: boolean; interrupted: boolean }) {
  const activeClass = interrupted
    ? "border-[#e2b66f] bg-[#fff7e6] text-[#875514]"
    : "border-[#20c7a7] bg-[#e8fbf5] text-[#075f55]";
  const nodeClass = active ? activeClass : passed ? "border-[#20c7a7] bg-[#20c7a7] text-white" : "border-[#d8e1ec] bg-white text-[#a0adbd]";
  return (
    <div className="flex flex-col items-center text-center">
      <span className={["relative z-10 flex h-[52px] w-[52px] items-center justify-center rounded-full border-2 shadow-[0_8px_18px_rgba(14,23,38,0.08)] transition", nodeClass].join(" ")}>
        {active ? <span className="absolute inset-[-5px] rounded-full border border-current opacity-20 animate-ping" /> : null}
        {passed ? <CheckCircle2 className="h-5 w-5" /> : active && !interrupted ? <LoadingRing /> : active ? <Activity className="h-5 w-5" /> : <span className="h-2.5 w-2.5 rounded-full bg-current" />}
      </span>
      <span className={["mt-3 text-sm font-black", active || passed ? "text-[#0b1220]" : "text-[#7a8799]"].join(" ")}>{label}</span>
    </div>
  );
}

function LoadingRing() {
  return <span aria-hidden="true" className="h-7 w-7 rounded-full border-[3px] border-[#13a989] border-r-transparent [animation-duration:1.45s] animate-spin" />;
}

function LoadingBars() {
  return (
    <span aria-hidden="true" className="flex h-8 items-center gap-2 px-1">
      <span className="h-6 w-2.5 rounded-full bg-[#bdeedd] [animation:jobuwant-bars_1.15s_ease-in-out_infinite]" />
      <span className="h-6 w-2.5 rounded-full bg-[#72d7bf] [animation:jobuwant-bars_1.15s_ease-in-out_0.15s_infinite]" />
      <span className="h-6 w-2.5 rounded-full bg-[#20c7a7] [animation:jobuwant-bars_1.15s_ease-in-out_0.3s_infinite]" />
      <style jsx>{`@keyframes jobuwant-bars { 0%, 100% { transform: scaleY(0.78); opacity: 0.48; } 50% { transform: scaleY(1.16); opacity: 1; } }`}</style>
    </span>
  );
}

function flowIndexForPhase(phase: FindPhase, title: string) {
  if (phase === "done") return 4;
  if (phase === "scoring") return 3;
  if (phase === "collecting") return 2;
  if (phase === "login") return 1;
  if (phase === "failed" || phase === "canceled") {
    if (title.includes("登录") || title.includes("扫码")) return 1;
    if (title.includes("评分")) return 3;
    if (title.includes("岗位")) return 2;
  }
  return 0;
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

function StructuringPanel({ task, onTaskChanged, showActions = true }: { task: AnalysisTask; onTaskChanged: () => void; showActions?: boolean }) {
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

  const shouldPollBatches = live && (task.status === "running" || (status?.batches ?? []).some((batch) => batch.status === "pending" || batch.status === "running"));

  useEffect(() => {
    if (!shouldPollBatches) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [loadStatus, shouldPollBatches]);

  const stageCounts = useMemo(() => {
    return (status?.batches ?? []).reduce<Record<string, number>>((acc, batch) => {
      acc[batch.status] = (acc[batch.status] ?? 0) + 1;
      return acc;
    }, {});
  }, [status]);
  const usageTotals = useMemo(() => {
    return (status?.batches ?? []).reduce(
      (acc, batch) => ({
        inputTokens: acc.inputTokens + batch.input_tokens,
        outputTokens: acc.outputTokens + batch.output_tokens,
        estimatedCny: acc.estimatedCny + batch.estimated_cny,
      }),
      { inputTokens: 0, outputTokens: 0, estimatedCny: 0 },
    );
  }, [status]);
  const totalTokens = usageTotals.inputTokens + usageTotals.outputTokens;
  const usageRecorded = totalTokens > 0 || usageTotals.estimatedCny > 0;

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

  const batches = status?.batches ?? [];
  const completedBatches = stageCounts.completed ?? 0;

  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
        <div className="flex flex-col gap-4 border-b border-[#edf2f7] bg-[#fbfdff] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-bold text-[#0b1220]">批次队列</h3>
            <p className="mt-1 text-sm font-medium text-[#607089]">每个批次会独立记录处理状态、用量和费用估算。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {showActions ? <button className={secondaryButtonClass} onClick={() => void loadStatus()} type="button">
              <RefreshCw className="h-4 w-4" />
              刷新
            </button> : null}
            {showActions ? <button className={secondaryButtonClass} disabled={Boolean(busyAction)} onClick={() => void run("start")} type="button">
              <Settings2 className="h-4 w-4" />
              {busyAction === "start" ? "处理中" : "生成批次"}
            </button> : null}
            {showActions ? <button className={primaryButtonClass} disabled={Boolean(busyAction) || !batches.length} onClick={() => void run("run")} type="button">
              <Play className="h-4 w-4" />
              {busyAction === "run" ? "处理中" : "执行批次"}
            </button> : null}
          </div>
        </div>

        {error ? <div className="px-5 pt-4"><ErrorBanner message={error} /></div> : null}

        <div className="grid gap-3 px-5 py-5 md:grid-cols-2">
          {loading ? <BatchQueueMessage message="正在加载批次..." /> : null}
          {!loading && batches.length === 0 ? <BatchQueueMessage message="暂无批次" /> : null}
          {!loading ? batches.map((batch) => <BatchQueueCard batch={batch} key={batch.batch_id} />) : null}
        </div>
      </section>

      <aside className="space-y-5">
        <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
          <div className="border-b border-[#edf2f7] px-5 py-4">
            <h3 className="text-lg font-bold text-[#0b1220]">用量摘要</h3>
            <p className="mt-1 text-sm font-medium text-[#607089]">用于观察本次分析的资源消耗。</p>
          </div>
          <div className="px-5 py-5">
            <div className="rounded-[24px] border border-[#c8e7e1] bg-[#f2fbf8] px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)]">
              <div className="flex items-center gap-2 text-sm font-bold text-[#0b7466]">
                <Activity className="h-4 w-4" />
                Token 消耗
              </div>
              <div className="mt-2 font-mono text-3xl font-bold text-[#0b1220]">{usageRecorded ? formatCount(totalTokens) : "-"}</div>
              <div className="mt-3 grid gap-2 text-sm font-medium text-[#607089]">
                <span>输入 <strong className="float-right font-mono text-[#0b1220]">{formatCount(usageTotals.inputTokens)}</strong></span>
                <span>输出 <strong className="float-right font-mono text-[#0b1220]">{formatCount(usageTotals.outputTokens)}</strong></span>
                <span>费用 <strong className="float-right font-mono text-[#0b1220]">{usageTotals.estimatedCny ? `¥${usageTotals.estimatedCny.toFixed(4)}` : "-"}</strong></span>
              </div>
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-[28px] border border-[#d8e1ec] bg-white/95 shadow-[0_18px_54px_rgba(14,23,38,0.10),inset_0_1px_0_rgba(255,255,255,0.98)]">
          <div className="grid grid-cols-2 gap-2 px-5 py-5">
            <AnalysisSideMetric label="样本版本" value={status?.sample_version ? String(status.sample_version) : "-"} />
            <AnalysisSideMetric label="入选岗位" value={formatCount(status?.selected_count ?? 0)} />
            <AnalysisSideMetric label="批次数" value={formatCount(status?.total_batches ?? 0)} />
            <AnalysisSideMetric label="已完成" value={`${formatCount(completedBatches)} / ${formatCount(status?.total_batches ?? 0)}`} />
          </div>
        </section>
      </aside>
    </section>
  );
}
function BatchQueueCard({ batch }: { batch: import("@/lib/api").StructuringBatch }) {
  const active = batch.status === "running" || batch.status === "pending";
  return (
    <article className="rounded-[24px] border border-[#d8e1ec] bg-[#f8fafc] px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] transition hover:-translate-y-0.5 hover:border-[#c8d5df] hover:bg-white hover:shadow-[0_14px_30px_rgba(14,23,38,0.08)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-xs font-bold text-[#607089]">BATCH #{batch.batch_index}</div>
          <h4 className="mt-1 text-base font-black text-[#0b1220]">{formatCount(batch.job_ids.length)} 个岗位</h4>
          <p className="mt-1 text-xs font-medium leading-5 text-[#607089]">{formatBatchJobs(batch.job_ids)}</p>
        </div>
        <BatchStatusPill status={batch.status} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-[#e5edf4] pt-3 text-xs">
        <BatchMiniMetric label="输入" value={formatCount(batch.input_tokens)} />
        <BatchMiniMetric label="输出" value={formatCount(batch.output_tokens)} />
        <BatchMiniMetric label="费用" value={batch.estimated_cny ? `¥${batch.estimated_cny.toFixed(4)}` : "-"} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-medium text-[#607089]">
        <span className="rounded-full border border-[#d8e1ec] bg-white px-2.5 py-1">{batch.model_name || "模型待记录"}</span>
        <span className="rounded-full border border-[#d8e1ec] bg-white px-2.5 py-1">{batch.elapsed_seconds ? formatDuration(batch.elapsed_seconds) : active ? "进行中" : "-"}</span>
      </div>

      {batch.error_message ? <p className="mt-3 break-words rounded-[16px] border border-[#f0d3a2] bg-[#fffaf0] px-3 py-2 text-xs font-medium leading-5 text-[#875514]">{batch.error_message}</p> : null}
    </article>
  );
}

function BatchQueueMessage({ message }: { message: string }) {
  return <div className="rounded-[24px] border border-dashed border-[#d8e1ec] bg-[#f8fafc] px-4 py-10 text-center text-sm font-medium text-[#607089] md:col-span-2">{message}</div>;
}

function BatchStatusPill({ status }: { status: string }) {
  const tone = status === "completed"
    ? "border-[#bfe9dc] bg-[#f1fbf7] text-[#087a67]"
    : status === "running" || status === "pending"
      ? "border-[#c8e7e1] bg-[#f2fbf8] text-[#0b7466]"
      : status === "failed" || status === "canceled"
        ? "border-[#f0d3a2] bg-[#fffaf0] text-[#875514]"
        : "border-[#d8e1ec] bg-white text-[#607089]";
  return (
    <span className={["inline-flex h-8 items-center gap-2 rounded-[14px] border px-2.5 text-xs font-bold", tone].join(" ")}>
      {status === "running" ? <span className="h-2 w-2 rounded-full bg-current animate-pulse" /> : <span className="h-2 w-2 rounded-full bg-current" />}
      {statusLabel(status)}
    </span>
  );
}

function BatchMiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-[#e0e7ef] bg-white px-3 py-2">
      <div className="font-bold text-[#8a97aa]">{label}</div>
      <div className="mt-1 truncate font-mono font-bold text-[#0b1220]">{value}</div>
    </div>
  );
}

function AnalysisSideMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-[#d8e1ec] bg-[#f8fafc] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)]">
      <div className="text-xs font-bold text-[#607089]">{label}</div>
      <div className="mt-1 truncate font-mono text-xl font-bold text-[#0b1220]">{value}</div>
    </div>
  );
}
function formatBatchJobs(jobIds: number[]) {
  if (!jobIds.length) {
    return "-";
  }
  const preview = jobIds.slice(0, 3).join("、");
  return jobIds.length > 3 ? `${preview} 等 ${jobIds.length} 个` : preview;
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
    collect_jobs: "收集岗位",
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





function formatEventTime(value: string) {
  if (!value) {
    return "fixture";
  }
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value) ? `${value.replace(" ", "T")}Z` : value;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}
function formatMetricScore(value: unknown) {
  const score = Number(value);
  if (!Number.isFinite(score) || score <= 0) {
    return "-";
  }
  return score.toFixed(1);
}


function formatDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "-";
  }
  if (seconds < 60) {
    return `${Math.round(seconds)} 秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;
}










