import type {
  IntegrationSummary,
  IntegrationDetail,
  CreateIntegrationInput,
  UpdateIntegrationInput,
} from '@/types/integration';
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON } from '@/api/client';

export async function getIntegrations(type?: string): Promise<IntegrationSummary[]> {
  const params = type ? `?type=${encodeURIComponent(type)}` : '';
  return fetchList<Omit<IntegrationSummary, 'id'>>(`/integrations${params}`);
}

export async function getIntegration(id: string): Promise<IntegrationDetail> {
  return fetchOne<Omit<IntegrationDetail, 'id'>>(`/integrations/${id}`);
}

export async function createIntegration(
  input: CreateIntegrationInput,
): Promise<IntegrationDetail> {
  return postJSON<Omit<IntegrationDetail, 'id'>>('/integrations', input, 'integrations');
}

export async function updateIntegration(
  id: string,
  input: UpdateIntegrationInput,
): Promise<IntegrationDetail> {
  return patchJSON<Omit<IntegrationDetail, 'id'>>(`/integrations/${id}`, input, 'integrations');
}

export async function deleteIntegration(id: string): Promise<void> {
  return deleteJSON(`/integrations/${id}`);
}
