export type AgentStatus =
  | 'creating'
  | 'running'
  | 'idle'
  | 'error'
  | 'recovering'
  | 'terminating';

export type ModelProvider = 'openai' | 'anthropic' | 'ollama' | 'glm';

export interface AgentSummary {
  id: string;
  name: string;
  status: AgentStatus;
  model_provider: ModelProvider;
  model_name: string;
  heartbeat_interval_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface AgentDetail extends AgentSummary {
  identity: string | null;
  personality: string | null;
  heartbeat_prompt: string | null;
  heartbeat_enabled: boolean;
  avatar_url: string | null;
  pod_name: string | null;
  memory: Record<string, unknown> | null;
}

export interface CreateAgentInput {
  name: string;
  model_provider: ModelProvider;
  model_name: string;
  identity?: string;
  personality?: string;
  heartbeat_interval_seconds?: number;
}

export interface UpdateAgentInput {
  name?: string;
  identity?: string;
  personality?: string;
  heartbeat_prompt?: string;
  heartbeat_interval_seconds?: number;
  heartbeat_enabled?: boolean;
  model_provider?: ModelProvider;
  model_name?: string;
}

export interface TokenUsageTotals {
  total_input_tokens: number;
  total_output_tokens: number;
}
