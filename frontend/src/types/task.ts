export interface TaskSummary {
  id: string;
  name: string;
  description: string | null;
  directive: string;
  notes: string;
  status: string;  // "open" | "done"
  channel_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends TaskSummary {}

export interface TaskAgent {
  id: string;
  task_id: string;
  agent_id: string;
  created_at: string;
}

export interface TaskSecret {
  id: string;
  task_id: string;
  secret_id: string;
  created_at: string;
}

export interface TaskSkill {
  id: string;
  task_id: string;
  skill_id: string;
  created_at: string;
}

export interface CreateTaskInput {
  name: string;
  description?: string;
  directive: string;
}

export interface UpdateTaskInput {
  name?: string;
  description?: string;
  directive?: string;
  status?: string;
}

export interface AssignAgentInput {
  agent_id: string;
}

export interface AssignSecretInput {
  secret_id: string;
}

export interface AssignSkillInput {
  skill_id: string;
}
