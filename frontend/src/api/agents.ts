import type { AgentSummary, AgentDetail, CreateAgentInput, UpdateAgentInput, TokenUsageTotals } from '@/types/agent';
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON, putJSON } from '@/api/client';

export async function getAgents(statusFilter?: string): Promise<AgentSummary[]> {
  const params = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
  return fetchList<Omit<AgentSummary, 'id'>>(`/agents${params}`);
}

export async function getAgent(id: string): Promise<AgentDetail> {
  return fetchOne<Omit<AgentDetail, 'id'>>(`/agents/${id}`);
}

export async function createAgent(input: CreateAgentInput): Promise<AgentDetail> {
  return postJSON<Omit<AgentDetail, 'id'>>('/agents', input, 'agents');
}

export async function updateAgent(id: string, input: UpdateAgentInput): Promise<AgentDetail> {
  return patchJSON<Omit<AgentDetail, 'id'>>(`/agents/${id}`, input, 'agents');
}

export async function deleteAgent(id: string): Promise<void> {
  return deleteJSON(`/agents/${id}`);
}

export async function duplicateAgent(id: string): Promise<AgentDetail> {
  return postJSON<Omit<AgentDetail, 'id'>>(`/agents/${id}/duplicate`, {});
}

export async function getAgentMemory(id: string): Promise<Record<string, unknown>> {
  return fetchOne<Record<string, unknown>>(`/agents/${id}/memory`);
}

export async function updateAgentMemory(
  id: string,
  content: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return putJSON<Record<string, unknown>>(`/agents/${id}/memory`, content, 'agent-memory');
}

export async function patchAgentMemory(
  id: string,
  patch: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return patchJSON<Record<string, unknown>>(`/agents/${id}/memory`, patch, 'agent-memory');
}

export async function getAgentTokenUsage(id: string): Promise<TokenUsageTotals> {
  return fetchOne<TokenUsageTotals>(`/agents/${id}/token-usage`);
}
