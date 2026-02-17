import { Check, ChevronDown, Plus } from 'lucide-react';
import type { Channel } from '@/types/channel';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
}

export function ChannelSelector({
  channels,
  activeChannelId,
  onChannelSelect,
  onCreateChannel,
  unreadCounts,
}: ChannelSelectorProps) {
  const activeChannel = channels.find((ch) => ch.id === activeChannelId);
  const triggerLabel = activeChannel?.name ?? 'Select Channel';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1 max-w-[200px]">
          <span className="truncate text-sm font-medium">{triggerLabel}</span>
          <ChevronDown className="size-3.5 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-64">
        {channels.map((channel) => {
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
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
