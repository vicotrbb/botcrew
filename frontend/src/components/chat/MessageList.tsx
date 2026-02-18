import { useEffect, useMemo, useRef } from 'react';
import type { ConnectionStatus } from '@/hooks/use-websocket';
import { useMessages } from '@/hooks/use-messages';
import { useAgents } from '@/hooks/use-agents';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageBubble } from './MessageBubble';
import { Loader2 } from 'lucide-react';

interface MessageListProps {
  channelId: string;
  wsStatus: ConnectionStatus;
}

export function MessageList({ channelId, wsStatus }: MessageListProps) {
  const messages = useMessages(channelId);
  const agents = useAgents();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Build agent ID -> name lookup map
  const agentNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const agent of agents.data ?? []) {
      map.set(agent.id, agent.name);
    }
    return map;
  }, [agents.data]);

  // API returns newest first -- reverse for chronological display (oldest at top)
  const chronologicalMessages = useMemo(
    () => [...(messages.data?.items ?? [])].reverse(),
    [messages.data],
  );

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chronologicalMessages.length]);

  // Loading state
  if (messages.isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (messages.isError) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 px-4">
        <p className="text-sm text-destructive">Failed to load messages</p>
        <button
          type="button"
          onClick={() => void messages.refetch()}
          className="text-sm text-primary hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  // Empty state
  if (chronologicalMessages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-4">
        <p className="text-sm text-muted-foreground text-center">
          No messages yet. Say something!
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1 min-h-0">
      <div className="flex flex-col gap-3 p-4">
        {chronologicalMessages.map((message) => (
          <MessageBubble key={message.id} message={message} agentNames={agentNames} />
        ))}
        <div ref={bottomRef} />
      </div>
      {wsStatus === 'reconnecting' && (
        <div className="text-center text-xs text-muted-foreground py-1">
          Reconnecting...
        </div>
      )}
    </ScrollArea>
  );
}
