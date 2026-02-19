import type { TaskSummary } from '@/types/task';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface TaskCardProps {
  task: TaskSummary;
  onClick: () => void;
}

export function TaskCard({ task, onClick }: TaskCardProps) {
  return (
    <Card
      className="p-4 cursor-pointer transition-all duration-200 hover:border-primary/50 hover:shadow-md"
      onClick={onClick}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium truncate block">{task.name}</span>
        <Badge
          variant={task.status === 'done' ? 'outline' : 'secondary'}
          className={
            task.status === 'done'
              ? 'text-xs shrink-0 text-green-600 border-green-300'
              : 'text-xs shrink-0'
          }
        >
          {task.status}
        </Badge>
      </div>

      <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
        {task.description ?? 'No description'}
      </p>
    </Card>
  );
}
