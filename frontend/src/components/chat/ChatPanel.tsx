import { useEffect, useMemo, useState } from 'react';
import { MoreHorizontal, X } from 'lucide-react';
import { toast } from 'sonner';
import { useWebSocket } from '@/hooks/use-websocket';
import { useChannels, useDeleteChannel, useGetDmChannel } from '@/hooks/use-channels';
import { useAgents } from '@/hooks/use-agents';
import { useChatStore } from '@/stores/chat-store';
import { getUnreadCount } from '@/api/messages';
import type { Channel } from '@/types/channel';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ChannelSelector } from './ChannelSelector';
import { CreateChannelDialog } from './CreateChannelDialog';
import { DeleteChannelDialog } from './DeleteChannelDialog';
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
  const deleteChannel = useDeleteChannel();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Find the active channel
  const activeChannel = (channels.data ?? []).find(
    (ch) => ch.id === activeChannelId,
  );

  // Only custom channels can be deleted
  const canDelete = activeChannel?.channel_type === 'custom';

  // Auto-select first channel on mount (prefer project > task > custom > any)
  useEffect(() => {
    if (activeChannelId) return;
    if (!channels.data || channels.data.length === 0) return;

    const project = channels.data.find((ch) => ch.channel_type === 'project');
    const task = channels.data.find((ch) => ch.channel_type === 'task');
    const custom = channels.data.find(
      (ch) => ch.channel_type === 'custom' || ch.channel_type === 'shared',
    );
    const fallback = channels.data[0];
    setActiveChannel((project ?? task ?? custom ?? fallback).id);
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

  const agents = agentsQuery.data ?? [];

  // Determine display name for the header
  let displayName = activeChannel?.name ?? 'Select Channel';
  if (activeChannel?.channel_type === 'dm' && activeChannel.description) {
    const dmAgent = agents.find((a) => a.id === activeChannel.description);
    if (dmAgent) displayName = `DM: ${dmAgent.name}`;
  }

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

  function handleDeleteChannel() {
    if (!activeChannelId) return;
    deleteChannel.mutate(activeChannelId, {
      onSuccess: () => {
        toast.success('Channel deleted');
        setDeleteDialogOpen(false);
        setActiveChannel(null); // clear active channel so auto-select picks next
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
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
      {/* Header bar with channel name + actions */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="text-sm font-medium truncate">{displayName}</span>
        <div className="flex items-center gap-1">
          {canDelete && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-xs" aria-label="Channel options">
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-destructive"
                  onSelect={() => setDeleteDialogOpen(true)}
                >
                  Delete Channel
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <Button variant="ghost" size="icon-xs" onClick={toggle} aria-label="Close chat">
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {/* Channel selector sidebar (scrollable) */}
      <ChannelSelector
        channels={channels.data ?? []}
        activeChannelId={activeChannelId}
        onChannelSelect={handleChannelSelect}
        onCreateChannel={() => setShowCreateDialog(true)}
        unreadCounts={unreadCounts}
        agents={agents}
        dmChannelMap={dmChannelMap}
        onAgentDmSelect={handleAgentDmSelect}
      />

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

      {/* Dialogs */}
      <CreateChannelDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
      <DeleteChannelDialog
        channelName={activeChannel?.name ?? ''}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        isPending={deleteChannel.isPending}
        onConfirm={handleDeleteChannel}
      />
    </div>
  );
}
