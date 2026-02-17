import type { AgentStatus, ModelProvider } from '@/types/agent';

/**
 * Status-to-color mapping for agent status badges.
 */
export const STATUS_COLORS: Record<AgentStatus, string> = {
  creating: 'blue',
  running: 'green',
  idle: 'yellow',
  error: 'red',
  recovering: 'orange',
  terminating: 'gray',
};

/**
 * Available model providers for agent creation forms.
 */
export const MODEL_PROVIDERS: { value: ModelProvider; label: string }[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'glm', label: 'GLM (Z.ai)' },
];

/**
 * Default heartbeat interval in seconds (5 minutes).
 */
export const DEFAULT_HEARTBEAT_INTERVAL = 300;

/**
 * Agent list polling interval in milliseconds (30 seconds).
 */
export const AGENT_POLL_INTERVAL = 30_000;

/**
 * Unread count polling interval in milliseconds (15 seconds).
 */
export const UNREAD_POLL_INTERVAL = 15_000;

/**
 * WebSocket base URL. Falls back to deriving from window.location.
 */
export const WS_BASE_URL: string = (() => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL as string;
  }
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}`;
  }
  return 'ws://localhost:8000';
})();
