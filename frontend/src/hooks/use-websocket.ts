import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { WebSocketMessage } from '@/types/message';
import { WS_BASE_URL } from '@/lib/constants';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

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

  useEffect(() => {
    // Clear any pending retry timer from a previous channel
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }

    // Close existing connection from a previous channel
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    retryCountRef.current = 0;

    if (!channelId) {
      // No channel selected -- nothing to connect to. Status will be
      // set to 'disconnected' by the onclose callback of the connection
      // we just closed above, or it's already 'disconnected' on mount.
      return;
    }

    const chId = channelId;

    function openConnection() {
      // Close any connection still held in wsRef (e.g. from a retry cycle)
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const clientId = getClientId();
      const url = `${WS_BASE_URL}/ws/channels/${chId}?client_id=${encodeURIComponent(clientId)}`;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Guard: only update status if this WS is still the active one.
        // A channel switch may have replaced wsRef.current already.
        if (wsRef.current !== ws) return;
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
        // Guard: only update state if this WS is still the active one.
        // When the user switches channels, the cleanup function closes this
        // WS and wsRef.current is set to the new channel's WS. The old WS's
        // onclose fires asynchronously -- without this guard it would null
        // wsRef.current and attempt reconnection to the old channel.
        if (wsRef.current !== ws) return;

        wsRef.current = null;
        setStatus('disconnected');

        // Reconnect with exponential backoff
        const delay = BACKOFF_DELAYS[Math.min(retryCountRef.current, BACKOFF_DELAYS.length - 1)];
        retryCountRef.current += 1;

        retryTimerRef.current = setTimeout(() => {
          openConnection();
        }, delay);
      };

      ws.onerror = () => {
        // onclose will fire after onerror, handling reconnection
      };

      setStatus(retryCountRef.current > 0 ? 'reconnecting' : 'connecting');
    }

    openConnection();

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
    // queryClient is stable (from QueryClientProvider context)
  }, [channelId, queryClient]);

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

  // When no channel is selected, always report as disconnected regardless
  // of internal state transitions from closing the previous connection.
  const effectiveStatus = channelId ? status : 'disconnected';

  return { status: effectiveStatus, sendMessage, wsRef };
}
