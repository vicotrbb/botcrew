import { Check, ChevronDown, Plus } from 'lucide-react';
import type { Channel } from '@/types/channel';
import type { AgentSummary } from '@/types/agent';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ChannelSelectorProps {
  channels: Channel[];
  activeChannelId: string | null;
  onChannelSelect: (id: string) => void;
  onCreateChannel: () => void;
  unreadCounts: Record<string, number>;
  agents: AgentSummary[];
  dmChannelMap: Record<string, string>;
  onAgentDmSelect: (agentId: string) => void;
}

export function ChannelSelector({
  channels,
  activeChannelId,
  onChannelSelect,
  onCreateChannel,
  unreadCounts,
  agents,
  dmChannelMap,
  onAgentDmSelect,
}: ChannelSelectorProps) {
  const activeChannel = channels.find((ch) => ch.id === activeChannelId);
  const nonDmChannels = channels.filter((ch) => ch.channel_type !== 'dm');

  // For DM channels, find the agent name from the agents list
  let triggerLabel = activeChannel?.name ?? 'Select Channel';
  if (activeChannel?.channel_type === 'dm' && activeChannel.description) {
    const dmAgent = agents.find((a) => a.id === activeChannel.description);
    if (dmAgent) triggerLabel = `DM: ${dmAgent.name}`;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1 max-w-[200px]">
          <span className="truncate text-sm font-medium">{triggerLabel}</span>
          <ChevronDown className="size-3.5 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-64">
        {nonDmChannels.map((channel) => {
          const isActive = channel.id === activeChannelId;
          const unread = unreadCounts[channel.id] ?? 0;

          return (
            <DropdownMenuItem
              key={channel.id}
              className={cn('flex items-center gap-2', isActive && 'bg-accent')}
              onSelect={() => onChannelSelect(channel.id)}
            >
              {/* Check icon for active channel */}
              <span className="w-4 shrink-0">
                {isActive && <Check className="size-4" />}
              </span>

              {/* Channel name */}
              <span
                className={cn(
                  'flex-1 truncate text-sm',
                  unread > 0 && 'font-bold',
                )}
              >
                {channel.name}
              </span>

              {/* Channel type label */}
              <span className="text-[10px] text-muted-foreground shrink-0">
                {channel.channel_type}
              </span>

              {/* Unread count badge */}
              {unread > 0 && (
                <Badge variant="secondary" className="h-5 min-w-5 px-1 text-[10px]">
                  {unread}
                </Badge>
              )}
            </DropdownMenuItem>
          );
        })}

        <DropdownMenuSeparator />

        <DropdownMenuItem onSelect={onCreateChannel}>
          <Plus className="size-4" />
          <span className="text-sm">New Channel</span>
        </DropdownMenuItem>

        {agents.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Direct Messages
            </div>
            {agents.map((agent) => {
              const dmChannelId = dmChannelMap[agent.id];
              const isActive = dmChannelId === activeChannelId;

              return (
                <DropdownMenuItem
                  key={`dm-${agent.id}`}
                  className={cn('flex items-center gap-2', isActive && 'bg-accent')}
                  onSelect={() => onAgentDmSelect(agent.id)}
                >
                  <span className="w-4 shrink-0">
                    {isActive && <Check className="size-4" />}
                  </span>
                  <AgentAvatar name={agent.name} size={20} />
                  <span className="flex-1 truncate text-sm">{agent.name}</span>
                  <span className="text-[10px] text-muted-foreground shrink-0">dm</span>
                </DropdownMenuItem>
              );
            })}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
