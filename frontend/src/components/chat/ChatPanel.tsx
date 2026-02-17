import { useEffect } from 'react';
import { X } from 'lucide-react';
import { useWebSocket } from '@/hooks/use-websocket';
import { useChannels } from '@/hooks/use-channels';
import { useChatStore } from '@/stores/chat-store';
import { Button } from '@/components/ui/button';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

export function ChatPanel() {
  const { activeChannelId, setActiveChannel, toggle } = useChatStore();
  const channels = useChannels();

  // Auto-select first shared channel on mount
  useEffect(() => {
    if (activeChannelId) return;
    if (!channels.data || channels.data.length === 0) return;

    const shared = channels.data.find((ch) => ch.channel_type === 'shared');
    const fallback = channels.data[0];
    setActiveChannel((shared ?? fallback).id);
  }, [activeChannelId, channels.data, setActiveChannel]);

  // Get active channel name for display
  const activeChannel = channels.data?.find((ch) => ch.id === activeChannelId);
  const channelName = activeChannel?.name ?? 'Chat';

  // Connect WebSocket at panel level, pass sendMessage down
  const { status: wsStatus, sendMessage: wsSendMessage } =
    useWebSocket(activeChannelId);

  // No channels available
  if (channels.isSuccess && channels.data.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-medium">Chat</span>
          <Button variant="ghost" size="icon-xs" onClick={toggle} aria-label="Close chat">
            <X className="size-4" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center px-4">
          <p className="text-sm text-muted-foreground text-center">
            No channels available
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex flex-col min-w-0">
          <span className="text-sm font-medium truncate">{channelName}</span>
          {/* Channel selector placeholder for Plan 07 */}
        </div>
        <Button variant="ghost" size="icon-xs" onClick={toggle} aria-label="Close chat">
          <X className="size-4" />
        </Button>
      </div>

      {/* Message list */}
      {activeChannelId ? (
        <MessageList channelId={activeChannelId} wsStatus={wsStatus} />
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-muted-foreground">Loading channels...</p>
        </div>
      )}

      {/* Message input */}
      {activeChannelId && (
        <MessageInput
          channelId={activeChannelId}
          wsStatus={wsStatus}
          wsSendMessage={wsSendMessage}
          disabled={!activeChannelId}
        />
      )}
    </div>
  );
}
