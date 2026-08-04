import { TaskWorkspace } from "@/features/tasks/task-workspace";

type PageProps = {
  params: Promise<{
    taskId: string;
  }>;
};

export default async function TaskReportInputPage({ params }: PageProps) {
  const { taskId } = await params;
  return <TaskWorkspace activeView="reportInput" initialTaskId={taskId} />;
}