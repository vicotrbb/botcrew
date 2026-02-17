import { useQuery, useMutation, useQueryClient, useQueries } from '@tanstack/react-query';
import type { Message, SendMessageInput } from '@/types/message';
import type { UnreadResponse } from '@/types/message';
import { getMessages, sendMessage, getUnreadCount } from '@/api/messages';
import { UNREAD_POLL_INTERVAL } from '@/lib/constants';

/**
 * Fetch messages for a channel. API returns newest first.
 * Display components should reverse the array for chronological rendering.
 */
export function useMessages(channelId: string | null | undefined) {
  return useQuery<{
    items: Message[];
    meta?: { total_count?: number; has_next?: boolean; [key: string]: unknown };
    links?: { first?: string; next?: string };
  }>({
    queryKey: ['messages', channelId],
    queryFn: () => getMessages(channelId!),
    enabled: !!channelId,
  });
}

/**
 * Send a message to a channel.
 * sendMessage() internally includes sender_user_identifier from sessionStorage.
 */
export function useSendMessage(channelId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SendMessageInput) => sendMessage(channelId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['messages', channelId] });
    },
  });
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
