import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Channel, CreateChannelInput, ChannelMember } from '@/types/channel';
import {
  getChannels,
  getChannel,
  createChannel,
  deleteChannel,
  getDmChannel,
  addChannelMember,
  removeChannelMember,
  getChannelMembers,
} from '@/api/channels';

export function useChannels() {
  return useQuery<Channel[]>({
    queryKey: ['channels'],
    queryFn: getChannels,
  });
}

export function useChannel(channelId: string | null | undefined) {
  return useQuery<Channel>({
    queryKey: ['channels', channelId],
    queryFn: () => getChannel(channelId!),
    enabled: !!channelId,
  });
}

export function useCreateChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateChannelInput) => createChannel(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

export function useDeleteChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteChannel(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

export function useChannelMembers(channelId: string | null | undefined) {
  return useQuery<(ChannelMember & { id: string })[]>({
    queryKey: ['channels', channelId, 'members'],
    queryFn: () => getChannelMembers(channelId!),
    enabled: !!channelId,
  });
}

export function useAddChannelMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      channelId,
      body,
    }: {
      channelId: string;
      body: { agent_id?: string; user_identifier?: string };
    }) => addChannelMember(channelId, body),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ['channels', variables.channelId],
      });
    },
  });
}

export function useRemoveChannelMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      channelId,
      agentId,
    }: {
      channelId: string;
      agentId: string;
    }) => removeChannelMember(channelId, agentId),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ['channels', variables.channelId],
      });
    },
  });
}

export function useGetDmChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => getDmChannel(agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}
