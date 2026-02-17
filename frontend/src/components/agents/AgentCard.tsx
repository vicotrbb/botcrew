import { useNavigate } from 'react-router';
import { Clock } from 'lucide-react';
import type { AgentSummary } from '@/types/agent';
import { Card } from '@/components/ui/card';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { AgentAvatar } from '@/components/shared/AgentAvatar';

function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

interface AgentCardProps {
  agent: AgentSummary;
}

export function AgentCard({ agent }: AgentCardProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="p-4 cursor-pointer transition-all duration-200 hover:border-primary/50 hover:shadow-md"
      onClick={() => { void navigate(`/agents/${agent.id}`); }}
      role="link"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          void navigate(`/agents/${agent.id}`);
        }
      }}
    >
      <div className="flex items-center gap-3">
        <AgentAvatar name={agent.name} size={40} />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium truncate block">{agent.name}</span>
        </div>
        <StatusBadge status={agent.status} size="sm" />
      </div>

      <div className="mt-3 space-y-1">
        <p className="text-xs text-muted-foreground truncate">
          {agent.model_provider}/{agent.model_name}
        </p>
        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="size-3" />
          {formatInterval(agent.heartbeat_interval_seconds)}
        </p>
      </div>
    </Card>
  );
}
