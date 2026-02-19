import { ClipboardList } from 'lucide-react';
import type { TaskSummary } from '@/types/task';
import { TaskCard } from './TaskCard';

interface TaskGridProps {
  tasks: TaskSummary[];
  onSelectTask: (id: string) => void;
}

export function TaskGrid({ tasks, onSelectTask }: TaskGridProps) {
  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <ClipboardList className="size-12 text-muted-foreground mb-3" />
        <p className="text-muted-foreground text-sm">No tasks yet.</p>
        <p className="text-muted-foreground text-sm mt-1">
          Create your first task to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onClick={() => onSelectTask(task.id)}
        />
      ))}
    </div>
  );
}
