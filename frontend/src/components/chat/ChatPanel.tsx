import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { useWebSocket } from '@/hooks/use-websocket';
import { useChannels, useGetDmChannel } from '@/hooks/use-channels';
import { useAgents } from '@/hooks/use-agents';
import { useChatStore } from '@/stores/chat-store';
import { getUnreadCount } from '@/api/messages';
import type { Channel } from '@/types/channel';
import { Button } from '@/components/ui/button';
import { ChannelSelector } from './ChannelSelector';
import { CreateChannelDialog } from './CreateChannelDialog';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

/**
 * Poll unread counts for all non-active channels every 15 seconds.
 * Updates the chat store so the ChannelSelector can display badges.
 */
function useUnreadPolling(channels: Channel[], activeChannelId: string | null) {
  const setUnreadCount = useChatStore((s) => s.setUnreadCount);

  useEffect(() => {
    if (!channels.length) return;

    const inactiveChannels = channels.filter((c) => c.id !== activeChannelId);
    if (!inactiveChannels.length) return;

    async function pollUnread() {
      for (const channel of inactiveChannels) {
        try {
          const result = await getUnreadCount(channel.id);
          setUnreadCount(channel.id, result.unread_count);
        } catch {
          // Ignore polling errors silently
        }
      }
    }

    void pollUnread(); // Initial fetch
    const interval = setInterval(() => void pollUnread(), 15_000);
    return () => clearInterval(interval);
  }, [channels, activeChannelId, setUnreadCount]);
}

export function ChatPanel() {
  const { activeChannelId, setActiveChannel, clearUnread, unreadCounts, toggle } =
    useChatStore();
  const channels = useChannels();
  const agentsQuery = useAgents();
  const getDmChannel = useGetDmChannel();
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // Auto-select first shared channel on mount
  useEffect(() => {
    if (activeChannelId) return;
    if (!channels.data || channels.data.length === 0) return;

    const shared = channels.data.find((ch) => ch.channel_type === 'shared');
    const fallback = channels.data[0];
    setActiveChannel((shared ?? fallback).id);
  }, [activeChannelId, channels.data, setActiveChannel]);

  // Poll unread counts for non-active channels
  useUnreadPolling(channels.data ?? [], activeChannelId);

  // Connect WebSocket at panel level, pass sendMessage down
  const { status: wsStatus, sendMessage: wsSendMessage } =
    useWebSocket(activeChannelId);

  // Build agent_id -> dm_channel_id map from existing DM channels
  const dmChannelMap = useMemo(() => {
    if (!channels.data) return {};
    const map: Record<string, string> = {};
    for (const ch of channels.data) {
      if (ch.channel_type === 'dm' && ch.description) {
        // DM channel description stores the agent_id (set by backend)
        map[ch.description] = ch.id;
      }
    }
    return map;
  }, [channels.data]);

  function handleChannelSelect(channelId: string) {
    clearUnread(channelId);
    setActiveChannel(channelId);
    // WebSocket automatically reconnects via useWebSocket(channelId) dependency
  }

  async function handleAgentDmSelect(agentId: string) {
    // Check if DM channel already exists
    const existingChannelId = dmChannelMap[agentId];
    if (existingChannelId) {
      clearUnread(existingChannelId);
      setActiveChannel(existingChannelId);
      return;
    }

    // Create DM channel lazily via backend
    try {
      const channel = await getDmChannel.mutateAsync(agentId);
      setActiveChannel(channel.id);
    } catch {
      // DM channel creation failed silently
    }
  }

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
            No channels available.{' '}
            <button
              className="underline hover:text-foreground"
              onClick={() => setShowCreateDialog(true)}
            >
              Create one
            </button>
          </p>
        </div>
        <CreateChannelDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <ChannelSelector
          channels={channels.data ?? []}
          activeChannelId={activeChannelId}
          onChannelSelect={handleChannelSelect}
          onCreateChannel={() => setShowCreateDialog(true)}
          unreadCounts={unreadCounts}
          agents={agentsQuery.data ?? []}
          dmChannelMap={dmChannelMap}
          onAgentDmSelect={handleAgentDmSelect}
        />
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

      {/* Create channel dialog */}
      <CreateChannelDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
    </div>
  );
}
