import type { SecretSummary, SecretDetail, CreateSecretInput, UpdateSecretInput } from '@/types/secret';
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON } from '@/api/client';

export async function getSecrets(): Promise<SecretSummary[]> {
  return fetchList<Omit<SecretSummary, 'id'>>('/secrets');
}

export async function getSecret(id: string): Promise<SecretDetail> {
  return fetchOne<Omit<SecretDetail, 'id'>>(`/secrets/${id}`);
}

export async function createSecret(input: CreateSecretInput): Promise<SecretDetail> {
  return postJSON<Omit<SecretDetail, 'id'>>('/secrets', input, 'secrets');
}

export async function updateSecret(id: string, input: UpdateSecretInput): Promise<SecretDetail> {
  return patchJSON<Omit<SecretDetail, 'id'>>(`/secrets/${id}`, input, 'secrets');
}

export async function deleteSecret(id: string): Promise<void> {
  return deleteJSON(`/secrets/${id}`);
}
