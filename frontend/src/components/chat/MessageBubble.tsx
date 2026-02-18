import Avatar from 'boring-avatars';
import type { Message } from '@/types/message';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

interface MessageBubbleProps {
  message: Message;
  agentNames: Map<string, string>;
}

function formatTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function MessageBubble({ message, agentNames }: MessageBubbleProps) {
  const isSystem = message.message_type === 'system';
  const isAgent = !!message.sender_agent_id;
  const isUser = !!message.sender_user_identifier && !isAgent;
  const agentName = message.sender_agent_id
    ? agentNames.get(message.sender_agent_id) ?? 'Agent'
    : 'Agent';

  // System messages: centered, no bubble
  if (isSystem) {
    return (
      <div className="flex justify-center py-1">
        <span className="text-xs text-muted-foreground">{message.content}</span>
      </div>
    );
  }

  // Agent messages: left-aligned with avatar
  if (isAgent) {
    return (
      <div className="flex flex-row items-start gap-2 max-w-[75%]">
        <div className="flex-shrink-0 mt-1">
          <Avatar
            name={agentName}
            size={28}
            variant="beam"
            colors={['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#e0e7ff']}
          />
        </div>
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-xs font-medium text-muted-foreground truncate">
            {agentName}
          </span>
          <div className="bg-muted text-foreground rounded-lg rounded-tl-sm px-3 py-2">
            <MarkdownRenderer content={message.content} />
          </div>
          <span className="text-[10px] text-muted-foreground">
            {formatTime(message.created_at)}
          </span>
        </div>
      </div>
    );
  }

  // User messages: right-aligned, no avatar
  if (isUser) {
    return (
      <div className="flex flex-row-reverse items-start max-w-[75%] ml-auto">
        <div className="flex flex-col items-end gap-0.5 min-w-0">
          <div className="bg-primary text-primary-foreground rounded-lg rounded-tr-sm px-3 py-2">
            <MarkdownRenderer
              content={message.content}
              className="prose-invert"
            />
          </div>
          <span className="text-[10px] text-muted-foreground">
            {formatTime(message.created_at)}
          </span>
        </div>
      </div>
    );
  }

  // Fallback: treat as agent message without avatar
  return (
    <div className="flex flex-row items-start gap-2 max-w-[75%]">
      <div className="flex flex-col gap-0.5 min-w-0">
        <div className="bg-muted text-foreground rounded-lg px-3 py-2">
          <MarkdownRenderer content={message.content} />
        </div>
        <span className="text-[10px] text-muted-foreground">
          {formatTime(message.created_at)}
        </span>
      </div>
    </div>
  );
}
