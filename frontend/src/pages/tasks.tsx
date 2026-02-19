import { useState } from 'react';
import { Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { useTasks } from '@/hooks/use-tasks';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { TaskGrid } from '@/components/tasks/TaskGrid';
import { TaskSheet } from '@/components/tasks/TaskSheet';

function TaskCardSkeleton() {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <div className="h-4 w-32 bg-muted animate-pulse rounded" />
        <div className="h-5 w-16 bg-muted animate-pulse rounded-full" />
      </div>
      <div className="mt-2 space-y-1">
        <div className="h-3 w-full bg-muted animate-pulse rounded" />
        <div className="h-3 w-3/4 bg-muted animate-pulse rounded" />
      </div>
    </Card>
  );
}

export function TasksPage() {
  const { data, isLoading, error, refetch } = useTasks();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [createMode, setCreateMode] = useState(false);

  function handleSelectTask(id: string) {
    setSelectedTaskId(id);
    setCreateMode(false);
    setSheetOpen(true);
  }

  function handleCreateClick() {
    setSelectedTaskId(null);
    setCreateMode(true);
    setSheetOpen(true);
  }

  function handleSheetOpenChange(open: boolean) {
    setSheetOpen(open);
    if (!open) {
      setSelectedTaskId(null);
      setCreateMode(false);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tasks</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage your tasks and work directives
          </p>
        </div>
        <Button onClick={handleCreateClick}>
          <Plus className="size-4" />
          Create Task
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <TaskCardSkeleton key={i} />
          ))}
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="size-8 text-destructive mb-3" />
          <p className="text-sm text-muted-foreground mb-4">
            Failed to load tasks.{' '}
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void refetch();
            }}
          >
            <RefreshCw className="size-4" />
            Retry
          </Button>
        </div>
      )}

      {data && <TaskGrid tasks={data} onSelectTask={handleSelectTask} />}

      <TaskSheet
        taskId={createMode ? null : selectedTaskId}
        open={sheetOpen}
        onOpenChange={handleSheetOpenChange}
      />
    </div>
  );
}
