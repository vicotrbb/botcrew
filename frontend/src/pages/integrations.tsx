import { useState, useCallback } from 'react';
import { AlertCircle, RefreshCw, ChevronDown, MessageSquare, Cpu, GitBranch } from 'lucide-react';
import type { IntegrationType, IntegrationSummary } from '@/types/integration';
import { useIntegrations, useDeleteIntegration } from '@/hooks/use-integrations';
import { updateIntegration } from '@/api/integrations';
import { DiscordSection } from '@/components/integrations/DiscordSection';
import { AIProvidersSection } from '@/components/integrations/AIProvidersSection';
import { GitHubSection } from '@/components/integrations/GitHubSection';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useQueryClient } from '@tanstack/react-query';

function SkeletonSection() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {Array.from({ length: 2 }).map((_, i) => (
        <Card key={i} className="p-4">
          <div className="space-y-2">
            <div className="h-4 w-32 bg-muted animate-pulse rounded" />
            <div className="h-3 w-48 bg-muted animate-pulse rounded" />
            <div className="h-3 w-24 bg-muted animate-pulse rounded" />
          </div>
        </Card>
      ))}
    </div>
  );
}

interface SectionConfig {
  type: IntegrationType;
  label: string;
  icon: React.ElementType;
}

const SECTIONS: SectionConfig[] = [
  { type: 'discord', label: 'Discord', icon: MessageSquare },
  { type: 'ai_provider', label: 'AI Providers', icon: Cpu },
  { type: 'github', label: 'GitHub', icon: GitBranch },
];

function renderSection(
  type: IntegrationType,
  integrations: IntegrationSummary[],
  onDelete: (id: string, name: string) => void,
  onToggleActive: (id: string, isActive: boolean) => void,
) {
  const props = { integrations, onDelete, onToggleActive };
  switch (type) {
    case 'discord':
      return <DiscordSection {...props} />;
    case 'ai_provider':
      return <AIProvidersSection {...props} />;
    case 'github':
      return <GitHubSection {...props} />;
    default:
      return null;
  }
}

export function IntegrationsPage() {
  const { data, isLoading, error, refetch } = useIntegrations();
  const deleteMutation = useDeleteIntegration();
  const queryClient = useQueryClient();

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  function handleDeleteRequest(id: string, name: string) {
    setDeleteTarget({ id, name });
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch {
      // Error shown by mutation
    }
  }

  const handleToggleActive = useCallback(
    (id: string, isActive: boolean) => {
      void updateIntegration(id, { is_active: isActive }).then(() => {
        void queryClient.invalidateQueries({ queryKey: ['integrations'] });
      });
    },
    [queryClient],
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground text-sm mt-1">Configure external service connections</p>
        </div>
      </div>

      {error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <AlertCircle className="size-8 text-destructive mb-3" />
          <p className="text-sm text-muted-foreground mb-4">
            Failed to load integrations. {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button variant="outline" size="sm" onClick={() => { void refetch(); }}>
            <RefreshCw className="size-4" />
            Retry
          </Button>
        </div>
      )}

      {isLoading && (
        <div className="space-y-4">
          {SECTIONS.map((section) => (
            <div key={section.type} className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 bg-muted animate-pulse rounded" />
                <div className="h-4 w-24 bg-muted animate-pulse rounded" />
              </div>
              <SkeletonSection />
            </div>
          ))}
        </div>
      )}

      {data && (
        <div className="space-y-4">
          {SECTIONS.map((section) => {
            const filtered = data.filter((i) => i.integration_type === section.type);
            const Icon = section.icon;
            return (
              <Collapsible key={section.type} defaultOpen>
                <div className="rounded-lg border">
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="w-full justify-between p-4 h-auto rounded-b-none">
                      <div className="flex items-center gap-2">
                        <Icon className="size-4" />
                        <span className="font-medium">{section.label}</span>
                        <Badge variant="secondary">{filtered.length}</Badge>
                      </div>
                      <ChevronDown className="size-4 transition-transform duration-200 [[data-state=closed]_&]:rotate-[-90deg]" />
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="px-4 pb-4">
                    {renderSection(section.type, filtered, handleDeleteRequest, handleToggleActive)}
                  </CollapsibleContent>
                </div>
              </Collapsible>
            );
          })}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete Integration</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteTarget?.name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={() => void handleDeleteConfirm()} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
