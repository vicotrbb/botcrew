import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { createAgentSchema } from '@/lib/schemas';
import type { CreateAgentInput } from '@/types/agent';
import { useCreateAgent } from '@/hooks/use-agents';
import { Form } from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  NameField,
  ModelProviderField,
  ModelNameField,
  IdentityField,
  PersonalityField,
  HeartbeatIntervalField,
} from '@/components/agents/AgentFormFields';

export function AgentCreatePage() {
  const navigate = useNavigate();
  const createAgent = useCreateAgent();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const form = useForm<CreateAgentInput>({
    resolver: zodResolver(createAgentSchema),
    defaultValues: {
      name: '',
      model_provider: undefined,
      model_name: '',
      identity: '',
      personality: '',
      heartbeat_interval_seconds: 300,
    },
  });

  function onSubmit(data: CreateAgentInput) {
    // Strip empty optional strings so the API receives undefined instead of ""
    const payload: CreateAgentInput = {
      name: data.name,
      model_provider: data.model_provider,
      model_name: data.model_name,
      ...(data.identity ? { identity: data.identity } : {}),
      ...(data.personality ? { personality: data.personality } : {}),
      heartbeat_interval_seconds: data.heartbeat_interval_seconds,
    };

    createAgent.mutate(payload, {
      onSuccess: () => navigate('/agents'),
    });
  }

  return (
    <div className="p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/agents')}
          >
            <ArrowLeft className="size-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Create Agent
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Configure a new agent for your workforce
            </p>
          </div>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-6"
              >
                {/* Required Fields */}
                <div className="space-y-4">
                  <NameField control={form.control} />
                  <div className="grid grid-cols-2 gap-4">
                    <ModelProviderField control={form.control} />
                    <ModelNameField control={form.control} />
                  </div>
                </div>

                <Separator />

                {/* Advanced Options Toggle */}
                <button
                  type="button"
                  className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                >
                  {showAdvanced ? (
                    <ChevronDown className="size-4" />
                  ) : (
                    <ChevronRight className="size-4" />
                  )}
                  Advanced options
                </button>

                {showAdvanced && (
                  <div className="space-y-4">
                    <IdentityField control={form.control} />
                    <PersonalityField control={form.control} />
                    <HeartbeatIntervalField control={form.control} />
                  </div>
                )}

                {/* Error Display */}
                {createAgent.error && (
                  <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                    {createAgent.error.message}
                  </div>
                )}

                {/* Submit */}
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={createAgent.isPending}
                >
                  {createAgent.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create Agent'
                  )}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
