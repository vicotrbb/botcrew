import { Link } from 'react-router';
import { Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { useAgents } from '@/hooks/use-agents';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AgentGrid } from '@/components/agents/AgentGrid';

function AgentCardSkeleton() {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-muted animate-pulse" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-24 bg-muted animate-pulse rounded" />
          <div className="h-3 w-32 bg-muted animate-pulse rounded" />
        </div>
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const { data, isLoading, error, refetch } = useAgents();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
          <p className="text-muted-foreground text-sm mt-1">Manage your AI workforce</p>
        </div>
        <Button asChild>
          <Link to="/agents/new">
            <Plus className="size-4" />
            Create Agent
          </Link>
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <AgentCardSkeleton key={i} />
          ))}
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="size-8 text-destructive mb-3" />
          <p className="text-sm text-muted-foreground mb-4">
            Failed to load agents. {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button variant="outline" size="sm" onClick={() => { void refetch(); }}>
            <RefreshCw className="size-4" />
            Retry
          </Button>
        </div>
      )}

      {data && <AgentGrid agents={data} />}
    </div>
  );
}
