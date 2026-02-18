import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  IntegrationSummary,
  IntegrationDetail,
  CreateIntegrationInput,
  UpdateIntegrationInput,
} from '@/types/integration';
import {
  getIntegrations,
  getIntegration,
  createIntegration,
  updateIntegration,
  deleteIntegration,
} from '@/api/integrations';

export function useIntegrations(type?: string) {
  return useQuery<IntegrationSummary[]>({
    queryKey: ['integrations', { type }],
    queryFn: () => getIntegrations(type),
  });
}

export function useIntegration(id: string | null | undefined) {
  return useQuery<IntegrationDetail>({
    queryKey: ['integrations', id],
    queryFn: () => getIntegration(id!),
    enabled: !!id,
  });
}

export function useCreateIntegration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateIntegrationInput) => createIntegration(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['integrations'] });
    },
  });
}

export function useUpdateIntegration(integrationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateIntegrationInput) => updateIntegration(integrationId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['integrations', integrationId] });
      void queryClient.invalidateQueries({ queryKey: ['integrations'] });
    },
  });
}

export function useDeleteIntegration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteIntegration(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['integrations'] });
    },
  });
}
