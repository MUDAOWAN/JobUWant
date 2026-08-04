"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, FileText, ListChecks, Plus, RefreshCw, Search } from "lucide-react";
import { createTask, getHealth, listTasks, type AnalysisTask, type AnalysisTaskCreate } from "@/lib/api";
import { formatCount, formatPercent, statusLabel } from "@/lib/format";
import { AppShell, ErrorBanner, MetricBlock, PageBody, Panel, PanelHeader, StatusPill, primaryButtonClass, secondaryButtonClass } from "@/components/ui/shell";

type LoadState = {
  health: string;
  tasks: AnalysisTask[];
  loading: boolean;
  error: string;
};

type CreateForm = {
  task_name: string;
  city: string;
  city_code: string;
  keyword: string;
  job_type: string;
  expected_job_count: string;
  batch_size: string;
  source_type: string;
};

const initialState: LoadState = {
  health: "检查中",
  tasks: [],
  loading: true,
  error: "",
};

const initialForm: CreateForm = {
  task_name: "",
  city: "杭州",
  city_code: "101210100",
  keyword: "Agent工程师",
  job_type: "intern",
  expected_job_count: "30",
  batch_size: "10",
  source_type: "",
};

export function TaskListPage() {
  const [state, setState] = useState<LoadState>(initialState);
  const [query, setQuery] = useState("");
  const [form, setForm] = useState<CreateForm>(initialForm);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const router = useRouter();

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const [health, tasks] = await Promise.all([getHealth(), listTasks()]);
      setState({
        health: health.status === "ok" ? "正常" : health.status,
        tasks,
        loading: false,
        error: "",
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "任务加载失败",
      }));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredTasks = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) {
      return state.tasks;
    }
    return state.tasks.filter((task) => {
      return [task.task_name, task.city, task.keyword, task.job_type, task.source_type]
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    });
  }, [query, state.tasks]);

  const summary = useMemo(() => {
    const totalJobs = state.tasks.reduce((sum, task) => sum + task.collected_count, 0);
    const selectedJobs = state.tasks.reduce((sum, task) => sum + task.analysis_ready_count, 0);
    const completedTasks = state.tasks.filter((task) => task.status === "completed").length;
    return { totalJobs, selectedJobs, completedTasks };
  }, [state.tasks]);

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setCreateError("");
    try {
      const payload: AnalysisTaskCreate = {
        task_name: form.task_name.trim(),
        city: form.city.trim(),
        city_code: form.city_code.trim(),
        keyword: form.keyword.trim(),
        job_type: form.job_type,
        expected_job_count: Number(form.expected_job_count) || 30,
        batch_size: Number(form.batch_size) || 10,
        source_type: form.source_type.trim(),
      };
      const created = await createTask(payload);
      router.push(`/tasks/${created.task.id}`);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "任务创建失败");
    } finally {
      setCreating(false);
    }
  }

  return (
    <AppShell
      actions={
        <>
          <StatusPill label="后端" value={state.health} />
          <button className={secondaryButtonClass} onClick={() => void load()} type="button">
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        </>
      }
      title="任务列表"
    >
      <PageBody>
        <ErrorBanner message={state.error} />

        <section className="grid gap-4 md:grid-cols-3">
          <MetricCard icon={<ListChecks className="h-4 w-4" />} label="任务总数" value={formatCount(state.tasks.length)} />
          <MetricCard icon={<CheckCircle2 className="h-4 w-4" />} label="已完成任务" value={formatCount(summary.completedTasks)} />
          <MetricCard icon={<FileText className="h-4 w-4" />} label="入选样本" value={formatCount(summary.selectedJobs)} helper={`来自 ${formatCount(summary.totalJobs)} 个岗位`} />
        </section>

        <Panel className="overflow-hidden">
          <PanelHeader
            actions={
              <>
                <label className="relative block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#647086]" />
                  <input
                    aria-label="搜索任务"
                    className="h-10 w-full rounded-md border border-[#d9dee8] bg-white pl-9 pr-3 text-sm outline-none transition placeholder:text-[#9aa4b4] focus:border-[#2364aa] sm:w-72"
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="搜索城市、关键词或任务名"
                    value={query}
                  />
                </label>
                <button className={primaryButtonClass} onClick={() => setCreateOpen((current) => !current)} type="button">
                  <Plus className="h-4 w-4" />
                  创建任务
                </button>
              </>
            }
            description="样本任务和 live 任务会一起显示；新任务创建后不会自动开始后续阶段。"
            title="分析任务"
          />

          {createOpen ? <CreateTaskForm creating={creating} error={createError} form={form} onChange={setForm} onSubmit={submitCreate} /> : null}

          <div className="overflow-x-auto">
            <table aria-label="分析任务列表" className="w-full min-w-[960px] border-collapse text-sm">
              <thead className="bg-[#f8fafc] text-left text-xs font-semibold text-[#647086]">
                <tr>
                  <th className="px-5 py-3" scope="col">任务</th>
                  <th className="px-4 py-3" scope="col">城市</th>
                  <th className="px-4 py-3" scope="col">关键词</th>
                  <th className="px-4 py-3" scope="col">求职类型</th>
                  <th className="px-4 py-3" scope="col">状态</th>
                  <th className="px-4 py-3" scope="col">岗位</th>
                  <th className="px-4 py-3" scope="col">样本</th>
                  <th className="px-4 py-3" scope="col">报告</th>
                  <th className="px-5 py-3 text-right" scope="col">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e8ecf2]">
                {state.loading ? <LoadingRows /> : null}
                {!state.loading && filteredTasks.length === 0 ? <EmptyRow /> : null}
                {!state.loading
                  ? filteredTasks.map((task) => (
                      <tr className="bg-white align-top transition hover:bg-[#fbfcfe]" key={task.id}>
                        <td className="px-5 py-4">
                          <div className="font-semibold text-[#172033]">{task.task_name}</div>
                          <div className="mt-1 max-w-md break-words text-xs leading-5 text-[#647086]">{task.source_type}</div>
                          <div className="mt-2 text-xs text-[#647086]">运行编号 {task.search_run_id || "-"}</div>
                        </td>
                        <td className="px-4 py-4">{cityLabel(task.city)}</td>
                        <td className="px-4 py-4">{keywordLabel(task.keyword)}</td>
                        <td className="px-4 py-4">{jobTypeLabel(task.job_type)}</td>
                        <td className="px-4 py-4"><TaskStatus status={task.status} /></td>
                        <td className="px-4 py-4">{formatCount(task.collected_count)}</td>
                        <td className="px-4 py-4">
                          <div>{formatCount(task.analysis_ready_count)}</div>
                          <div className="mt-1 text-xs text-[#647086]">{formatPercent(task.analysis_ready_count, task.collected_count)}</div>
                        </td>
                        <td className="px-4 py-4">{task.fixture.report_path || task.id.startsWith("task-") ? (task.status === "completed" ? "已生成" : "未生成") : "已生成"}</td>
                        <td className="px-5 py-4 text-right">
                          <Link className={primaryButtonClass} href={`/tasks/${task.id}`}>
                            查看详情
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </td>
                      </tr>
                    ))
                  : null}
              </tbody>
            </table>
          </div>
        </Panel>
      </PageBody>
    </AppShell>
  );
}

function CreateTaskForm({ form, creating, error, onChange, onSubmit }: { form: CreateForm; creating: boolean; error: string; onChange: (form: CreateForm) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  function update<K extends keyof CreateForm>(key: K, value: CreateForm[K]) {
    onChange({ ...form, [key]: value });
  }
  return (
    <form className="grid gap-4 border-b border-[#e8ecf2] bg-[#fbfcfe] px-5 py-5 lg:grid-cols-6" onSubmit={onSubmit}>
      {error ? <div className="rounded-md border border-[#f0b8b8] bg-[#fff7f7] px-3 py-2 text-sm text-[#b42318] lg:col-span-6">{error}</div> : null}
      <TextField label="任务名" onChange={(value) => update("task_name", value)} placeholder="可选" value={form.task_name} />
      <TextField label="城市" onChange={(value) => update("city", value)} value={form.city} />
      <TextField label="城市编码" onChange={(value) => update("city_code", value)} value={form.city_code} />
      <TextField label="关键词" onChange={(value) => update("keyword", value)} value={form.keyword} />
      <label className="text-sm">
        <span className="font-medium text-[#647086]">求职类型</span>
        <select className="mt-1 h-10 w-full rounded-md border border-[#d9dee8] bg-white px-3 outline-none focus:border-[#2364aa]" onChange={(event) => update("job_type", event.target.value)} value={form.job_type}>
          <option value="intern">实习</option>
          <option value="any">不限</option>
          <option value="full_time">全职</option>
        </select>
      </label>
      <TextField label="目标数量" onChange={(value) => update("expected_job_count", value)} type="number" value={form.expected_job_count} />
      <TextField label="批大小" onChange={(value) => update("batch_size", value)} type="number" value={form.batch_size} />
      <label className="text-sm lg:col-span-4">
        <span className="font-medium text-[#647086]">来源类型</span>
        <input className="mt-1 h-10 w-full rounded-md border border-[#d9dee8] bg-white px-3 outline-none focus:border-[#2364aa]" onChange={(event) => update("source_type", event.target.value)} placeholder="留空则后端自动生成" value={form.source_type} />
      </label>
      <div className="flex items-end">
        <button className={`${primaryButtonClass} w-full`} disabled={creating} type="submit">
          <Plus className="h-4 w-4" />
          {creating ? "创建中" : "确认创建"}
        </button>
      </div>
    </form>
  );
}

function TextField({ label, value, onChange, placeholder = "", type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string }) {
  return (
    <label className="text-sm">
      <span className="font-medium text-[#647086]">{label}</span>
      <input className="mt-1 h-10 w-full rounded-md border border-[#d9dee8] bg-white px-3 outline-none focus:border-[#2364aa]" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} type={type} value={value} />
    </label>
  );
}

function MetricCard({ icon, label, value, helper }: { icon: ReactNode; label: string; value: string; helper?: string }) {
  return (
    <Panel className="p-5">
      <MetricBlock helper={helper} icon={icon} label={label} value={value} />
    </Panel>
  );
}

function TaskStatus({ status }: { status: string }) {
  return <span className="inline-flex rounded-full bg-[#e8f7f2] px-2 py-1 text-xs font-medium text-[#2f7d65]">{statusLabel(status)}</span>;
}

function LoadingRows() {
  return (
    <tr>
      <td className="px-5 py-8 text-center text-[#647086]" colSpan={9}>正在加载任务...</td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td className="px-5 py-8 text-center text-[#647086]" colSpan={9}>没有符合条件的任务</td>
    </tr>
  );
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


