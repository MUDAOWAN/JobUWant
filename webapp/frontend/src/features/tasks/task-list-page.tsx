"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CircleDot,
  Clock3,
  Check,
  ChevronDown,
  FileText,
  MapPin,
  Play,
  Search,
  Settings,
  Target,
  Terminal,
} from "lucide-react";
import {
  createTask,
  getHealth,
  listCities,
  listTasks,
  startCollection,
  type AnalysisTask,
  type AnalysisTaskCreate,
  type SupportedCity,
} from "@/lib/api";
import { formatCount, formatPercent, statusLabel } from "@/lib/format";

type LoadState = {
  health: string;
  tasks: AnalysisTask[];
  cities: SupportedCity[];
  loading: boolean;
  error: string;
};

type CreateForm = {
  task_name: string;
  city: string;
  keyword: string;
  job_type: string;
  expected_job_count: string;
};

const MAX_TARGET_COUNT = 200;
const DEFAULT_BATCH_SIZE = 10;

const initialState: LoadState = {
  health: "检查中",
  tasks: [],
  cities: [],
  loading: true,
  error: "",
};

const initialForm: CreateForm = {
  task_name: "任务1",
  city: "杭州",
  keyword: "Agent工程师",
  job_type: "intern",
  expected_job_count: "30",
};

const jobTypes = [
  { value: "intern", label: "实习" },
  { value: "full_time", label: "全职" },
  { value: "any", label: "不限" },
];

export function TaskListPage() {
  const [state, setState] = useState<LoadState>(initialState);
  const [form, setForm] = useState<CreateForm>(initialForm);
  const [creating, setCreating] = useState(false);
  const [starting, setStarting] = useState(false);
  const [createError, setCreateError] = useState("");
  const router = useRouter();

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const [health, tasks, cities] = await Promise.all([getHealth(), listTasks(), listCities()]);
      setState({
        health: health.status === "ok" ? "正常" : health.status,
        tasks,
        cities,
        loading: false,
        error: "",
      });
      setForm((current) => {
        if (cities.some((city) => city.name === current.city)) {
          return current;
        }
        return { ...current, city: cities[0]?.name ?? current.city };
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        health: "未连接",
        loading: false,
        error: normalizeLoadError(error),
      }));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const recentTasks = useMemo(() => state.tasks.slice(0, 3), [state.tasks]);
  const targetValidation = validateTargetCount(form.expected_job_count);
  const runningSubmit = creating || starting;
  const canSubmit = !runningSubmit && !targetValidation && Boolean(form.city) && Boolean(form.keyword.trim());

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationMessage = validateTargetCount(form.expected_job_count);
    if (validationMessage) {
      setCreateError(validationMessage);
      return;
    }
    setCreating(true);
    setStarting(false);
    setCreateError("");
    try {
      const payload: AnalysisTaskCreate = {
        task_name: form.task_name.trim(),
        city: form.city,
        keyword: form.keyword.trim(),
        job_type: form.job_type,
        expected_job_count: Number(form.expected_job_count),
        batch_size: DEFAULT_BATCH_SIZE,
      };
      const created = await createTask(payload);
      setCreating(false);
      setStarting(true);
      await startCollection(created.task.id);
      router.push("/tasks/" + created.task.id);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "任务创建失败");
    } finally {
      setCreating(false);
      setStarting(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[#f7f9fc] text-[#0e1726]">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(14,23,38,0.045)_1px,transparent_1px),linear-gradient(90deg,rgba(14,23,38,0.045)_1px,transparent_1px)] bg-[size:44px_44px]" />
      <div className="pointer-events-none fixed inset-x-0 top-0 h-40 bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(255,255,255,0))]" />

      <header className="relative z-10">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
          <Link
            className="group inline-flex items-baseline gap-2 font-mono text-[22px] font-semibold tracking-tight text-[#0b1220] outline-none transition focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-4"
            href="/tasks"
          >
            <span className="relative">
              jobuwant
              <span className="absolute -bottom-1 left-0 h-px w-full origin-left scale-x-0 bg-[#20c7a7] transition group-hover:scale-x-100" />
            </span>
            <span className="text-[#20c7a7]">_</span>
          </Link>
          <button
            className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-md border border-[#d6dde8] bg-white/85 px-3 font-mono text-xs text-[#4b5c73] shadow-[0_6px_24px_rgba(14,23,38,0.08)] backdrop-blur transition hover:border-[#20c7a7] hover:text-[#0b7466] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-2"
            type="button"
          >
            <CircleDot className={state.health === "正常" ? "h-3.5 w-3.5 text-[#20c7a7]" : "h-3.5 w-3.5 text-[#d18b19]"} />
            服务 {state.health}
          </button>
        </div>
      </header>

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-64px)] max-w-7xl flex-col px-5 pb-10">
        <section className="flex flex-1 flex-col items-center justify-center pt-8 text-center">
          <div className="inline-flex h-8 items-center gap-2 rounded-full border border-[#d8e0eb] bg-white/82 px-3 font-mono text-[11px] text-[#607089] shadow-sm backdrop-blur">
            <Terminal className="h-3.5 w-3.5 text-[#159b83]" />
            job search console
          </div>
          <h1 className="mt-5 text-4xl font-semibold tracking-normal text-[#0b1220] sm:text-6xl">想查什么岗位？</h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-[#58677d] sm:text-base">
            选择城市、岗位方向和目标数量，创建任务后立即开始查找。
          </p>

          <SearchConsole
            canSubmit={canSubmit}
            cities={state.cities}
            creating={creating}
            error={createError || state.error}
            form={form}
            onChange={setForm}
            onSubmit={submitCreate}
            starting={starting}
            targetValidation={targetValidation}
          />
        </section>

        <RecentTasksPanel loading={state.loading} recentTasks={recentTasks} totalTasks={state.tasks.length} />
      </div>
    </main>
  );
}

const searchCtaMotionStyles = `
  @keyframes jobuwant-live-cta-sweep {
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

  .jobuwant-search-cta {
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

  .jobuwant-search-cta::before {
    content: "";
    position: absolute;
    inset: 1px;
    z-index: 1;
    border-radius: inherit;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0) 42%);
    pointer-events: none;
  }

  .jobuwant-search-cta::after {
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
    animation: jobuwant-live-cta-sweep 2.8s linear infinite;
  }

  .jobuwant-search-cta:hover::after,
  .jobuwant-search-cta:focus-visible::after {
    animation-duration: 2.8s;
  }

  .jobuwant-search-cta:hover .jobuwant-search-cta-icon,
  .jobuwant-search-cta:focus-visible .jobuwant-search-cta-icon {
    transform: translateX(4px);
  }

  .jobuwant-search-cta:disabled {
    border-color: #cbd5e1 !important;
    background: #eef2f7 !important;
  }

  .jobuwant-search-cta:disabled::before,
  .jobuwant-search-cta:disabled::after {
    display: none;
  }

  .jobuwant-search-cta:disabled .jobuwant-search-cta-icon {
    transform: none;
  }

`;


function SearchConsole({
  form,
  cities,
  creating,
  starting,
  canSubmit,
  error,
  targetValidation,
  onChange,
  onSubmit,
}: {
  form: CreateForm;
  cities: SupportedCity[];
  creating: boolean;
  starting: boolean;
  canSubmit: boolean;
  error: string;
  targetValidation: string;
  onChange: (form: CreateForm) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [openPicker, setOpenPicker] = useState<"" | "city" | "jobType">("");
  const cityPickerRef = useRef<HTMLDivElement>(null);
  const jobTypePickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!openPicker) {
      return;
    }

    function closeOnOutsidePointer(event: PointerEvent) {
      const target = event.target as Node;
      if (cityPickerRef.current?.contains(target) || jobTypePickerRef.current?.contains(target)) {
        return;
      }
      setOpenPicker("");
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenPicker("");
      }
    }

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [openPicker]);

  function update<K extends keyof CreateForm>(key: K, value: CreateForm[K]) {
    onChange({ ...form, [key]: value });
  }

  function chooseCity(value: string) {
    update("city", value);
    setOpenPicker("");
  }

  function chooseJobType(value: string) {
    update("job_type", value);
    setOpenPicker("");
  }

  return (
    <form
      className="group relative z-50 mx-auto mt-9 w-full max-w-7xl rounded-[28px] border border-[#d8e1ec] bg-white/94 p-3 text-left shadow-[0_24px_74px_rgba(14,23,38,0.14),inset_0_1px_0_rgba(255,255,255,0.98)] backdrop-blur transition focus-within:border-[#20c7a7] focus-within:shadow-[0_28px_90px_rgba(14,23,38,0.16),0_0_0_4px_rgba(32,199,167,0.12)]"
      onSubmit={onSubmit}
    >
      <style>{searchCtaMotionStyles}</style>
      <div className="mb-3 flex flex-col gap-2 rounded-[24px] border border-[#dde6ef] bg-[#f8fafc] px-4 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.98)] sm:flex-row sm:items-center sm:justify-between">
        <div className="flex shrink-0 items-center gap-2 px-1 font-bold text-[#53657b]">
          <Terminal className="h-3.5 w-3.5 text-[#0b7466]" />
          <span className="text-sm font-bold">即将搜索</span>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-[#294256]">
          <SummaryChip>{cityLabelOnly(cities, form.city)}</SummaryChip>
          <SummaryChip>{form.keyword || "输入岗位"}</SummaryChip>
          <SummaryChip>{jobTypeLabel(form.job_type)}</SummaryChip>
          <SummaryChip>{form.expected_job_count || "-"} 条</SummaryChip>
        </div>
      </div>

      <div className="grid gap-2 lg:grid-cols-[minmax(176px,0.92fr)_minmax(220px,1.05fr)_minmax(166px,0.76fr)_minmax(140px,0.62fr)_minmax(190px,0.86fr)_minmax(150px,0.66fr)]">
        <div ref={cityPickerRef} className="relative z-[70] min-w-0">
          <ConsoleField
            active={openPicker === "city"}
            icon={<MapPin className="h-4 w-4" />}
            label="城市"
            onClick={() => setOpenPicker((current) => (current === "city" ? "" : "city"))}
          >
            <PickerValue label={cityLabelOnly(cities, form.city)} open={openPicker === "city"} />
          </ConsoleField>
          {openPicker === "city" ? <CityPickerMenu cities={cities} onChoose={chooseCity} value={form.city} /> : null}
        </div>
        <ConsoleField icon={<Search className="h-4 w-4" />} label="岗位">
          <input
            className={consoleInputClass}
            onChange={(event) => update("keyword", event.target.value)}
            placeholder="Agent工程师"
            value={form.keyword}
          />
        </ConsoleField>
        <div ref={jobTypePickerRef} className="relative z-[65] min-w-0">
          <ConsoleField
            active={openPicker === "jobType"}
            icon={<Settings className="h-4 w-4" />}
            label="类型"
            onClick={() => setOpenPicker((current) => (current === "jobType" ? "" : "jobType"))}
          >
            <PickerValue label={jobTypeLabel(form.job_type)} open={openPicker === "jobType"} />
          </ConsoleField>
          {openPicker === "jobType" ? <JobTypePickerMenu onChoose={chooseJobType} value={form.job_type} /> : null}
        </div>
        <ConsoleField icon={<Target className="h-4 w-4" />} label="数量">
          <input
            aria-invalid={Boolean(targetValidation)}
            className={consoleInputClass}
            max={MAX_TARGET_COUNT}
            min={1}
            onChange={(event) => update("expected_job_count", event.target.value)}
            type="number"
            value={form.expected_job_count}
          />
        </ConsoleField>
        <ConsoleField icon={<FileText className="h-4 w-4" />} label="任务名">
          <input
            className={consoleInputClass}
            onChange={(event) => update("task_name", event.target.value)}
            placeholder="任务1"
            value={form.task_name}
          />
        </ConsoleField>
        <button
          className="jobuwant-search-cta relative inline-flex h-[66px] cursor-pointer items-center justify-center gap-2.5 overflow-hidden rounded-full border border-transparent px-5 text-[17px] font-black text-[#064f47] shadow-[0_15px_24px_rgba(15,23,42,0.13),0_7px_16px_rgba(32,199,167,0.20),inset_0_1px_0_rgba(255,255,255,0.96),inset_0_-2px_5px_rgba(15,23,42,0.05)] transition duration-200 hover:-translate-y-1 hover:border-transparent hover:shadow-[0_20px_31px_rgba(15,23,42,0.15),0_9px_22px_rgba(32,199,167,0.28),inset_0_1px_0_rgba(255,255,255,0.98),inset_0_-2px_5px_rgba(15,23,42,0.04)] active:translate-y-0 active:shadow-[0_8px_14px_rgba(15,23,42,0.12),0_4px_10px_rgba(32,199,167,0.14),inset_0_1px_0_rgba(255,255,255,0.96)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-[#cbd5e1] disabled:bg-[#eef2f7] disabled:text-[#7a8799] disabled:hover:translate-y-0"
          disabled={!canSubmit}
          type="submit"
        >

          <span className="relative z-[3] flex items-center gap-2.5">
            <Play className="jobuwant-search-cta-icon h-5 w-5 text-[#087a67] transition-transform duration-200" />
            <span className="font-black">{creating ? "创建中" : starting ? "启动中" : "开始查找"}</span>
          </span>
        </button>
      </div>

      {targetValidation ? <p className="mt-2 px-1.5 text-xs font-medium text-[#b42318]">{targetValidation}</p> : null}
      {error ? <p className="mt-2 rounded-md border border-[#f5d19b] bg-[#fffaf0] px-3 py-2 text-sm text-[#875514]">{error}</p> : null}
    </form>
  );
}

const consoleInputClass =
  "h-8 w-full min-w-0 flex-1 truncate bg-transparent text-[16px] font-bold text-[#0b1220] outline-none placeholder:text-[#8b99ad] focus:text-[#0b7466]";

function ConsoleField({ icon, label, children, onClick, active = false }: { icon: ReactNode; label: string; children: ReactNode; onClick?: () => void; active?: boolean }) {
  return (
    <div
      className={[
        "relative flex h-[66px] min-w-0 items-center gap-3 overflow-visible rounded-[24px] border bg-[#f8fafc] px-4 py-2 shadow-[0_10px_24px_rgba(14,23,38,0.08),inset_0_1px_0_rgba(255,255,255,0.98)] transition duration-200 hover:-translate-y-0.5 hover:border-[#b9c7d5] hover:bg-white hover:shadow-[0_16px_32px_rgba(14,23,38,0.11),inset_0_1px_0_rgba(255,255,255,1)] focus-within:-translate-y-0.5 focus-within:border-[#20c7a7] focus-within:bg-white focus-within:ring-2 focus-within:ring-[#d5faf1]",
        onClick ? "cursor-pointer" : "cursor-text",
        active ? "border-[#20c7a7] bg-white ring-2 ring-[#d5faf1]" : "border-[#d8e1ec]",
      ].join(" ")}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick();
        }
      } : undefined}
    >
      <span className="shrink-0 text-[#0b7466]">{icon}</span>
      <span className="flex min-w-0 flex-1 items-center gap-1.5">
        <span className="shrink-0 text-[15px] font-bold text-[#526276]">{label}：</span>
        <span className="min-w-0 flex-1 overflow-visible">{children}</span>
      </span>
    </div>
  );
}

function PickerValue({ label, open }: { label: string; open: boolean }) {
  return (
    <span className="flex h-8 min-w-0 flex-1 items-center gap-1.5">
      <span className="min-w-0 truncate text-[16px] font-bold text-[#0b1220]">{label}</span>
      <ChevronDown className={open ? "h-4 w-4 shrink-0 rotate-180 text-[#0b7466] transition" : "h-4 w-4 shrink-0 text-[#0b7466] transition"} />
    </span>
  );
}

function CityPickerMenu({ cities, value, onChoose }: { cities: SupportedCity[]; value: string; onChoose: (value: string) => void }) {
  const grouped = groupCitiesByTier(cities);
  const hasCities = cities.length > 0;
  return (
    <div className="absolute left-0 right-0 top-[74px] z-[100] overflow-hidden rounded-[22px] border border-[#d8e1ec] bg-white/98 p-2 shadow-[0_24px_70px_rgba(14,23,38,0.18),inset_0_1px_0_rgba(255,255,255,0.98)] backdrop-blur">
      <div className="px-3 pb-2 pt-2 text-xs font-bold text-[#607089]">选择城市</div>
      <div className="max-h-[320px] overflow-y-auto pr-1">
        {!hasCities ? (
          <button className="flex w-full items-center justify-between rounded-[16px] px-3 py-2.5 text-left text-sm font-bold text-[#0b1220] hover:bg-[#f3f7fb]" onClick={() => onChoose(value)} type="button">
            {value || "杭州"}
            <Check className="h-4 w-4 text-[#0b7466]" />
          </button>
        ) : null}
        {Object.entries(grouped).map(([tier, options]) => (
          <div className="py-1" key={tier}>
            <div className="px-3 py-1.5 font-mono text-[11px] text-[#8a97aa]">{tierLabel(tier)}</div>
            <div className="grid gap-1">
              {options.map((city) => {
                const active = city.name === value;
                return (
                  <button
                    className={[
                      "flex w-full items-center justify-between gap-3 rounded-[16px] px-3 py-2.5 text-left transition",
                      active ? "bg-[#e8fbf5] text-[#075f55]" : "text-[#0b1220] hover:bg-[#f3f7fb]",
                    ].join(" ")}
                    key={city.city_code}
                    onClick={() => onChoose(city.name)}
                    type="button"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-bold">{city.name}</span>
                      <span className="mt-0.5 block truncate text-xs text-[#7a8799]">{city.province}</span>
                    </span>
                    {active ? <Check className="h-4 w-4 shrink-0 text-[#0b7466]" /> : null}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function JobTypePickerMenu({ value, onChoose }: { value: string; onChoose: (value: string) => void }) {
  return (
    <div className="absolute left-0 right-0 top-[74px] z-[100] overflow-hidden rounded-[22px] border border-[#d8e1ec] bg-white/98 p-2 shadow-[0_22px_60px_rgba(14,23,38,0.16),inset_0_1px_0_rgba(255,255,255,0.98)] backdrop-blur">
      <div className="px-3 pb-2 pt-2 text-xs font-bold text-[#607089]">选择类型</div>
      <div className="grid gap-1">
        {jobTypes.map((item) => {
          const active = item.value === value;
          return (
            <button
              className={[
                "flex w-full items-center justify-between rounded-[16px] px-3 py-2.5 text-left text-sm font-bold transition",
                active ? "bg-[#e8fbf5] text-[#075f55]" : "text-[#0b1220] hover:bg-[#f3f7fb]",
              ].join(" ")}
              key={item.value}
              onClick={() => onChoose(item.value)}
              type="button"
            >
              {item.label}
              {active ? <Check className="h-4 w-4 text-[#0b7466]" /> : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SummaryChip({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-[#d8e1ec] bg-white px-3 py-1 text-[#294256] shadow-[inset_0_1px_0_rgba(255,255,255,0.96)]">{children}</span>;
}
function RecentTasksPanel({ recentTasks, loading, totalTasks }: { recentTasks: AnalysisTask[]; loading: boolean; totalTasks: number }) {
  return (
    <section className="mx-auto mt-8 w-full max-w-5xl">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="font-mono text-sm font-bold text-[#0b1220]">recent_runs</h2>
          <p className="mt-1 text-xs text-[#607089]">最多展示最近 3 条任务。</p>
        </div>
        <span className="font-mono text-xs text-[#607089]">{formatCount(totalTasks)} total</span>
      </div>

      <div className="grid gap-2">
        {loading ? <RecentPlaceholder label="正在加载任务..." /> : null}
        {!loading && recentTasks.length === 0 ? <RecentPlaceholder label="还没有创建过任务" /> : null}
        {!loading
          ? recentTasks.map((task) => (
              <article
                className="grid gap-3 rounded-lg border border-[#e0e6ef] bg-white/82 px-4 py-3 text-sm shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-[#c2ccd9] hover:bg-white hover:shadow-[0_14px_34px_rgba(14,23,38,0.10)] md:grid-cols-[minmax(0,1.5fr)_0.72fr_0.9fr_auto] md:items-center"
                key={task.id}
              >
                <div className="min-w-0">
                  <div className="truncate font-bold text-[#0b1220]">{task.task_name}</div>
                  <div className="mt-1 flex min-w-0 items-center gap-2 truncate font-mono text-xs text-[#607089]">
                    <BriefcaseBusiness className="h-3.5 w-3.5 shrink-0 text-[#159b83]" />
                    <span className="truncate">
                      {cityLabel(task.city)} / {keywordLabel(task.keyword)} / {jobTypeLabel(task.job_type)}
                    </span>
                  </div>
                </div>
                <TaskStatus status={task.status} />
                <div className="flex items-center gap-2 text-xs text-[#607089]">
                  <Clock3 className="h-3.5 w-3.5 text-[#8a97aa]" />
                  <span>
                    <span className="font-bold text-[#0b1220]">{formatCount(task.analysis_ready_count)}</span> /{" "}
                    {formatCount(task.collected_count)} 样本
                    <span className="ml-2">{formatPercent(task.analysis_ready_count, task.collected_count)}</span>
                  </span>
                </div>
                <Link
                  className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-[#d6dde8] bg-white px-3 text-xs font-bold text-[#0b1220] transition hover:border-[#20c7a7] hover:text-[#0b7466] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20c7a7] focus-visible:ring-offset-2"
                  href={"/tasks/" + task.id}
                >
                  继续
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </article>
            ))
          : null}
      </div>
    </section>
  );
}

function RecentPlaceholder({ label }: { label: string }) {
  return <div className="rounded-lg border border-dashed border-[#d8e0eb] bg-white/68 px-4 py-5 text-center text-sm text-[#607089]">{label}</div>;
}

function TaskStatus({ status }: { status: string }) {
  const done = status === "completed";
  return (
    <span
      className={
        done
          ? "inline-flex w-fit rounded-full bg-[#e8fbf5] px-2.5 py-1 text-xs font-semibold text-[#087a67]"
          : "inline-flex w-fit rounded-full bg-[#fff7e8] px-2.5 py-1 text-xs font-semibold text-[#936213]"
      }
    >
      {statusLabel(status)}
    </span>
  );
}

function validateTargetCount(value: string) {
  const count = Number(value);
  if (!value || !Number.isFinite(count) || count < 1) {
    return "请输入 1 到 200 条";
  }
  if (count > MAX_TARGET_COUNT) {
    return "最多不超过 200 条，请减少目标数量";
  }
  return "";
}

function groupCitiesByTier(cities: SupportedCity[]) {
  return cities.reduce<Record<string, SupportedCity[]>>((groups, city) => {
    const tier = city.tier || "other";
    groups[tier] = [...(groups[tier] ?? []), city];
    return groups;
  }, {});
}

function tierLabel(value: string) {
  const labels: Record<string, string> = {
    first: "一线城市",
    new_first: "新一线城市",
    second: "二线城市",
  };
  return labels[value] ?? "其他城市";
}

function cityLabel(value: string) {
  const labels: Record<string, string> = {
    Hangzhou: "杭州",
    Guangzhou: "广州",
  };
  return labels[value] ?? value;
}

function cityLabelOnly(cities: SupportedCity[], value: string) {
  const city = cities.find((item) => item.name === value);
  return city?.name ?? (value || "选择城市");
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

function normalizeLoadError(error: unknown) {
  if (error instanceof TypeError) {
    return "无法连接后端服务，请确认 Backend 正在 http://127.0.0.1:8000 运行。";
  }
  return error instanceof Error ? error.message : "任务加载失败";
}
