import { useState } from 'react';
import { Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { useProjects, useCreateProject } from '@/hooks/use-projects';
import type { CreateProjectFormInput } from '@/lib/schemas';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { ProjectGrid } from '@/components/projects/ProjectGrid';
import { ProjectDetailSheet } from '@/components/projects/ProjectDetailSheet';
import { ProjectForm } from '@/components/projects/ProjectForm';

function ProjectCardSkeleton() {
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
      <div className="mt-3 h-3 w-20 bg-muted animate-pulse rounded" />
    </Card>
  );
}

export function ProjectsPage() {
  const { data, isLoading, error, refetch } = useProjects();
  const createProject = useCreateProject();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  function handleSelectProject(id: string) {
    setSelectedProjectId(id);
    setDetailOpen(true);
  }

  function handleCreate(input: CreateProjectFormInput) {
    createProject.mutate(input, {
      onSuccess: () => setCreateDialogOpen(false),
    });
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage your projects and workspaces
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="size-4" />
          Create Project
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <ProjectCardSkeleton key={i} />
          ))}
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="size-8 text-destructive mb-3" />
          <p className="text-sm text-muted-foreground mb-4">
            Failed to load projects.{' '}
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

      {data && (
        <ProjectGrid projects={data} onSelectProject={handleSelectProject} />
      )}

      {/* Create Project Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Project</DialogTitle>
            <DialogDescription>
              Set up a new project for your agents to work on.
            </DialogDescription>
          </DialogHeader>
          <ProjectForm
            mode="create"
            onSubmit={handleCreate}
            isPending={createProject.isPending}
            error={createProject.error}
          />
        </DialogContent>
      </Dialog>

      {/* Project Detail Sheet */}
      <ProjectDetailSheet
        projectId={selectedProjectId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
