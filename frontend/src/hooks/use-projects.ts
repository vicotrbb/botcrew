import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  ProjectSummary,
  ProjectDetail,
  CreateProjectInput,
  UpdateProjectInput,
  ProjectAgent,
  AssignAgentInput,
} from '@/types/project';
import {
  getProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  getProjectAgents,
  assignAgent,
  removeAgent,
  syncProject,
} from '@/api/projects';

export function useProjects() {
  return useQuery<ProjectSummary[]>({
    queryKey: ['projects'],
    queryFn: () => getProjects(),
  });
}

export function useProject(id: string | null | undefined) {
  return useQuery<ProjectDetail>({
    queryKey: ['projects', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateProjectInput) => createProject(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateProjectInput) => updateProject(projectId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects', projectId] });
      void queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useProjectAgents(projectId: string | null | undefined) {
  return useQuery<ProjectAgent[]>({
    queryKey: ['projects', projectId, 'agents'],
    queryFn: () => getProjectAgents(projectId!),
    enabled: !!projectId,
  });
}

export function useAssignAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AssignAgentInput) => assignAgent(projectId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'agents'] });
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useRemoveAgent(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => removeAgent(projectId, agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'agents'] });
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });
}

export function useSyncProject() {
  return useMutation({
    mutationFn: (projectId: string) => syncProject(projectId),
  });
}
