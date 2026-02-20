import type { Channel } from '@/types/channel';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { AgentAvatar } from '@/components/shared/AgentAvatar';

interface ChannelItemProps {
  channel: Channel;
  isActive: boolean;
  unreadCount: number;
  onClick: () => void;
  agentName?: string;
}

export function ChannelItem({
  channel,
  isActive,
  unreadCount,
  onClick,
  agentName,
}: ChannelItemProps) {
  const isDm = channel.channel_type === 'dm';
  const displayName = isDm && agentName ? `DM: ${agentName}` : channel.name;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 w-full rounded-md px-2 py-1.5 text-left hover:bg-accent/50 transition-colors',
        isActive && 'bg-accent',
      )}
    >
      {isDm && agentName && <AgentAvatar name={agentName} size={20} />}

      <span
        className={cn(
          'flex-1 truncate text-sm',
          unreadCount > 0 && 'font-bold',
        )}
      >
        {displayName}
      </span>

      <span className="text-[10px] text-muted-foreground shrink-0">
        {channel.channel_type}
      </span>

      {unreadCount > 0 && (
        <Badge variant="secondary" className="h-5 min-w-5 px-1 text-[10px]">
          {unreadCount}
        </Badge>
      )}
    </button>
  );
}
