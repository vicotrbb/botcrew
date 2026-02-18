import { useState, useCallback, useRef, type ChangeEvent, type KeyboardEvent } from 'react';
import type { AgentSummary } from '@/types/agent';

interface MentionQuery {
  /** Index of the '@' character in the input value */
  atIndex: number;
  /** Text after '@' up to the cursor */
  query: string;
}

function extractMentionQuery(
  value: string,
  cursorPos: number,
): MentionQuery | null {
  // Scan backward from cursor to find '@'
  for (let i = cursorPos - 1; i >= 0; i--) {
    const ch = value[i];
    // If we hit a space before finding '@', no active mention
    if (ch === ' ' || ch === '\n') return null;
    if (ch === '@') {
      // '@' must be at start of input or preceded by whitespace
      if (i === 0 || value[i - 1] === ' ' || value[i - 1] === '\n') {
        return { atIndex: i, query: value.slice(i + 1, cursorPos) };
      }
      return null;
    }
  }
  return null;
}

export function useMentionAutocomplete(
  value: string,
  agents: AgentSummary[] | undefined,
) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const mentionRef = useRef<MentionQuery | null>(null);

  const filteredAgents = (() => {
    const mq = mentionRef.current;
    if (!isOpen || !mq || !agents) return [];
    const q = mq.query.toLowerCase();
    return agents.filter((a) => a.name.toLowerCase().includes(q));
  })();

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const el = e.target;
      const cursor = el.selectionStart ?? el.value.length;
      const mq = extractMentionQuery(el.value, cursor);
      mentionRef.current = mq;

      if (mq) {
        setIsOpen(true);
        setActiveIndex(0);
      } else {
        setIsOpen(false);
      }
    },
    [],
  );

  const selectAgent = useCallback(
    (agent: AgentSummary): string => {
      const mq = mentionRef.current;
      if (!mq) return value;
      const insertName = agent.name.replace(/ /g, '_');
      const before = value.slice(0, mq.atIndex);
      const after = value.slice(mq.atIndex + 1 + mq.query.length);
      const newValue = `${before}@${insertName} ${after}`;
      setIsOpen(false);
      mentionRef.current = null;
      return newValue;
    },
    [value],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent): { consumed: boolean; newValue?: string } => {
      if (!isOpen || filteredAgents.length === 0) {
        return { consumed: false };
      }

      if (e.key === 'ArrowDown') {
        setActiveIndex((prev) =>
          prev < filteredAgents.length - 1 ? prev + 1 : 0,
        );
        return { consumed: true };
      }

      if (e.key === 'ArrowUp') {
        setActiveIndex((prev) =>
          prev > 0 ? prev - 1 : filteredAgents.length - 1,
        );
        return { consumed: true };
      }

      if (e.key === 'Enter' || e.key === 'Tab') {
        const agent = filteredAgents[activeIndex];
        if (agent) {
          const newValue = selectAgent(agent);
          return { consumed: true, newValue };
        }
      }

      if (e.key === 'Escape') {
        setIsOpen(false);
        mentionRef.current = null;
        return { consumed: true };
      }

      return { consumed: false };
    },
    [isOpen, filteredAgents, activeIndex, selectAgent],
  );

  const close = useCallback(() => {
    setIsOpen(false);
    mentionRef.current = null;
  }, []);

  return {
    isOpen,
    filteredAgents,
    activeIndex,
    setActiveIndex,
    handleChange,
    handleKeyDown,
    selectAgent,
    close,
  };
}
