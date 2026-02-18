import Avatar from 'boring-avatars';
import type { AgentSummary } from '@/types/agent';

interface MentionDropdownProps {
  agents: AgentSummary[];
  activeIndex: number;
  onSelect: (agent: AgentSummary) => void;
  onHover: (index: number) => void;
}

export function MentionDropdown({
  agents,
  activeIndex,
  onSelect,
  onHover,
}: MentionDropdownProps) {
  if (agents.length === 0) {
    return (
      <div className="absolute bottom-full left-0 right-0 mb-1 rounded-md border border-border bg-popover p-2 shadow-md">
        <p className="text-sm text-muted-foreground">No agents found</p>
      </div>
    );
  }

  return (
    <ul
      role="listbox"
      className="absolute bottom-full left-0 right-0 mb-1 max-h-48 overflow-y-auto rounded-md border border-border bg-popover py-1 shadow-md"
    >
      {agents.map((agent, i) => (
        <li
          key={agent.id}
          role="option"
          aria-selected={i === activeIndex}
          className={`flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm ${
            i === activeIndex ? 'bg-accent text-accent-foreground' : ''
          }`}
          onMouseDown={(e) => {
            e.preventDefault();
            onSelect(agent);
          }}
          onMouseEnter={() => onHover(i)}
        >
          <Avatar
            name={agent.name}
            size={20}
            variant="beam"
            colors={['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#e0e7ff']}
          />
          <span className="truncate">{agent.name}</span>
        </li>
      ))}
    </ul>
  );
}
