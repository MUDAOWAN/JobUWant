export function formatCount(value: number | undefined) {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

export function formatPercent(part: number, total: number) {
  if (!total) {
    return "0%";
  }
  return `${Math.round((part / total) * 100)}%`;
}

export function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: "已完成",
    running: "运行中",
    failed: "失败",
    pending: "等待中",
    missing_fixture: "样本缺失",
  };
  return labels[status] ?? status;
}
