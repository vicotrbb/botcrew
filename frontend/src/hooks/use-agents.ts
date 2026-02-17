import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AgentSummary, AgentDetail, CreateAgentInput, UpdateAgentInput } from '@/types/agent';
import {
  getAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
  duplicateAgent,
  getAgentMemory,
  updateAgentMemory,
} from '@/api/agents';
import { AGENT_POLL_INTERVAL } from '@/lib/constants';

export function useAgents(statusFilter?: string) {
  return useQuery<AgentSummary[]>({
    queryKey: ['agents', { status: statusFilter }],
    queryFn: () => getAgents(statusFilter),
    refetchInterval: AGENT_POLL_INTERVAL,
  });
}

export function useAgent(agentId: string | null | undefined) {
  return useQuery<AgentDetail>({
    queryKey: ['agents', agentId],
    queryFn: () => getAgent(agentId!),
    enabled: !!agentId,
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAgentInput) => createAgent(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useUpdateAgent(agentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateAgentInput) => updateAgent(agentId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['agents', agentId] });
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useDeleteAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAgent(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useDuplicateAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => duplicateAgent(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useAgentMemory(agentId: string | null | undefined) {
  return useQuery<Record<string, unknown>>({
    queryKey: ['agents', agentId, 'memory'],
    queryFn: () => getAgentMemory(agentId!),
    enabled: !!agentId,
  });
}

export function useUpdateAgentMemory(agentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: Record<string, unknown>) => updateAgentMemory(agentId, content),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['agents', agentId, 'memory'] });
    },
  });
}
