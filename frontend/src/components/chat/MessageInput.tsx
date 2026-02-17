import { type FormEvent, useState } from 'react';
import { Send } from 'lucide-react';
import type { ConnectionStatus } from '@/hooks/use-websocket';
import { useSendMessage } from '@/hooks/use-messages';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

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

  const canSend = value.trim().length > 0 && !disabled;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const content = value.trim();
    if (!content) return;

    if (wsStatus === 'connected') {
      // Send via WebSocket
      wsSendMessage(content);
    } else {
      // REST fallback -- sendMessage already includes sender_user_identifier
      restSend.mutate({ content, message_type: 'chat' });
    }

    setValue('');
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-border p-3"
    >
      <StatusDot status={wsStatus} />
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
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
