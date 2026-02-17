import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { WebSocketMessage } from '@/types/message';
import { WS_BASE_URL } from '@/lib/constants';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000];

/**
 * Get or create a per-tab client ID stored in sessionStorage.
 * Using sessionStorage (not localStorage) avoids tab collision.
 */
function getClientId(): string {
  const key = 'botcrew_client_id';
  let clientId = sessionStorage.getItem(key);
  if (!clientId) {
    clientId = crypto.randomUUID();
    sessionStorage.setItem(key, clientId);
  }
  return clientId;
}

export function useWebSocket(channelId: string | null) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  const connect = useCallback(
    (chId: string) => {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const clientId = getClientId();
      const url = `${WS_BASE_URL}/ws/channels/${chId}?client_id=${encodeURIComponent(clientId)}`;

      setStatus(retryCountRef.current > 0 ? 'reconnecting' : 'connecting');

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retryCountRef.current = 0;
        setStatus('connected');
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data as string) as WebSocketMessage;
          if (msg.type === 'message') {
            void queryClient.invalidateQueries({ queryKey: ['messages', chId] });
          }
        } catch {
          // Ignore unparseable messages
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        setStatus('disconnected');

        // Reconnect with exponential backoff
        const delay = BACKOFF_DELAYS[Math.min(retryCountRef.current, BACKOFF_DELAYS.length - 1)];
        retryCountRef.current += 1;

        retryTimerRef.current = setTimeout(() => {
          // Only reconnect if the channel hasn't changed
          if (channelId === chId) {
            connect(chId);
          }
        }, delay);
      };

      ws.onerror = () => {
        // onclose will fire after onerror, handling reconnection
      };
    },
    [channelId, queryClient],
  );

  useEffect(() => {
    // Clear any pending retry timer
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    retryCountRef.current = 0;

    if (channelId) {
      connect(channelId);
    } else {
      setStatus('disconnected');
    }

    return () => {
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [channelId, connect]);

  const sendMessage = useCallback(
    (content: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'message',
            content,
            message_type: 'chat',
          }),
        );
      }
    },
    [],
  );

  return { status, sendMessage, wsRef };
}
