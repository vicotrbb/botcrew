import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useAgents } from '@/hooks/use-agents';
import { useCreateChannel } from '@/hooks/use-channels';
import { useChatStore } from '@/stores/chat-store';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';

interface CreateChannelDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateChannelDialog({ open, onOpenChange }: CreateChannelDialogProps) {
  const [name, setName] = useState('');
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const agents = useAgents();
  const createChannel = useCreateChannel();
  const setActiveChannel = useChatStore((s) => s.setActiveChannel);

  const isNameValid = name.trim().length > 0 && name.trim().length <= 100;
  const hasAgents = selectedAgentIds.length > 0;
  const canSubmit = isNameValid && hasAgents && !createChannel.isPending;

  function handleAgentToggle(agentId: string, checked: boolean) {
    setSelectedAgentIds((prev) =>
      checked ? [...prev, agentId] : prev.filter((id) => id !== agentId),
    );
  }

  function resetForm() {
    setName('');
    setSelectedAgentIds([]);
    setError(null);
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      resetForm();
    }
    onOpenChange(nextOpen);
  }

  async function handleSubmit() {
    if (!canSubmit) return;

    setError(null);
    const clientId = sessionStorage.getItem('botcrew_client_id') || '';

    try {
      const channel = await createChannel.mutateAsync({
        name: name.trim(),
        channel_type: 'custom',
        agent_ids: selectedAgentIds,
        creator_user_identifier: clientId,
      });

      setActiveChannel(channel.id);
      resetForm();
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to create channel';
      setError(message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Channel</DialogTitle>
          <DialogDescription>
            Create a custom channel with specific agents.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Channel name */}
          <div className="space-y-2">
            <Label htmlFor="channel-name">Channel Name</Label>
            <Input
              id="channel-name"
              placeholder="e.g. Project Discussion"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              autoFocus
            />
          </div>

          {/* Agent selection */}
          <div className="space-y-2">
            <Label>
              Agents{' '}
              <span className="text-muted-foreground font-normal">
                ({selectedAgentIds.length} selected)
              </span>
            </Label>

            {agents.isLoading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="size-4 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Loading agents...</span>
              </div>
            )}

            {agents.isSuccess && agents.data.length === 0 && (
              <p className="text-sm text-muted-foreground py-2">
                No agents available. Create an agent first.
              </p>
            )}

            {agents.isSuccess && agents.data.length > 0 && (
              <ScrollArea className="h-[200px] rounded-md border p-2">
                <div className="space-y-1">
                  {agents.data.map((agent) => {
                    const isChecked = selectedAgentIds.includes(agent.id);
                    return (
                      <label
                        key={agent.id}
                        className="flex items-center gap-3 rounded-md px-2 py-1.5 hover:bg-accent cursor-pointer"
                      >
                        <Checkbox
                          checked={isChecked}
                          onCheckedChange={(checked) =>
                            handleAgentToggle(agent.id, checked === true)
                          }
                        />
                        <AgentAvatar name={agent.name} size={24} />
                        <span className="flex-1 text-sm truncate">{agent.name}</span>
                        <StatusBadge status={agent.status} size="sm" showLabel={false} />
                      </label>
                    );
                  })}
                </div>
              </ScrollArea>
            )}

            {!hasAgents && selectedAgentIds !== undefined && (
              <p className="text-xs text-muted-foreground">
                Select at least one agent to include in the channel.
              </p>
            )}
          </div>

          {/* Error message */}
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={createChannel.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={() => void handleSubmit()}
            disabled={!canSubmit}
          >
            {createChannel.isPending && (
              <Loader2 className="size-4 animate-spin mr-2" />
            )}
            Create Channel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
