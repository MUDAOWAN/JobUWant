import type { ReactNode } from "react";

export const panelClass = "rounded-lg border border-[#d9dee8] bg-white shadow-[0_6px_18px_rgba(23,32,51,0.06)]";
export const primaryButtonClass =
  "inline-flex h-10 items-center justify-center gap-2 rounded-md bg-[#2364aa] px-3 text-sm font-medium text-white shadow-sm transition hover:bg-[#1f5794] disabled:cursor-not-allowed disabled:bg-[#9aa4b4]";
export const secondaryButtonClass =
  "inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#d9dee8] bg-white px-3 text-sm font-medium shadow-sm transition hover:border-[#2364aa] hover:text-[#2364aa] disabled:cursor-not-allowed disabled:border-[#e8ecf2] disabled:bg-[#f8fafc] disabled:text-[#9aa4b4]";

type AppShellProps = {
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function AppShell({ title, eyebrow = "JobUWant Web App", actions, children }: AppShellProps) {
  return (
    <main className="min-h-screen bg-[#f4f7fb] text-[#172033]">
      <header className="border-b border-[#e8ecf2] bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            {eyebrow ? <p className="text-sm font-medium text-[#2364aa]">{eyebrow}</p> : null}
            <h1 className={eyebrow ? "mt-1 text-2xl font-semibold" : "text-2xl font-semibold"}>{title}</h1>
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
        </div>
      </header>
      {children}
    </main>
  );
}

export function PageBody({ children, className = "space-y-5" }: { children: ReactNode; className?: string }) {
  return <div className={`mx-auto max-w-7xl px-5 py-5 ${className}`}>{children}</div>;
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`${panelClass} ${className}`}>{children}</section>;
}

export function PanelHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-col gap-4 border-b border-[#e8ecf2] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-[#647086]">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-col gap-3 sm:flex-row sm:items-center">{actions}</div> : null}
    </div>
  );
}

export function StatusPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex h-10 items-center gap-2 rounded-md border border-[#d9dee8] bg-white px-3 text-sm text-[#647086] shadow-sm">
      <span className="h-2 w-2 rounded-full bg-[#2f9f7f]" />
      <span className="font-medium text-[#172033]">{label}</span>
      <span>{value}</span>
    </span>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  if (!message) {
    return null;
  }
  return <section className="rounded-lg border border-[#f0b8b8] bg-[#fff7f7] px-4 py-3 text-sm text-[#b42318]">{message}</section>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className={`${panelClass} px-4 py-8 text-center text-sm text-[#647086]`}>{message}</div>;
}

export function MetricBlock({ label, value, helper, icon }: { label: string; value: string; helper?: string; icon?: ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm text-[#647086]">
        {icon}
        <span>{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
      {helper ? <div className="mt-1 text-xs text-[#647086]">{helper}</div> : null}
    </div>
  );
}

