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
    .default(300),
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
 * Inferred types from Zod schemas for form usage.
 */
export type CreateAgentInput = z.infer<typeof createAgentSchema>;
export type UpdateAgentInput = z.infer<typeof updateAgentSchema>;
export type CreateChannelInput = z.infer<typeof createChannelSchema>;
