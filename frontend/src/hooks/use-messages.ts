import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query';
import type { Message, SendMessageInput } from '@/types/message';
import type { UnreadResponse } from '@/types/message';
import { getMessages, sendMessage, getUnreadCount } from '@/api/messages';
import { UNREAD_POLL_INTERVAL } from '@/lib/constants';

/** Shape of the messages query data in the React Query cache. */
type MessagesQueryData = {
  items: Message[];
  meta?: { total_count?: number; has_next?: boolean; [key: string]: unknown };
  links?: { first?: string; next?: string };
};

/**
 * Fetch messages for a channel. API returns newest first.
 * Display components should reverse the array for chronological rendering.
 */
export function useMessages(channelId: string | null | undefined) {
  return useQuery<MessagesQueryData>({
    queryKey: ['messages', channelId],
    queryFn: () => getMessages(channelId!),
    enabled: !!channelId,
  });
}

/**
 * Send a message to a channel (REST fallback).
 * sendMessage() internally includes sender_user_identifier from sessionStorage.
 * Includes optimistic update so the message appears instantly in the UI.
 */
export function useSendMessage(channelId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SendMessageInput) => sendMessage(channelId, input),
    onMutate: async (input) => {
      // Cancel in-flight refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ['messages', channelId] });

      const previous = queryClient.getQueryData<MessagesQueryData>(['messages', channelId]);

      // Build an optimistic message (API returns newest first, so prepend)
      const optimistic: Message = {
        id: `optimistic-${crypto.randomUUID()}`,
        content: input.content,
        message_type: input.message_type ?? 'chat',
        sender_agent_id: null,
        sender_user_identifier: sessionStorage.getItem('botcrew_client_id') ?? '',
        channel_id: channelId,
        metadata: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      queryClient.setQueryData<MessagesQueryData>(['messages', channelId], (old) => {
        if (!old) return { items: [optimistic] };
        // API returns newest first, so prepend the new message
        return { ...old, items: [optimistic, ...old.items] };
      });

      return { previous };
    },
    onError: (_err, _input, context) => {
      // Roll back to the previous cache value on error
      if (context?.previous) {
        queryClient.setQueryData(['messages', channelId], context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after mutation to sync with server truth
      void queryClient.invalidateQueries({ queryKey: ['messages', channelId] });
    },
  });
}

/**
 * Add an optimistic message to the cache for a channel.
 * Used by the WebSocket send path (which bypasses useMutation) so the
 * message appears instantly in the UI without waiting for the WS echo
 * and subsequent invalidateQueries refetch.
 */
export function useOptimisticMessage(channelId: string) {
  const queryClient = useQueryClient();

  return (content: string) => {
    const optimistic: Message = {
      id: `optimistic-${crypto.randomUUID()}`,
      content,
      message_type: 'chat',
      sender_agent_id: null,
      sender_user_identifier: sessionStorage.getItem('botcrew_client_id') ?? '',
      channel_id: channelId,
      metadata: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    queryClient.setQueryData<MessagesQueryData>(['messages', channelId], (old) => {
      if (!old) return { items: [optimistic] };
      // API returns newest first, so prepend the new message
      return { ...old, items: [optimistic, ...old.items] };
    });
  };
}

/**
 * Fetch unread count for a single channel. Polls every 15 seconds.
 */
export function useUnreadCount(channelId: string | null | undefined) {
  return useQuery<UnreadResponse>({
    queryKey: ['unread', channelId],
    queryFn: () => getUnreadCount(channelId!),
    refetchInterval: UNREAD_POLL_INTERVAL,
    enabled: !!channelId,
  });
}

/**
 * Fetch unread counts for multiple channels in parallel.
 */
export function useUnreadCounts(channelIds: string[]) {
  return useQueries({
    queries: channelIds.map((channelId) => ({
      queryKey: ['unread', channelId] as const,
      queryFn: () => getUnreadCount(channelId),
      refetchInterval: UNREAD_POLL_INTERVAL,
      enabled: !!channelId,
    })),
  });
}
