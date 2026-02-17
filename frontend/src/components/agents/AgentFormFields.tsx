import type { Control, FieldValues, Path } from 'react-hook-form';
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { MODEL_PROVIDERS } from '@/lib/constants';

/**
 * Convert seconds to a human-readable duration string.
 */
function humanizeDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} second${seconds !== 1 ? 's' : ''}`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  if (minutes < 60) {
    const parts = [`${minutes} minute${minutes !== 1 ? 's' : ''}`];
    if (remaining > 0) parts.push(`${remaining}s`);
    return parts.join(' ');
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  const parts = [`${hours} hour${hours !== 1 ? 's' : ''}`];
  if (remainingMinutes > 0) parts.push(`${remainingMinutes}m`);
  return parts.join(' ');
}

// ---- Shared field props type ----

interface FieldProps<T extends FieldValues> {
  control: Control<T>;
}

// ---- Name Field ----

export function NameField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'name' as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Name</FormLabel>
          <FormControl>
            <Input placeholder="My Agent" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// ---- Model Provider Field ----

export function ModelProviderField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'model_provider' as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Model Provider</FormLabel>
          <Select onValueChange={field.onChange} value={field.value as string}>
            <FormControl>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a provider" />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              {MODEL_PROVIDERS.map((provider) => (
                <SelectItem key={provider.value} value={provider.value}>
                  {provider.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// ---- Model Name Field ----

export function ModelNameField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'model_name' as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Model Name</FormLabel>
          <FormControl>
            <Input placeholder="gpt-4o" {...field} />
          </FormControl>
          <FormDescription>
            The specific model identifier (e.g., gpt-4o, claude-sonnet-4-20250514, llama3)
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// ---- Identity Field ----

export function IdentityField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'identity' as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Identity</FormLabel>
          <FormControl>
            <Textarea
              placeholder="Describe who this agent is..."
              rows={6}
              {...field}
              value={field.value ?? ''}
            />
          </FormControl>
          <FormDescription>
            Defines the agent's role and purpose. This shapes how the agent
            introduces itself and approaches tasks.
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// ---- Personality Field ----

export function PersonalityField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'personality' as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Personality</FormLabel>
          <FormControl>
            <Textarea
              placeholder="Describe how this agent communicates..."
              rows={6}
              {...field}
              value={field.value ?? ''}
            />
          </FormControl>
          <FormDescription>
            Controls the agent's communication style, tone, and behavioral
            tendencies.
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// ---- Heartbeat Interval Field ----

export function HeartbeatIntervalField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'heartbeat_interval_seconds' as Path<T>}
      render={({ field }) => {
        const numValue = typeof field.value === 'number' ? field.value : 300;
        return (
          <FormItem>
            <FormLabel>Heartbeat Interval (seconds)</FormLabel>
            <FormControl>
              <Input
                type="number"
                min={10}
                max={86400}
                {...field}
                value={field.value ?? 300}
                onChange={(e) => {
                  const val = e.target.value;
                  field.onChange(val === '' ? undefined : Number(val));
                }}
              />
            </FormControl>
            <FormDescription>
              = {humanizeDuration(numValue)} (min 10s, max 24h)
            </FormDescription>
            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
}

// ---- Heartbeat Prompt Field (edit page only) ----

export function HeartbeatPromptField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'heartbeat_prompt' as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Heartbeat Prompt</FormLabel>
          <FormControl>
            <Textarea
              placeholder="Instructions for what the agent should do during heartbeats..."
              rows={4}
              {...field}
              value={field.value ?? ''}
            />
          </FormControl>
          <FormDescription>
            The prompt sent to the agent on each heartbeat tick. Guides
            autonomous behavior between messages.
          </FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// ---- Heartbeat Enabled Field (edit page only) ----

export function HeartbeatEnabledField<T extends FieldValues>({
  control,
}: FieldProps<T>) {
  return (
    <FormField
      control={control}
      name={'heartbeat_enabled' as Path<T>}
      render={({ field }) => (
        <FormItem className="flex items-center justify-between rounded-lg border p-4">
          <div className="space-y-0.5">
            <FormLabel>Heartbeat Enabled</FormLabel>
            <FormDescription>
              When enabled, the agent will autonomously wake on a timer
            </FormDescription>
          </div>
          <FormControl>
            <Switch
              checked={field.value as boolean}
              onCheckedChange={field.onChange}
            />
          </FormControl>
        </FormItem>
      )}
    />
  );
}
