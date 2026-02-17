import type { Channel, CreateChannelInput } from '@/types/channel';
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON, deleteJSONWithBody } from '@/api/client';

export async function getChannels(): Promise<Channel[]> {
  return fetchList<Omit<Channel, 'id'>>('/channels');
}

export async function getChannel(id: string): Promise<Channel> {
  return fetchOne<Omit<Channel, 'id'>>(`/channels/${id}`);
}

export async function createChannel(input: CreateChannelInput): Promise<Channel> {
  return postJSON<Omit<Channel, 'id'>>('/channels', input);
}

export async function updateChannel(
  id: string,
  input: Partial<Pick<Channel, 'name' | 'description'>>,
): Promise<Channel> {
  return patchJSON<Omit<Channel, 'id'>>(`/channels/${id}`, input);
}

export async function deleteChannel(id: string): Promise<void> {
  return deleteJSON(`/channels/${id}`);
}

export async function addChannelMember(
  channelId: string,
  body: { agent_id?: string; user_identifier?: string },
): Promise<void> {
  await postJSON<Record<string, unknown>>(`/channels/${channelId}/members`, body);
}

/**
 * Remove a member from a channel.
 * Backend expects DELETE /channels/{id}/members with JSON body { agent_id }.
 * There is NO path parameter for the member.
 */
export async function removeChannelMember(
  channelId: string,
  agentId: string,
): Promise<void> {
  return deleteJSONWithBody(`/channels/${channelId}/members`, { agent_id: agentId });
}
