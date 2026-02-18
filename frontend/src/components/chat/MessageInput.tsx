import { type FormEvent, useState } from 'react';
import { Send } from 'lucide-react';
import type { ConnectionStatus } from '@/hooks/use-websocket';
import { useSendMessage, useOptimisticMessage } from '@/hooks/use-messages';
import { useAgents } from '@/hooks/use-agents';
import { useMentionAutocomplete } from '@/hooks/use-mention-autocomplete';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { MentionDropdown } from './MentionDropdown';

interface MessageInputProps {
  channelId: string;
  wsStatus: ConnectionStatus;
  wsSendMessage: (content: string) => void;
  disabled?: boolean;
}

function StatusDot({ status }: { status: ConnectionStatus }) {
  const colorMap: Record<ConnectionStatus, string> = {
    connected: 'bg-green-500',
    connecting: 'bg-yellow-500',
    reconnecting: 'bg-yellow-500',
    disconnected: 'bg-red-500',
  };

  const labelMap: Record<ConnectionStatus, string> = {
    connected: 'Connected',
    connecting: 'Connecting',
    reconnecting: 'Reconnecting',
    disconnected: 'Disconnected',
  };

  return (
    <span
      className={`inline-block size-2 rounded-full ${colorMap[status]}`}
      title={labelMap[status]}
    />
  );
}

export function MessageInput({
  channelId,
  wsStatus,
  wsSendMessage,
  disabled = false,
}: MessageInputProps) {
  const [value, setValue] = useState('');
  const restSend = useSendMessage(channelId);
  const addOptimistic = useOptimisticMessage(channelId);
  const { data: agents } = useAgents();
  const mention = useMentionAutocomplete(value, agents);

  const canSend = value.trim().length > 0 && !disabled;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const content = value.trim();
    if (!content) return;

    if (wsStatus === 'connected') {
      // Add optimistic message so it appears instantly in the UI.
      // The WS echo will trigger invalidateQueries which refetches
      // and replaces the optimistic entry with the real server data.
      addOptimistic(content);
      wsSendMessage(content);
    } else {
      // REST fallback -- useSendMessage handles its own optimistic update
      restSend.mutate({ content, message_type: 'chat' });
    }

    setValue('');
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="relative flex items-center gap-2 border-t border-border p-3"
    >
      {mention.isOpen && (
        <MentionDropdown
          agents={mention.filteredAgents}
          activeIndex={mention.activeIndex}
          onSelect={(agent) => setValue(mention.selectAgent(agent))}
          onHover={mention.setActiveIndex}
        />
      )}
      <StatusDot status={wsStatus} />
      <Input
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          mention.handleChange(e);
        }}
        onKeyDown={(e) => {
          const result = mention.handleKeyDown(e);
          if (result.consumed) {
            e.preventDefault();
            if (result.newValue !== undefined) {
              setValue(result.newValue);
            }
          }
        }}
        onBlur={() => setTimeout(mention.close, 150)}
        placeholder="Type a message..."
        disabled={disabled}
        className="flex-1"
      />
      <Button
        type="submit"
        size="icon-sm"
        disabled={!canSend}
        aria-label="Send message"
      >
        <Send className="size-4" />
      </Button>
    </form>
  );
}
