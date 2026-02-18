import { z } from 'zod';

/**
 * Zod schema for agent creation form validation.
 */
export const createAgentSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be 100 characters or fewer'),
  model_provider: z.enum(['openai', 'anthropic', 'ollama', 'glm']),
  model_name: z.string().min(1, 'Model name is required').max(100, 'Model name must be 100 characters or fewer'),
  identity: z.string().optional(),
  personality: z.string().optional(),
  heartbeat_interval_seconds: z
    .number()
    .min(10, 'Minimum interval is 10 seconds')
    .max(86400, 'Maximum interval is 86400 seconds (24 hours)')
    .optional(),
});

/**
 * Zod schema for agent update form validation. All fields optional.
 */
export const updateAgentSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  model_provider: z.enum(['openai', 'anthropic', 'ollama', 'glm']).optional(),
  model_name: z.string().min(1).max(100).optional(),
  identity: z.string().optional(),
  personality: z.string().optional(),
  heartbeat_prompt: z.string().optional(),
  heartbeat_enabled: z.boolean().optional(),
  heartbeat_interval_seconds: z.number().min(10).max(86400).optional(),
});

/**
 * Zod schema for channel creation form validation.
 */
export const createChannelSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be 100 characters or fewer'),
  description: z.string().optional(),
  channel_type: z.enum(['shared', 'direct']).default('shared'),
  agent_ids: z.array(z.string()).default([]),
});

/**
 * Zod schema for sending a message.
 */
export const sendMessageSchema = z.object({
  content: z.string().min(1, 'Message cannot be empty'),
  message_type: z.enum(['chat', 'system', 'command']).default('chat'),
});

/**
 * Zod schema for secret creation form validation.
 */
export const createSecretSchema = z.object({
  key: z.string().min(1, 'Key is required').max(255, 'Key must be 255 characters or fewer')
    .regex(/^[A-Za-z_][A-Za-z0-9_]*$/, 'Key must be a valid identifier (letters, digits, underscores)'),
  value: z.string().min(1, 'Value is required'),
  description: z.string().optional(),
});

/**
 * Zod schema for secret update form validation. All fields optional.
 */
export const updateSecretSchema = z.object({
  key: z.string().min(1).max(255)
    .regex(/^[A-Za-z_][A-Za-z0-9_]*$/, 'Key must be a valid identifier')
    .optional(),
  value: z.string().min(1).optional(),
  description: z.string().optional(),
});

/**
 * Zod schema for skill creation form validation.
 */
export const createSkillSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be 100 characters or fewer'),
  description: z.string().min(1, 'Description is required').max(250, 'Description must be 250 characters or fewer'),
  body: z.string().min(1, 'Skill content is required'),
});

/**
 * Zod schema for skill update form validation. All fields optional.
 */
export const updateSkillSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().min(1).max(250).optional(),
  body: z.string().min(1).optional(),
});

/**
 * Zod schema for Discord integration creation form validation.
 */
export const discordIntegrationSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  webhook_url: z.string().url('Must be a valid URL'),
  agent_id: z.string().optional(),
  channel_id: z.string().optional(),
});

/**
 * Zod schema for AI provider integration creation form validation.
 */
export const aiProviderIntegrationSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  provider: z.enum(['openai', 'anthropic', 'ollama', 'glm']),
  api_key: z.string().min(1, 'API key is required'),
});

/**
 * Zod schema for GitHub integration creation form validation.
 */
export const githubIntegrationSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  token: z.string().min(1, 'Token is required'),
  default_org: z.string().optional(),
});

/**
 * Inferred types from Zod schemas for form usage.
 */
export type CreateAgentInput = z.infer<typeof createAgentSchema>;
export type UpdateAgentInput = z.infer<typeof updateAgentSchema>;
export type CreateChannelInput = z.infer<typeof createChannelSchema>;
export type CreateSecretInput = z.infer<typeof createSecretSchema>;
export type UpdateSecretInput = z.infer<typeof updateSecretSchema>;
export type CreateSkillInput = z.infer<typeof createSkillSchema>;
export type UpdateSkillInput = z.infer<typeof updateSkillSchema>;
export type DiscordIntegrationInput = z.infer<typeof discordIntegrationSchema>;
export type AIProviderIntegrationInput = z.infer<typeof aiProviderIntegrationSchema>;
export type GitHubIntegrationInput = z.infer<typeof githubIntegrationSchema>;
