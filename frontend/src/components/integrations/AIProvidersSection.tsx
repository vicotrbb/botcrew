import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import type { IntegrationSummary } from '@/types/integration';
import { useCreateIntegration, useUpdateIntegration } from '@/hooks/use-integrations';
import { aiProviderIntegrationSchema, type AIProviderIntegrationInput } from '@/lib/schemas';
import { IntegrationCard } from '@/components/integrations/IntegrationCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'glm', label: 'GLM' },
] as const;

interface AIProvidersSectionProps {
  integrations: IntegrationSummary[];
  onDelete: (id: string, name: string) => void;
  onToggleActive: (id: string, isActive: boolean) => void;
}

export function AIProvidersSection({ integrations, onDelete, onToggleActive }: AIProvidersSectionProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const createIntegration = useCreateIntegration();

  function handleEdit(id: string) {
    setEditingId(id);
    setDialogOpen(true);
  }

  function handleCreate() {
    setEditingId(null);
    setDialogOpen(true);
  }

  function handleDialogClose() {
    setDialogOpen(false);
    setEditingId(null);
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {integrations.map((integration) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            onEdit={handleEdit}
            onDelete={(id) => onDelete(id, integration.name)}
            onToggleActive={onToggleActive}
          />
        ))}
      </div>

      <Button variant="outline" size="sm" onClick={handleCreate}>
        <Plus className="size-4" />
        Add AI Provider
      </Button>

      <AIProviderDialog
        open={dialogOpen}
        onOpenChange={(open) => { if (!open) handleDialogClose(); else setDialogOpen(true); }}
        editingId={editingId}
        editingIntegration={editingId ? integrations.find((i) => i.id === editingId) : undefined}
        createMutation={createIntegration}
      />
    </div>
  );
}

interface AIProviderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingId: string | null;
  editingIntegration?: IntegrationSummary;
  createMutation: ReturnType<typeof useCreateIntegration>;
}

function AIProviderDialog({
  open,
  onOpenChange,
  editingId,
  editingIntegration,
  createMutation,
}: AIProviderDialogProps) {
  const isEditing = editingId !== null;
  const updateMutation = useUpdateIntegration(editingId ?? '');

  const defaultValues = getDefaults(editingIntegration);
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AIProviderIntegrationInput>({
    resolver: zodResolver(aiProviderIntegrationSchema),
    defaultValues,
  });

  const provider = watch('provider');

  useEffect(() => {
    if (open && editingIntegration) {
      reset(getDefaults(editingIntegration));
    } else if (open && !editingIntegration) {
      reset(getDefaults(undefined));
    }
  }, [open, editingIntegration, reset]);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      reset(getDefaults(undefined));
    } else if (editingIntegration) {
      reset(getDefaults(editingIntegration));
    }
    onOpenChange(nextOpen);
  }

  async function onSubmit(data: AIProviderIntegrationInput) {
    try {
      if (isEditing && editingId) {
        await updateMutation.mutateAsync({
          name: data.name,
          config: JSON.stringify({ provider: data.provider, api_key: data.api_key }),
        });
        toast.success('AI provider updated');
      } else {
        await createMutation.mutateAsync({
          name: data.name,
          integration_type: 'ai_provider',
          config: JSON.stringify({ provider: data.provider, api_key: data.api_key }),
        });
        toast.success('AI provider created');
      }
      handleOpenChange(false);
    } catch {
      toast.error('Something went wrong. Please try again.');
    }
  }

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutationError = isEditing ? updateMutation.error : createMutation.error;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit AI Provider' : 'Add AI Provider'}</DialogTitle>
          <DialogDescription>Configure an AI model provider integration.</DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="ai-name">Name</Label>
            <Input id="ai-name" placeholder="e.g. OpenAI Production" {...register('name')} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="ai-provider">Provider</Label>
            <Select
              value={provider ?? ''}
              onValueChange={(v) => setValue('provider', v as AIProviderIntegrationInput['provider'])}
            >
              <SelectTrigger id="ai-provider" className="w-full">
                <SelectValue placeholder="Select a provider..." />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.provider && <p className="text-xs text-destructive">{errors.provider.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="ai-apikey">API Key</Label>
            <Input id="ai-apikey" type="password" placeholder="sk-..." {...register('api_key')} />
            {errors.api_key && <p className="text-xs text-destructive">{errors.api_key.message}</p>}
          </div>

          {mutationError && (
            <p className="text-sm text-destructive">
              {mutationError instanceof Error ? mutationError.message : 'Operation failed'}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="size-4 animate-spin mr-2" />}
              {isEditing ? 'Save Changes' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function getDefaults(integration?: IntegrationSummary): AIProviderIntegrationInput {
  if (!integration) return { name: '', provider: 'openai', api_key: '' };
  let config: Record<string, unknown> = {};
  try {
    config = JSON.parse(integration.config) as Record<string, unknown>;
  } catch { /* empty */ }
  return {
    name: integration.name,
    provider: (config.provider as AIProviderIntegrationInput['provider']) || 'openai',
    api_key: (config.api_key as string) || '',
  };
}
