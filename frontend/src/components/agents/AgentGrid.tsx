import { Link } from 'react-router';
import { Plus } from 'lucide-react';
import type { AgentSummary } from '@/types/agent';
import { AgentCard } from './AgentCard';

interface AgentGridProps {
  agents: AgentSummary[];
}

export function AgentGrid({ agents }: AgentGridProps) {
  if (agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-muted-foreground text-sm">No agents yet</p>
        <Link
          to="/agents/new"
          className="mt-3 inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <Plus className="size-4" />
          Create your first agent
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
