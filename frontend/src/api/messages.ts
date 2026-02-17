import type { Message, SendMessageInput } from '@/types/message';
import type { UnreadResponse } from '@/types/message';
import { API_BASE, ApiError, fetchListWithMeta, postJSON } from '@/api/client';

/**
 * Get messages for a channel. Backend returns newest first.
 * The function returns messages as-is (newest first);
 * display components are responsible for reversing if needed.
 */
export async function getMessages(
  channelId: string,
  cursor?: string,
): Promise<{
  items: Message[];
  meta?: { total_count?: number; has_next?: boolean; [key: string]: unknown };
  links?: { first?: string; next?: string };
}> {
  let path = `/channels/${channelId}/messages`;
  if (cursor) {
    path += `?before=${encodeURIComponent(cursor)}`;
  }
  return fetchListWithMeta<Omit<Message, 'id'>>(path);
}

/**
 * Send a message to a channel.
 * The sender_user_identifier query param is REQUIRED by the backend.
 * It is retrieved from sessionStorage.
 */
export async function sendMessage(
  channelId: string,
  input: SendMessageInput,
): Promise<Message> {
  const clientId = sessionStorage.getItem('botcrew_client_id') || '';
  return postJSON<Omit<Message, 'id'>>(
    `/channels/${channelId}/messages?sender_user_identifier=${encodeURIComponent(clientId)}`,
    input,
  );
}

/**
 * Get unread message count for a channel.
 * The user_identifier query param is REQUIRED by the backend.
 * Returns the unread count extracted from meta.unread_count in the JSON:API response.
 */
export async function getUnreadCount(channelId: string): Promise<UnreadResponse> {
  const clientId = sessionStorage.getItem('botcrew_client_id') || '';
  const res = await fetch(
    `${API_BASE}/channels/${channelId}/messages/unread?user_identifier=${encodeURIComponent(clientId)}`,
    { headers: { 'Content-Type': 'application/json' } },
  );
  if (!res.ok) {
    throw new ApiError(res.status, 'Failed to fetch unread count');
  }
  const json = await res.json() as { meta?: { unread_count?: number } };
  return { unread_count: json.meta?.unread_count ?? 0 };
}
