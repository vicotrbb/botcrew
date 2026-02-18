import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Loader2 } from 'lucide-react';
import type { IntegrationSummary } from '@/types/integration';
import { useAgents } from '@/hooks/use-agents';
import { useCreateIntegration, useUpdateIntegration } from '@/hooks/use-integrations';
import { discordIntegrationSchema, type DiscordIntegrationInput } from '@/lib/schemas';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface DiscordSectionProps {
  integrations: IntegrationSummary[];
  onDelete: (id: string, name: string) => void;
  onToggleActive: (id: string, isActive: boolean) => void;
}

export function DiscordSection({ integrations, onDelete, onToggleActive }: DiscordSectionProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const agents = useAgents();
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
        Add Discord Webhook
      </Button>

      <DiscordDialog
        open={dialogOpen}
        onOpenChange={(open) => { if (!open) handleDialogClose(); else setDialogOpen(true); }}
        editingId={editingId}
        editingIntegration={editingId ? integrations.find((i) => i.id === editingId) : undefined}
        agents={agents.data ?? []}
        createMutation={createIntegration}
      />
    </div>
  );
}

interface DiscordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingId: string | null;
  editingIntegration?: IntegrationSummary;
  agents: { id: string; name: string }[];
  createMutation: ReturnType<typeof useCreateIntegration>;
}

function DiscordDialog({
  open,
  onOpenChange,
  editingId,
  editingIntegration,
  agents,
  createMutation,
}: DiscordDialogProps) {
  const isEditing = editingId !== null;
  const updateMutation = useUpdateIntegration(editingId ?? '');

  const defaultValues = getDefaults(editingIntegration);
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<DiscordIntegrationInput>({
    resolver: zodResolver(discordIntegrationSchema),
    defaultValues,
  });

  const agentId = watch('agent_id');

  // Reset form when dialog opens/closes or editing changes
  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      reset(getDefaults(undefined));
    } else if (editingIntegration) {
      reset(getDefaults(editingIntegration));
    }
    onOpenChange(nextOpen);
  }

  async function onSubmit(data: DiscordIntegrationInput) {
    try {
      if (isEditing && editingId) {
        await updateMutation.mutateAsync({
          name: data.name,
          config: JSON.stringify({ webhook_url: data.webhook_url }),
          agent_id: data.agent_id || null,
          channel_id: data.channel_id || null,
        });
      } else {
        await createMutation.mutateAsync({
          name: data.name,
          integration_type: 'discord',
          config: JSON.stringify({ webhook_url: data.webhook_url }),
          agent_id: data.agent_id,
          channel_id: data.channel_id,
        });
      }
      handleOpenChange(false);
    } catch {
      // Error displayed by mutation state
    }
  }

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutationError = isEditing ? updateMutation.error : createMutation.error;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Discord Integration' : 'Add Discord Webhook'}</DialogTitle>
          <DialogDescription>Configure a Discord webhook integration.</DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="discord-name">Name</Label>
            <Input id="discord-name" placeholder="e.g. #general notifications" {...register('name')} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="discord-webhook">Webhook URL</Label>
            <Input id="discord-webhook" placeholder="https://discord.com/api/webhooks/..." {...register('webhook_url')} />
            {errors.webhook_url && <p className="text-xs text-destructive">{errors.webhook_url.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="discord-agent">Agent (optional)</Label>
            <Select
              value={agentId ?? ''}
              onValueChange={(v) => setValue('agent_id', v || undefined)}
            >
              <SelectTrigger id="discord-agent" className="w-full">
                <SelectValue placeholder="Select an agent..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">None</SelectItem>
                {agents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="discord-channel">Channel ID (optional)</Label>
            <Input id="discord-channel" placeholder="Channel ID" {...register('channel_id')} />
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

function getDefaults(integration?: IntegrationSummary): DiscordIntegrationInput {
  if (!integration) return { name: '', webhook_url: '' };
  let config: Record<string, unknown> = {};
  try {
    config = JSON.parse(integration.config) as Record<string, unknown>;
  } catch { /* empty */ }
  return {
    name: integration.name,
    webhook_url: (config.webhook_url as string) || '',
    agent_id: integration.agent_id ?? undefined,
    channel_id: integration.channel_id ?? undefined,
  };
}
