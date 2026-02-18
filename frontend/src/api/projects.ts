import type {
  ProjectSummary,
  ProjectDetail,
  CreateProjectInput,
  UpdateProjectInput,
  ProjectAgent,
  AssignAgentInput,
} from '@/types/project';
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON } from '@/api/client';

export async function getProjects(): Promise<ProjectSummary[]> {
  return fetchList<Omit<ProjectSummary, 'id'>>('/projects');
}

export async function getProject(id: string): Promise<ProjectDetail> {
  return fetchOne<Omit<ProjectDetail, 'id'>>(`/projects/${id}`);
}

export async function createProject(input: CreateProjectInput): Promise<ProjectDetail> {
  return postJSON<Omit<ProjectDetail, 'id'>>('/projects', input, 'projects');
}

export async function updateProject(id: string, input: UpdateProjectInput): Promise<ProjectDetail> {
  return patchJSON<Omit<ProjectDetail, 'id'>>(`/projects/${id}`, input, 'projects');
}

export async function deleteProject(id: string): Promise<void> {
  return deleteJSON(`/projects/${id}`);
}

export async function getProjectAgents(projectId: string): Promise<ProjectAgent[]> {
  return fetchList<Omit<ProjectAgent, 'id'>>(`/projects/${projectId}/agents`);
}

export async function assignAgent(projectId: string, input: AssignAgentInput): Promise<ProjectAgent> {
  return postJSON<Omit<ProjectAgent, 'id'>>(`/projects/${projectId}/agents`, input, 'project-agents');
}

export async function removeAgent(projectId: string, agentId: string): Promise<void> {
  return deleteJSON(`/projects/${projectId}/agents/${agentId}`);
}

export async function syncProject(projectId: string): Promise<ProjectDetail> {
  return postJSON<Omit<ProjectDetail, 'id'>>(`/projects/${projectId}/sync`, {});
}
