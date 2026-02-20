export type ChannelType = 'shared' | 'custom' | 'dm';

export interface Channel {
  id: string;
  name: string;
  description: string | null;
  channel_type: ChannelType;
  creator_user_identifier: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateChannelInput {
  name: string;
  description?: string;
  channel_type?: ChannelType;
  agent_ids: string[];
  creator_user_identifier?: string;
}

export interface ChannelMember {
  channel_id: string;
  agent_id: string | null;
  user_identifier: string | null;
  created_at: string;
}
