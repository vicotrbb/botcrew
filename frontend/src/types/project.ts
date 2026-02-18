export interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  goals: string | null;
  specs: string | null;
  github_repo_url: string | null;
  channel_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends ProjectSummary {}

export interface ProjectAgent {
  id: string;
  project_id: string;
  agent_id: string;
  role_prompt: string | null;
  created_at: string;
}

export interface CreateProjectInput {
  name: string;
  description?: string;
  goals?: string;
  github_repo_url?: string;
}

export interface UpdateProjectInput {
  name?: string;
  description?: string;
  goals?: string;
  specs?: string;
  github_repo_url?: string;
}

export interface AssignAgentInput {
  agent_id: string;
  role_prompt?: string;
}
