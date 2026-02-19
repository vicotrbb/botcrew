import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  TaskSummary,
  TaskDetail,
  CreateTaskInput,
  UpdateTaskInput,
  TaskAgent,
  AssignAgentInput,
  TaskSecret,
  AssignSecretInput,
  TaskSkill,
  AssignSkillInput,
} from '@/types/task';
import {
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  getTaskAgents,
  assignAgent,
  removeAgent,
  getTaskSecrets,
  assignSecret,
  removeSecret,
  getTaskSkills,
  assignSkill,
  removeSkill,
} from '@/api/tasks';

// Task CRUD hooks
export function useTasks() {
  return useQuery<TaskSummary[]>({
    queryKey: ['tasks'],
    queryFn: () => getTasks(),
  });
}

export function useTask(id: string | null | undefined) {
  return useQuery<TaskDetail>({
    queryKey: ['tasks', id],
    queryFn: () => getTask(id!),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTaskInput) => createTask(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] });
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

export function useUpdateTask(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateTaskInput) => updateTask(taskId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId] });
      void queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks'] });
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

// Agent assignment hooks
export function useTaskAgents(taskId: string | null | undefined) {
  return useQuery<TaskAgent[]>({
    queryKey: ['tasks', taskId, 'agents'],
    queryFn: () => getTaskAgents(taskId!),
    enabled: !!taskId,
  });
}

export function useAssignTaskAgent(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AssignAgentInput) => assignAgent(taskId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId, 'agents'] });
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

export function useRemoveTaskAgent(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId: string) => removeAgent(taskId, agentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId, 'agents'] });
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

// Secret assignment hooks
export function useTaskSecrets(taskId: string | null | undefined) {
  return useQuery<TaskSecret[]>({
    queryKey: ['tasks', taskId, 'secrets'],
    queryFn: () => getTaskSecrets(taskId!),
    enabled: !!taskId,
  });
}

export function useAssignTaskSecret(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AssignSecretInput) => assignSecret(taskId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId, 'secrets'] });
    },
  });
}

export function useRemoveTaskSecret(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (secretId: string) => removeSecret(taskId, secretId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId, 'secrets'] });
    },
  });
}

// Skill assignment hooks
export function useTaskSkills(taskId: string | null | undefined) {
  return useQuery<TaskSkill[]>({
    queryKey: ['tasks', taskId, 'skills'],
    queryFn: () => getTaskSkills(taskId!),
    enabled: !!taskId,
  });
}

export function useAssignTaskSkill(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AssignSkillInput) => assignSkill(taskId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId, 'skills'] });
    },
  });
}

export function useRemoveTaskSkill(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) => removeSkill(taskId, skillId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tasks', taskId, 'skills'] });
    },
  });
}
