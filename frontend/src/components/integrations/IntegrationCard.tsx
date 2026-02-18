import { Pencil, Trash2 } from 'lucide-react';
import type { IntegrationSummary, AIProviderConfig, GitHubConfig } from '@/types/integration';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';

function parseConfig(config: string): Record<string, unknown> {
  try {
    return JSON.parse(config) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function maskValue(value: string, visibleChars = 4): string {
  if (value.length <= visibleChars) return '****';
  return value.slice(0, visibleChars) + '****';
}

function ConfigDetails({ integration }: { integration: IntegrationSummary }) {
  const config = parseConfig(integration.config);

  switch (integration.integration_type) {
    case 'ai_provider': {
      const ac = config as unknown as AIProviderConfig;
      return (
        <div className="space-y-0.5">
          <p className="text-xs text-muted-foreground">
            Provider: <span className="font-medium text-foreground">{ac.provider || 'Unknown'}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            API Key: {ac.api_key ? maskValue(ac.api_key) : '****'}
          </p>
        </div>
      );
    }
    case 'github': {
      const gc = config as unknown as GitHubConfig;
      return (
        <div className="space-y-0.5">
          <p className="text-xs text-muted-foreground">
            Token: {gc.token ? maskValue(gc.token) : '****'}
          </p>
          {gc.default_org && (
            <p className="text-xs text-muted-foreground">
              Org: <span className="font-medium text-foreground">{gc.default_org}</span>
            </p>
          )}
        </div>
      );
    }
    default:
      return null;
  }
}

interface IntegrationCardProps {
  integration: IntegrationSummary;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onToggleActive: (id: string, isActive: boolean) => void;
}

export function IntegrationCard({ integration, onEdit, onDelete, onToggleActive }: IntegrationCardProps) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">{integration.name}</span>
            <Badge variant={integration.is_active ? 'default' : 'secondary'} className="text-[10px]">
              {integration.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
          <div className="mt-1">
            <ConfigDetails integration={integration} />
          </div>
          <p className="text-[10px] text-muted-foreground mt-1">
            Created {new Date(integration.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <Switch
            checked={integration.is_active}
            onCheckedChange={(checked) => onToggleActive(integration.id, checked)}
            size="sm"
          />
          <Button variant="ghost" size="icon" className="size-8" onClick={() => onEdit(integration.id)}>
            <Pencil className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-destructive hover:text-destructive"
            onClick={() => onDelete(integration.id)}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
