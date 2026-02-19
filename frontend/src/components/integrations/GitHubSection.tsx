import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import type { IntegrationSummary } from '@/types/integration';
import { useCreateIntegration, useUpdateIntegration } from '@/hooks/use-integrations';
import { githubIntegrationSchema, type GitHubIntegrationInput } from '@/lib/schemas';
import { IntegrationCard } from '@/components/integrations/IntegrationCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface GitHubSectionProps {
  integrations: IntegrationSummary[];
  onDelete: (id: string, name: string) => void;
  onToggleActive: (id: string, isActive: boolean) => void;
}

export function GitHubSection({ integrations, onDelete, onToggleActive }: GitHubSectionProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const createIntegration = useCreateIntegration();

  function handleEdit(id: string) {
    setEditingId(id);
    setDialogOpen(true);
  }

  function handleCreate() {
    setEditingId(null);
    setDialogOpen(true);
  }

  function handleDialogClose() {
    setDialogOpen(false);
    setEditingId(null);
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {integrations.map((integration) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            onEdit={handleEdit}
            onDelete={(id) => onDelete(id, integration.name)}
            onToggleActive={onToggleActive}
          />
        ))}
      </div>

      <Button variant="outline" size="sm" onClick={handleCreate}>
        <Plus className="size-4" />
        Add GitHub Token
      </Button>

      <GitHubDialog
        open={dialogOpen}
        onOpenChange={(open) => { if (!open) handleDialogClose(); else setDialogOpen(true); }}
        editingId={editingId}
        editingIntegration={editingId ? integrations.find((i) => i.id === editingId) : undefined}
        createMutation={createIntegration}
      />
    </div>
  );
}

interface GitHubDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingId: string | null;
  editingIntegration?: IntegrationSummary;
  createMutation: ReturnType<typeof useCreateIntegration>;
}

function GitHubDialog({
  open,
  onOpenChange,
  editingId,
  editingIntegration,
  createMutation,
}: GitHubDialogProps) {
  const isEditing = editingId !== null;
  const updateMutation = useUpdateIntegration(editingId ?? '');

  const defaultValues = getDefaults(editingIntegration);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<GitHubIntegrationInput>({
    resolver: zodResolver(githubIntegrationSchema),
    defaultValues,
  });

  useEffect(() => {
    if (open && editingIntegration) {
      reset(getDefaults(editingIntegration));
    } else if (open && !editingIntegration) {
      reset(getDefaults(undefined));
    }
  }, [open, editingIntegration, reset]);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      reset(getDefaults(undefined));
    } else if (editingIntegration) {
      reset(getDefaults(editingIntegration));
    }
    onOpenChange(nextOpen);
  }

  async function onSubmit(data: GitHubIntegrationInput) {
    try {
      if (isEditing && editingId) {
        await updateMutation.mutateAsync({
          name: data.name,
          config: JSON.stringify({ token: data.token, default_org: data.default_org }),
        });
        toast.success('GitHub integration updated');
      } else {
        await createMutation.mutateAsync({
          name: data.name,
          integration_type: 'github',
          config: JSON.stringify({ token: data.token, default_org: data.default_org }),
        });
        toast.success('GitHub integration created');
      }
      handleOpenChange(false);
    } catch {
      toast.error('Something went wrong. Please try again.');
    }
  }

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutationError = isEditing ? updateMutation.error : createMutation.error;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit GitHub Integration' : 'Add GitHub Token'}</DialogTitle>
          <DialogDescription>Configure a GitHub personal access token.</DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="gh-name">Name</Label>
            <Input id="gh-name" placeholder="e.g. GitHub Personal" {...register('name')} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="gh-token">Token</Label>
            <Input id="gh-token" type="password" placeholder="ghp_..." {...register('token')} />
            {errors.token && <p className="text-xs text-destructive">{errors.token.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="gh-org">Default Organization (optional)</Label>
            <Input id="gh-org" placeholder="e.g. my-org" {...register('default_org')} />
          </div>

          {mutationError && (
            <p className="text-sm text-destructive">
              {mutationError instanceof Error ? mutationError.message : 'Operation failed'}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="size-4 animate-spin mr-2" />}
              {isEditing ? 'Save Changes' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function getDefaults(integration?: IntegrationSummary): GitHubIntegrationInput {
  if (!integration) return { name: '', token: '' };
  let config: Record<string, unknown> = {};
  try {
    config = JSON.parse(integration.config) as Record<string, unknown>;
  } catch { /* empty */ }
  return {
    name: integration.name,
    token: (config.token as string) || '',
    default_org: (config.default_org as string) || undefined,
  };
}
