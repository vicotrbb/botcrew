import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  ArrowLeft,
  Loader2,
  Save,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import MDEditor from '@uiw/react-md-editor';
import { toast } from 'sonner';
import { updateAgentSchema } from '@/lib/schemas';
import type { UpdateAgentInput } from '@/types/agent';
import {
  useAgent,
  useUpdateAgent,
  useDeleteAgent,
  useAgentMemory,
  useUpdateAgentMemory,
  useAgentTokenUsage,
} from '@/hooks/use-agents';
import { Form } from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { StatusBadge } from '@/components/shared/StatusBadge';
import {
  NameField,
  ModelProviderField,
  ModelNameField,
  IdentityField,
  PersonalityField,
  HeartbeatIntervalField,
  HeartbeatPromptField,
  HeartbeatEnabledField,
} from '@/components/agents/AgentFormFields';

// ---- Loading Skeleton ----

function DetailSkeleton() {
  return (
    <div className="p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <div className="w-9 h-9 bg-muted animate-pulse rounded" />
          <div className="space-y-2">
            <div className="h-7 w-48 bg-muted animate-pulse rounded" />
            <div className="h-4 w-24 bg-muted animate-pulse rounded" />
          </div>
        </div>
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader>
              <div className="h-5 w-32 bg-muted animate-pulse rounded" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="h-9 bg-muted animate-pulse rounded" />
              <div className="h-9 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---- Delete Confirmation Dialog ----

function DeleteDialog({
  agentName,
  isPending,
  onConfirm,
}: {
  agentName: string;
  isPending: boolean;
  onConfirm: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm">
          <Trash2 className="size-4" />
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-destructive" />
            Delete Agent
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete <strong>{agentName}</strong>? This
            will terminate the agent's pod and remove all associated data. This
            action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Agent'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---- Memory Editor Section ----

function MemorySection({ agentId }: { agentId: string }) {
  const { data: memoryData, isLoading } = useAgentMemory(agentId);
  const updateMemory = useUpdateAgentMemory(agentId);
  const [memoryText, setMemoryText] = useState('');
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (memoryData) {
      // Memory comes back as { content: "..." } or as a flat object.
      // Extract the content string if present, otherwise JSON stringify.
      const raw = memoryData as Record<string, unknown>;
      if (typeof raw.content === 'string') {
        setMemoryText(raw.content);
      } else {
        setMemoryText(JSON.stringify(raw, null, 2));
      }
      setIsDirty(false);
    }
  }, [memoryData]);

  function handleSave() {
    updateMemory.mutate(
      { content: memoryText } as Record<string, unknown>,
      {
        onSuccess: () => {
          setIsDirty(false);
          toast.success('Memory saved');
        },
        onError: () => {
          toast.error('Something went wrong. Please try again.');
        },
      },
    );
  }

  const colorMode = typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Memory</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="h-[300px] bg-muted animate-pulse rounded" />
        ) : (
          <div data-color-mode={colorMode}>
            <MDEditor
              value={memoryText}
              onChange={(val) => {
                setMemoryText(val ?? '');
                setIsDirty(true);
              }}
              height={300}
            />
          </div>
        )}
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={!isDirty || updateMemory.isPending}
          >
            {updateMemory.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="size-4" />
                Save Memory
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---- Token Usage Section ----

function formatTokenCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 10_000) return `${(count / 1_000).toFixed(1)}K`;
  return new Intl.NumberFormat().format(count);
}

function TokenUsageSection({ agentId }: { agentId: string }) {
  const { data, isLoading } = useAgentTokenUsage(agentId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Token Usage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="h-20 bg-muted animate-pulse rounded-lg" />
            <div className="h-20 bg-muted animate-pulse rounded-lg" />
          </div>
        ) : data && (data.total_input_tokens > 0 || data.total_output_tokens > 0) ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 rounded-lg bg-muted/30">
                <p className="text-2xl font-semibold">{formatTokenCount(data.total_input_tokens)}</p>
                <p className="text-xs text-muted-foreground mt-1">Input Tokens</p>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/30">
                <p className="text-2xl font-semibold">{formatTokenCount(data.total_output_tokens)}</p>
                <p className="text-xs text-muted-foreground mt-1">Output Tokens</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">Lifetime cumulative totals across all calls.</p>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No token usage recorded yet</p>
        )}
      </CardContent>
    </Card>
  );
}

// ---- Main Detail Page ----

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: agent, isLoading, error } = useAgent(id);
  const updateAgent = useUpdateAgent(id!);
  const deleteAgent = useDeleteAgent();

  const form = useForm<UpdateAgentInput>({
    resolver: zodResolver(updateAgentSchema),
    defaultValues: {
      name: '',
      model_provider: undefined,
      model_name: '',
      identity: '',
      personality: '',
      heartbeat_prompt: '',
      heartbeat_enabled: false,
      heartbeat_interval_seconds: 300,
    },
  });

  // Populate form when agent data loads
  useEffect(() => {
    if (agent) {
      form.reset({
        name: agent.name,
        model_provider: agent.model_provider,
        model_name: agent.model_name,
        identity: agent.identity ?? '',
        personality: agent.personality ?? '',
        heartbeat_prompt: agent.heartbeat_prompt ?? '',
        heartbeat_enabled: agent.heartbeat_enabled,
        heartbeat_interval_seconds: agent.heartbeat_interval_seconds,
      });
    }
  }, [agent, form]);

  function onSubmit(data: UpdateAgentInput) {
    // Only send fields that have actually changed
    const dirtyFields = form.formState.dirtyFields;
    const changedData: Partial<UpdateAgentInput> = {};
    for (const key of Object.keys(dirtyFields) as (keyof UpdateAgentInput)[]) {
      if (dirtyFields[key]) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (changedData as any)[key] = data[key];
      }
    }

    if (Object.keys(changedData).length === 0) return;

    updateAgent.mutate(changedData as UpdateAgentInput, {
      onSuccess: () => {
        toast.success('Agent updated');
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
  }

  function handleDelete() {
    if (!id) return;
    deleteAgent.mutate(id, {
      onSuccess: () => {
        toast.success('Agent deleted');
        navigate('/agents');
      },
      onError: () => {
        toast.error('Something went wrong. Please try again.');
      },
    });
  }

  // Loading state
  if (isLoading) return <DetailSkeleton />;

  // Error state
  if (error || !agent) {
    return (
      <div className="p-6">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-4 mb-6">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/agents')}
            >
              <ArrowLeft className="size-5" />
            </Button>
            <h1 className="text-2xl font-semibold tracking-tight">
              Agent Not Found
            </h1>
          </div>
          <Card>
            <CardContent className="py-12 text-center">
              <AlertTriangle className="size-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">
                {error?.message ?? 'Agent could not be loaded'}
              </p>
              <p className="text-muted-foreground mt-1">
                The agent may have been deleted or the ID is invalid.
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => navigate('/agents')}
              >
                Back to Agents
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/agents')}
            >
              <ArrowLeft className="size-5" />
            </Button>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-semibold tracking-tight">
                  {agent.name}
                </h1>
                <StatusBadge status={agent.status} />
              </div>
              <p className="text-muted-foreground text-sm mt-0.5">
                {agent.model_provider} / {agent.model_name}
              </p>
            </div>
          </div>
          <DeleteDialog
            agentName={agent.name}
            isPending={deleteAgent.isPending}
            onConfirm={handleDelete}
          />
        </div>

        {/* Configuration Form (Sections 1-3) */}
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-6"
          >
            {/* Section 1: General */}
            <Card>
              <CardHeader>
                <CardTitle>General</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <NameField control={form.control} />
                <div className="grid grid-cols-2 gap-4">
                  <ModelProviderField control={form.control} />
                  <ModelNameField control={form.control} />
                </div>
              </CardContent>
            </Card>

            {/* Section 2: Identity & Personality */}
            <Card>
              <CardHeader>
                <CardTitle>Identity & Personality</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <IdentityField control={form.control} />
                <Separator />
                <PersonalityField control={form.control} />
              </CardContent>
            </Card>

            {/* Section 3: Heartbeat */}
            <Card>
              <CardHeader>
                <CardTitle>Heartbeat</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <HeartbeatEnabledField control={form.control} />
                <HeartbeatIntervalField control={form.control} />
                <HeartbeatPromptField control={form.control} />
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={
                  !form.formState.isDirty || updateAgent.isPending
                }
              >
                {updateAgent.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="size-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </form>
        </Form>

        {/* Section 4: Memory (separate save) */}
        <MemorySection agentId={id!} />

        {/* Section 5: Token Usage */}
        <TokenUsageSection agentId={id!} />
      </div>
    </div>
  );
}
