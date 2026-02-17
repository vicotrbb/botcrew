import type { AgentStatus } from '@/types/agent';
import { cn } from '@/lib/utils';

interface StatusConfig {
  color: string;
  pulse: boolean;
  label: string;
}

const STATUS_MAP: Record<AgentStatus, StatusConfig> = {
  creating:    { color: 'bg-blue-500',   pulse: true,  label: 'Creating' },
  running:     { color: 'bg-green-500',  pulse: true,  label: 'Running' },
  idle:        { color: 'bg-yellow-500', pulse: false, label: 'Idle' },
  error:       { color: 'bg-red-500',    pulse: false, label: 'Error' },
  recovering:  { color: 'bg-orange-500', pulse: true,  label: 'Recovering' },
  terminating: { color: 'bg-gray-500',   pulse: false, label: 'Terminating' },
};

const DOT_SIZES = {
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3.5 h-3.5',
} as const;

const LABEL_SIZES = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-sm',
} as const;

interface StatusBadgeProps {
  status: AgentStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function StatusBadge({ status, size = 'md', showLabel = true }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? STATUS_MAP.error;
  const dotSize = DOT_SIZES[size];
  const labelSize = LABEL_SIZES[size];

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex">
        {config.pulse && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
              config.color,
            )}
          />
        )}
        <span className={cn('relative inline-flex rounded-full', dotSize, config.color)} />
      </span>
      {showLabel && (
        <span className={cn('font-medium text-muted-foreground', labelSize)}>
          {config.label}
        </span>
      )}
    </span>
  );
}
