export type IntegrationType = 'discord' | 'ai_provider' | 'github';

export interface IntegrationSummary {
  id: string;
  name: string;
  integration_type: IntegrationType;
  config: string;
  agent_id: string | null;
  channel_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type IntegrationDetail = IntegrationSummary;

/** Parsed config types for each integration type */
export interface DiscordConfig {
  webhook_url: string;
}

export interface AIProviderConfig {
  provider: string;
  api_key: string;
}

export interface GitHubConfig {
  token: string;
  default_org?: string;
}

export interface CreateIntegrationInput {
  name: string;
  integration_type: IntegrationType;
  config: string;
  agent_id?: string;
  channel_id?: string;
}

export interface UpdateIntegrationInput {
  name?: string;
  integration_type?: string;
  config?: string;
  agent_id?: string | null;
  channel_id?: string | null;
  is_active?: boolean;
}
