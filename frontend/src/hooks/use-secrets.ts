import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { SecretSummary, CreateSecretInput, UpdateSecretInput } from '@/types/secret';
import {
  getSecrets,
  getSecret,
  createSecret,
  updateSecret,
  deleteSecret,
} from '@/api/secrets';

export function useSecrets() {
  return useQuery<SecretSummary[]>({
    queryKey: ['secrets'],
    queryFn: getSecrets,
  });
}

/**
 * Reveal a secret's real value by fetching it directly.
 * Used imperatively in SecretRow -- not a hook-based query.
 */
export async function revealSecret(id: string): Promise<string> {
  const detail = await getSecret(id);
  return detail.value;
}

export function useCreateSecret() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSecretInput) => createSecret(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['secrets'] });
    },
  });
}

export function useUpdateSecret(secretId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateSecretInput) => updateSecret(secretId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['secrets', secretId] });
      void queryClient.invalidateQueries({ queryKey: ['secrets'] });
    },
  });
}

export function useDeleteSecret() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSecret(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['secrets'] });
    },
  });
}
