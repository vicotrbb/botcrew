import { useState, useEffect } from 'react';
import { Loader2, Trash2, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  useProject,
  useUpdateProject,
  useDeleteProject,
  useSyncProject,
} from '@/hooks/use-projects';
import type { UpdateProjectFormInput } from '@/lib/schemas';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ProjectForm } from './ProjectForm';
import { AgentAssignment } from './AgentAssignment';
import { SecretAssignment } from './SecretAssignment';
import { FileExplorer } from './FileExplorer';

interface ProjectDetailSheetProps {
  projectId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProjectDetailSheet({
  projectId,
  open,
  onOpenChange,
}: ProjectDetailSheetProps) {
  const { data: project, isLoading } = useProject(projectId);
  const updateProject = useUpdateProject(projectId ?? '');
  const deleteProject = useDeleteProject();
  const syncProject = useSyncProject();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Reset form key when project changes to force re-render
  const [formKey, setFormKey] = useState(0);
  useEffect(() => {
    if (project) {
      setFormKey((k) => k + 1);
    }
  }, [project]);

  function handleUpdate(data: UpdateProjectFormInput) {
    updateProject.mutate(data);
  }

  function handleDelete() {
    if (!projectId) return;
    deleteProject.mutate(projectId, {
      onSuccess: () => {
        setDeleteDialogOpen(false);
        onOpenChange(false);
      },
    });
  }

  function handleSync() {
    if (!projectId) return;
    syncProject.mutate(projectId);
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle>Project Details</SheetTitle>
          <SheetDescription>View and edit project configuration</SheetDescription>
        </SheetHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {project && (
          <div className="space-y-6 px-4 pb-6">
            {/* Edit form */}
            <ProjectForm
              key={formKey}
              mode="edit"
              defaultValues={{
                name: project.name,
                description: project.description ?? '',
                goals: project.goals ?? '',
                specs: project.specs ?? '',
                github_repo_url: project.github_repo_url ?? '',
              }}
              onSubmit={handleUpdate}
              isPending={updateProject.isPending}
              error={updateProject.error}
            />

            <Separator />

            {/* Agent assignment */}
            <AgentAssignment projectId={projectId!} />

            <Separator />

            {/* Secret assignment */}
            <SecretAssignment projectId={projectId!} />

            <Separator />

            {/* Workspace file explorer */}
            <FileExplorer projectId={projectId!} />

            <Separator />

            {/* Actions */}
            <div className="flex items-center gap-2">
              {project.github_repo_url && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSync}
                  disabled={syncProject.isPending}
                >
                  {syncProject.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="size-4" />
                      Sync GitHub
                    </>
                  )}
                </Button>
              )}

              <div className="flex-1" />

              <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="destructive" size="sm">
                    <Trash2 className="size-4" />
                    Delete
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <AlertTriangle className="size-5 text-destructive" />
                      Delete Project
                    </DialogTitle>
                    <DialogDescription>
                      Are you sure you want to delete{' '}
                      <strong>{project.name}</strong>? This will remove all
                      project data and agent assignments. This action cannot
                      be undone.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setDeleteDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDelete}
                      disabled={deleteProject.isPending}
                    >
                      {deleteProject.isPending ? (
                        <>
                          <Loader2 className="size-4 animate-spin" />
                          Deleting...
                        </>
                      ) : (
                        'Delete Project'
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
