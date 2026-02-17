export type MessageType = 'chat' | 'system' | 'command';

export interface Message {
  id: string;
  content: string;
  message_type: MessageType;
  sender_agent_id: string | null;
  sender_user_identifier: string | null;
  channel_id: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface SendMessageInput {
  content: string;
  message_type?: MessageType;
}

export interface WebSocketMessage {
  type: string;
  id?: string;
  channel_id: string;
  sender_type?: string;
  sender_id?: string;
  content?: string;
  message_type?: string;
  created_at?: string;
}

export interface UnreadResponse {
  unread_count: number;
}
