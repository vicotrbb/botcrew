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
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON } from '@/api/client';

// Task CRUD
export async function getTasks(): Promise<TaskSummary[]> {
  return fetchList<Omit<TaskSummary, 'id'>>('/tasks');
}

export async function getTask(id: string): Promise<TaskDetail> {
  return fetchOne<Omit<TaskDetail, 'id'>>(`/tasks/${id}`);
}

export async function createTask(input: CreateTaskInput): Promise<TaskDetail> {
  return postJSON<Omit<TaskDetail, 'id'>>('/tasks', input, 'tasks');
}

export async function updateTask(id: string, input: UpdateTaskInput): Promise<TaskDetail> {
  return patchJSON<Omit<TaskDetail, 'id'>>(`/tasks/${id}`, input, 'tasks');
}

export async function deleteTask(id: string): Promise<void> {
  return deleteJSON(`/tasks/${id}`);
}

// Agent assignment
export async function getTaskAgents(taskId: string): Promise<TaskAgent[]> {
  return fetchList<Omit<TaskAgent, 'id'>>(`/tasks/${taskId}/agents`);
}

export async function assignAgent(taskId: string, input: AssignAgentInput): Promise<TaskAgent> {
  return postJSON<Omit<TaskAgent, 'id'>>(`/tasks/${taskId}/agents`, input, 'task-agents');
}

export async function removeAgent(taskId: string, agentId: string): Promise<void> {
  return deleteJSON(`/tasks/${taskId}/agents/${agentId}`);
}

// Secret assignment
export async function getTaskSecrets(taskId: string): Promise<TaskSecret[]> {
  return fetchList<Omit<TaskSecret, 'id'>>(`/tasks/${taskId}/secrets`);
}

export async function assignSecret(taskId: string, input: AssignSecretInput): Promise<TaskSecret> {
  return postJSON<Omit<TaskSecret, 'id'>>(`/tasks/${taskId}/secrets`, input, 'task-secrets');
}

export async function removeSecret(taskId: string, secretId: string): Promise<void> {
  return deleteJSON(`/tasks/${taskId}/secrets/${secretId}`);
}

// Skill assignment
export async function getTaskSkills(taskId: string): Promise<TaskSkill[]> {
  return fetchList<Omit<TaskSkill, 'id'>>(`/tasks/${taskId}/skills`);
}

export async function assignSkill(taskId: string, input: AssignSkillInput): Promise<TaskSkill> {
  return postJSON<Omit<TaskSkill, 'id'>>(`/tasks/${taskId}/skills`, input, 'task-skills');
}

export async function removeSkill(taskId: string, skillId: string): Promise<void> {
  return deleteJSON(`/tasks/${taskId}/skills/${skillId}`);
}
